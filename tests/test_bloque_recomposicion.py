"""
Tests del Bloque 1 · Recomposición (carril data-driven).
Corré:  python tests/test_bloque_recomposicion.py

Además de verificar que el YAML parsee, estos tests blindan las REGLAS del
bloque: si alguien edita el YAML y rompe una regla de seguridad (WOD en día
de Zona 2, simetría invertida en el curl femoral, un movimiento prohibido),
el test falla en vez de generar una planilla peligrosa.
"""

import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bloque_builder import BloqueBuilder
from src.bloque_exporter import BloqueExporter

BLOQUE = "recomposicion"


def _b():
    return BloqueBuilder(nombre_bloque=BLOQUE)


def _dia(semana, titulo):
    return [d for d in semana.dias if d.titulo == titulo][0]


def _lineas_dia(semana, titulo):
    lineas = []
    for _, ls in _dia(semana, titulo).bloques:
        lineas += ls
    return lineas


def _headers_dia(semana, titulo):
    return [h for h, _ in _dia(semana, titulo).bloques]


def _todas_las_lineas(semana):
    lineas = []
    for dia in semana.dias:
        for _, ls in dia.bloques:
            lineas += ls
    return lineas


# ═══════════════════════════════════════════════════════════════
# Metadatos y estructura
# ═══════════════════════════════════════════════════════════════

def test_metadatos():
    b = _b()
    assert b.total_semanas == 4
    assert b.program.semana_deload == 4
    assert b.program.tema == "arena"
    assert b.program.atleta == "Luciano"


def test_variantes_declaradas():
    b = _b()
    assert b.dias_disponibles == [3, 4, 5]
    assert b.program.variante_default == 4


def test_estructura_por_variante():
    b = _b()
    esperado = {
        3: ["FUERZA A", "PACING", "FUERZA B"],
        4: ["FUERZA A", "AERÓBICO", "PACING", "FUERZA B"],
        5: ["FUERZA A", "AERÓBICO", "PACING", "FUERZA B", "WOD"],
    }
    for n, titulos in esperado.items():
        assert [d.titulo for d in b.construir_semana(1, dias=n).dias] == titulos


def test_piso_innegociable_en_toda_variante():
    """F1, Z2 y F2 tienen que estar sí o sí, entrene 3, 4 o 5 días."""
    b = _b()
    for n in (3, 4, 5):
        titulos = [d.titulo for d in b.construir_semana(1, dias=n).dias]
        for obligatorio in ("FUERZA A", "PACING", "FUERZA B"):
            assert obligatorio in titulos, f"{n} días: falta {obligatorio}"


def test_dia_w_solo_en_variante_5():
    b = _b()
    for n in (3, 4):
        assert "WOD" not in [d.titulo for d in b.construir_semana(1, dias=n).dias]


def test_el_dia_mas_corto_va_segundo():
    """
    Los martes son largos y la 2ª sesión de la semana cae en martes el 90% de
    las semanas: ahí tiene que ir la sesión más corta.

    El más corto se calcula de las duraciones declaradas en el YAML, no de un
    orden hardcodeado: si mañana cambian las duraciones, el test sigue midiendo
    la intención y no una lista.

    La variante de 3 queda afuera a propósito: esas semanas no incluyen martes.
    """
    import re
    b = _b()

    def techo_min(clave):
        """'~35-45 min' → 45. Se compara por el techo declarado."""
        nums = [int(x) for x in re.findall(r"\d+", b.program.dias[clave].duracion)]
        return max(nums) if nums else 0

    for n in (4, 5):
        claves = b.program.variantes[n].dias
        duraciones = {c: techo_min(c) for c in claves}
        mas_corto = min(duraciones, key=duraciones.get)
        assert claves[1] == mas_corto, (
            f"{n} días: el 2º día es {claves[1]} ({duraciones[claves[1]]} min), "
            f"pero el más corto es {mas_corto} ({duraciones[mas_corto]} min)")


def test_semana_fuera_de_rango():
    b = _b()
    for mala in (0, 5):
        try:
            b.construir_semana(mala)
            assert False, f"Semana {mala} debería fallar"
        except ValueError:
            pass


def test_sin_dias_vacios():
    b = _b()
    for n in (3, 4, 5):
        for sem in range(1, 5):
            for dia in b.construir_semana(sem, dias=n).dias:
                assert dia.bloques, f"{n}d · S{sem} · {dia.titulo} sin bloques"


# ═══════════════════════════════════════════════════════════════
# Progresión y deload
# ═══════════════════════════════════════════════════════════════

def test_progresion_front_squat():
    """Sube S1→S3 y baja en el deload."""
    b = _b()
    def fs(s):
        return [l for l in _lineas_dia(b.construir_semana(s), "FUERZA A")
                if l.startswith("Front squat")][0]
    assert "60 kg" in fs(1)
    assert "62,5 kg" in fs(2)
    assert "65 kg" in fs(3)
    assert "50 kg" in fs(4) and "deload" in fs(4).lower()


def test_progresion_hip_thrust():
    b = _b()
    def ht(s):
        return [l for l in _lineas_dia(b.construir_semana(s), "FUERZA A")
                if l.startswith("Hip thrust")][0]
    assert "65 kg" in ht(1) and "70 kg" in ht(2) and "75 kg" in ht(3)
    assert "60 kg · 2×10" in ht(4)


def test_zona_2_sube_y_descarga():
    b = _b()
    def dur(s):
        return [l for l in _lineas_dia(b.construir_semana(s), "PACING")
                if l.startswith("Duración efectiva")][0]
    assert "45 min" in dur(1)
    assert "50 min" in dur(2)
    assert "55-60 min" in dur(3)
    assert "40 min" in dur(4)


def test_cues_fijos_se_repiten():
    """Los cues técnicos deben aparecer en las 4 semanas."""
    b = _b()
    for sem in range(1, 5):
        ht = [l for l in _lineas_dia(b.construir_semana(sem), "FUERZA A")
              if l.startswith("Hip thrust")][0]
        assert "2s pausa arriba" in ht, f"S{sem}: falta el cue -> {ht}"


# ═══════════════════════════════════════════════════════════════
# REGLAS DE SEGURIDAD — lo que no se puede romper editando el YAML
# ═══════════════════════════════════════════════════════════════

def test_curl_femoral_serie_extra_izquierda():
    """
    Injerto de semitendinoso: la izquierda SIEMPRE lleva más series que la
    derecha. Si alguien invierte esto en el YAML, el test lo caza.
    """
    import re
    b = _b()
    for sem in range(1, 5):
        linea = [l for l in _lineas_dia(b.construir_semana(sem), "FUERZA A")
                 if l.startswith("Curl femoral unilateral")][0]
        izq = int(re.search(r"IZQ (\d+)×", linea).group(1))
        der = int(re.search(r"DER (\d+)×", linea).group(1))
        assert izq > der, f"S{sem}: IZQ {izq} no supera a DER {der} -> {linea}"


def test_unilaterales_empiezan_por_izquierda():
    """Todo ejercicio unilateral debe llevar el cue 'IZQ primero'."""
    b = _b()
    unilaterales = ["Curl femoral unilateral", "Step-up lateral",
                    "RDL unilateral con mancuernas"]
    lineas = _todas_las_lineas(b.construir_semana(1, dias=5))
    for nombre in unilaterales:
        match = [l for l in lineas if l.startswith(nombre)]
        assert match, f"No encontré '{nombre}'"
        assert "IZQ primero" in match[0], f"'{nombre}' sin cue de lado -> {match[0]}"


def test_dia_zona_2_no_lleva_wod():
    """
    Regla dura: si el día de Zona 2 lleva intensidad, deja de ser Zona 2.
    Ni Z2 ni Z2B pueden tener sección de WOD o finisher.
    """
    b = _b()
    for n in (3, 4, 5):
        for sem in range(1, 5):
            semana = b.construir_semana(sem, dias=n)
            for titulo in ("PACING", "AERÓBICO"):
                if titulo not in [d.titulo for d in semana.dias]:
                    continue
                headers = " ".join(_headers_dia(semana, titulo)).upper()
                assert "WOD" not in headers and "FINISHER" not in headers, (
                    f"{n}d · S{sem} · {titulo} tiene intensidad: {headers}"
                )


def test_dias_de_fuerza_llevan_finisher():
    """La contracara: F1 y F2 sí tienen su WOD corto."""
    b = _b()
    for titulo in ("FUERZA A", "FUERZA B"):
        headers = " ".join(_headers_dia(b.construir_semana(1), titulo)).upper()
        assert "FINISHER" in headers, f"{titulo} sin finisher"


def test_presupuesto_maximo_3_wods():
    """
    2 finishers (F1, F2) + 1 WOD principal (día W) = 3. Ni uno más,
    aunque se entrene 5 días.
    """
    b = _b()
    for n in (3, 4, 5):
        semana = b.construir_semana(1, dias=n)
        con_wod = sum(
            1 for d in semana.dias
            if any("WOD" in h.upper() or "FINISHER" in h.upper() for h, _ in d.bloques)
        )
        assert con_wod <= 3, f"{n} días: {con_wod} sesiones con WOD (máx 3)"


def test_movimientos_prohibidos_declarados():
    """Los filtros del día W tienen que nombrar lo que está vedado."""
    b = _b()
    lineas = " ".join(_lineas_dia(b.construir_semana(1, dias=5), "WOD")).lower()
    for prohibido in ("press de hombro", "vuelos laterales", "press banca",
                      "fondos", "muscle-ups", "pistols"):
        assert prohibido in lineas, f"Falta declarar como prohibido: {prohibido}"


def test_sin_press_por_encima_de_la_cabeza_en_fuerza():
    """
    Hombro derecho (rotura parcial de supraespinoso): ningún día de fuerza
    puede prescribir press de hombro, push press, jerk, thruster o vuelos.
    El landmine press SÍ está permitido (confirmado por el atleta).
    """
    b = _b()
    vedados = ["press militar", "press de hombro", "push press",
               "jerk", "thruster", "vuelo lateral", "elevaciones laterales",
               "press banca", "fondos", "dips"]
    for n in (3, 4, 5):
        for sem in range(1, 5):
            semana = b.construir_semana(sem, dias=n)
            for titulo in ("FUERZA A", "FUERZA B"):
                for h, ls in _dia(semana, titulo).bloques:
                    if "FILTRO" in h.upper() or "FINISHER" in h.upper():
                        continue          # ahí se nombran justamente para prohibirlos
                    texto = " ".join(ls).lower()
                    for v in vedados:
                        assert v not in texto, f"{titulo} S{sem}: aparece '{v}'"


def test_nota_global_cubre_las_prioridades():
    b = _b()
    nota = b.construir_semana(1).nota_global.lower()
    assert "grasa" in nota
    assert "zona 2" in nota
    assert "izquierda" in nota
    assert "dolor" in nota


# ═══════════════════════════════════════════════════════════════
# Exportación
# ═══════════════════════════════════════════════════════════════

def test_exporter_todas_las_variantes():
    b = _b()
    with tempfile.TemporaryDirectory() as tmp:
        exp = BloqueExporter(output_dir=tmp, tema=b.program.tema)
        for n in (3, 4, 5):
            for sem in range(1, 5):
                ruta = exp.exportar_semana(b.construir_semana(sem, dias=n),
                                           f"test_recomp_S{sem}_{n}d")
                assert os.path.exists(ruta) and os.path.getsize(ruta) > 0


def test_convive_con_reconstruccion():
    """El bloque viejo tiene que seguir cargando igual que siempre."""
    viejo = BloqueBuilder(nombre_bloque="reconstruccion")
    assert viejo.program.nombre == "Bloque Reconstrucción"
    assert [d.titulo for d in viejo.construir_semana(1).dias] == \
        ["DÍA A", "DÍA B", "DÍA C", "DÍA D"]


if __name__ == "__main__":
    tests = [
        test_metadatos,
        test_variantes_declaradas,
        test_estructura_por_variante,
        test_piso_innegociable_en_toda_variante,
        test_dia_w_solo_en_variante_5,
        test_el_dia_mas_corto_va_segundo,
        test_semana_fuera_de_rango,
        test_sin_dias_vacios,
        test_progresion_front_squat,
        test_progresion_hip_thrust,
        test_zona_2_sube_y_descarga,
        test_cues_fijos_se_repiten,
        test_curl_femoral_serie_extra_izquierda,
        test_unilaterales_empiezan_por_izquierda,
        test_dia_zona_2_no_lleva_wod,
        test_dias_de_fuerza_llevan_finisher,
        test_presupuesto_maximo_3_wods,
        test_movimientos_prohibidos_declarados,
        test_sin_press_por_encima_de_la_cabeza_en_fuerza,
        test_nota_global_cubre_las_prioridades,
        test_exporter_todas_las_variantes,
        test_convive_con_reconstruccion,
    ]

    print("🧪 Corriendo tests del Bloque 1 · Recomposición...\n")
    passed = failed = 0
    for test in tests:
        try:
            test()
            print(f"  ✅ {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  ❌ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ {test.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n📊 Resultados: {passed} pasaron, {failed} fallaron")
    sys.exit(1 if failed else 0)
