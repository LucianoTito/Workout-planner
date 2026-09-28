"""
Tests del Bloque 2 · Recomposición (carril data-driven).
Corré:  python tests/test_bloque_recomposicion_b2.py
"""

import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bloque_builder import BloqueBuilder
from src.bloque_exporter import BloqueExporter

NOMBRE = "recomposicion_b2"


def _todas_las_lineas(semana):
    lineas = []
    for dia in semana.dias:
        for _, ls in dia.bloques:
            lineas += ls
    return lineas


def _lineas_dia(semana, titulo):
    dia = [d for d in semana.dias if d.titulo == titulo][0]
    return [l for _, ls in dia.bloques for l in ls]


def test_carga_metadatos():
    b = BloqueBuilder(nombre_bloque=NOMBRE)
    assert b.total_semanas == 4
    assert b.program.semana_deload == 4
    assert b.dias_disponibles == [2, 3, 4]
    assert b.program.variante_default == 3


def test_variantes_de_dias():
    b = BloqueBuilder(nombre_bloque=NOMBRE)
    esperado = {
        2: ["FUERZA COMBINADA", "PACING"],
        3: ["FUERZA A", "PACING", "FUERZA B"],
        4: ["FUERZA A", "AERÓBICO", "PACING", "FUERZA B"],
    }
    for n, titulos in esperado.items():
        for s in range(1, 5):
            assert [d.titulo for d in b.construir_semana(s, dias=n).dias] == titulos


def test_variante_invalida():
    b = BloqueBuilder(nombre_bloque=NOMBRE)
    for malo in (1, 5):
        try:
            b.construir_semana(1, dias=malo)
            assert False, f"dias={malo} debería fallar"
        except ValueError:
            pass


def test_ningun_dia_vacio():
    b = BloqueBuilder(nombre_bloque=NOMBRE)
    for n in (2, 3, 4):
        for s in range(1, 5):
            for d in b.construir_semana(s, dias=n).dias:
                assert d.bloques, f"{d.titulo} vacío (dias={n}, S{s})"


def test_pacing_siempre_assault_y_zona2_en_todas_las_variantes():
    b = BloqueBuilder(nombre_bloque=NOMBRE)
    for n in (2, 3, 4):
        lineas = _lineas_dia(b.construir_semana(1, dias=n), "PACING")
        assert any("Assault bike" in l for l in lineas)
        assert any("120-130 ppm" in l for l in lineas)


def test_rehab_de_rodilla_y_manguito_no_se_pierden():
    b = BloqueBuilder(nombre_bloque=NOMBRE)
    s = b.construir_semana(1, dias=3)
    a = " ".join(_lineas_dia(s, "FUERZA A"))
    bb = " ".join(_lineas_dia(s, "FUERZA B"))
    for clave in ("Abducción de cadera", "monster walk", "TKE", "Dead bug", "Wall sit"):
        assert clave in a, f"falta {clave} en FUERZA A"
    for clave in ("Reverse fly", "Rotación externa", "Face pull", "Serrato punch",
                  "Prone IYT", "Band pull-apart", "Colgado activo"):
        assert clave in bb, f"falta {clave} en FUERZA B"


def test_fuerza_combinada_conserva_rehab_de_rodilla_y_hombro():
    b = BloqueBuilder(nombre_bloque=NOMBRE)
    fc = " ".join(_lineas_dia(b.construir_semana(1, dias=2), "FUERZA COMBINADA"))
    for clave in ("TKE", "Abducción de cadera", "Face pull", "Serrato punch",
                  "Hang power clean", "Front squat", "Curl femoral unilateral"):
        assert clave in fc, f"falta {clave} en FUERZA COMBINADA"


def test_front_squat_mantiene_3s_de_bajada_y_progresa():
    b = BloqueBuilder(nombre_bloque=NOMBRE)
    cargas = []
    for s in range(1, 5):
        linea = [l for l in _lineas_dia(b.construir_semana(s, dias=3), "FUERZA A")
                 if l.startswith("Front squat")][0]
        assert "3s bajando" in linea
        cargas.append(linea)
    assert "62,5 kg" in cargas[0] and "65 kg" in cargas[1]
    assert "67,5 kg" in cargas[2] and "55 kg" in cargas[3]      # S4 = deload


def test_curl_femoral_tiene_serie_extra_izquierda_en_todas_las_semanas():
    b = BloqueBuilder(nombre_bloque=NOMBRE)
    import re
    for s in range(1, 5):
        linea = [l for l in _lineas_dia(b.construir_semana(s, dias=3), "FUERZA A")
                 if l.startswith("Curl femoral unilateral")][0]
        m = re.search(r"IZQ (\d)×\d+(?:-\d+)? / DER (\d)×", linea)
        assert m and int(m.group(1)) == int(m.group(2)) + 1, linea


def test_press_sentado_esta_marcado_en_prueba():
    b = BloqueBuilder(nombre_bloque=NOMBRE)
    for s in range(1, 5):
        lineas = _lineas_dia(b.construir_semana(s, dias=3), "FUERZA B")
        press = [l for l in lineas if l.startswith("Press de hombro sentado")][0]
        assert "EN PRUEBA" in press and "17,5 kg" in press


def test_no_hay_gestos_prohibidos_por_hombro_ni_jerk():
    """El bloque no incluye jerk, push press, thrusters, vuelos laterales ni ring dips."""
    b = BloqueBuilder(nombre_bloque=NOMBRE)
    texto = " ".join(_todas_las_lineas(b.construir_semana(1, dias=4))).lower()
    for prohibido in ("jerk", "push press", "thruster", "vuelos laterales", "ring dip"):
        assert prohibido not in texto


def test_deload_baja_el_volumen_de_potencia():
    b = BloqueBuilder(nombre_bloque=NOMBRE)
    s3 = [l for l in _lineas_dia(b.construir_semana(3, dias=3), "FUERZA A")
          if l.startswith("Hang power clean")][0]
    s4 = [l for l in _lineas_dia(b.construir_semana(4, dias=3), "FUERZA A")
          if l.startswith("Hang power clean")][0]
    assert "5×2" in s3 and "4×2" in s4


def test_exporta_excel_para_cada_variante():
    b = BloqueBuilder(nombre_bloque=NOMBRE)
    with tempfile.TemporaryDirectory() as tmp:
        exp = BloqueExporter(output_dir=tmp, tema=b.program.tema)
        for n in (2, 3, 4):
            ruta = exp.exportar_semana(b.construir_semana(1, dias=n), f"prueba_{n}dias")
            assert os.path.exists(ruta) and os.path.getsize(ruta) > 0


# ═══════════════════════════════════════════════════════════════
# AGREGADOS AL ADAPTAR EL BLOQUE AL REPO LOCAL
# Mismo criterio que la suite del Bloque 1: blindar las reglas de seguridad
# para que editar el YAML no pueda generar una planilla peligrosa.
# ═══════════════════════════════════════════════════════════════

VARIANTES = (2, 3, 4)
SEMANAS = range(1, 5)


def _dia_por_titulo(b, titulo):
    """Definición del día (no la semana resuelta), buscada por título."""
    return [d for d in b.program.dias.values() if d.titulo == titulo][0]


def _headers(semana, titulo):
    dia = [d for d in semana.dias if d.titulo == titulo][0]
    return [h for h, _ in dia.bloques]


def test_gestos_prohibidos_en_todas_las_variantes_y_semanas():
    """
    Hombro derecho y rodilla izquierda, en TODAS las variantes (el test del
    handoff solo mira la de 4, así que FUERZA COMBINADA nunca se revisaba).
    """
    b = BloqueBuilder(nombre_bloque=NOMBRE)
    vedados = ["push press", "jerk", "thruster", "press militar", "vuelo lateral",
               "vuelos laterales", "elevaciones laterales", "press banca", "fondos",
               "ring dip", "muscle-up", "pistol"]
    for n in VARIANTES:
        for s in SEMANAS:
            texto = " ".join(_todas_las_lineas(b.construir_semana(s, dias=n))).lower()
            for v in vedados:
                assert v not in texto, f"{n}d · S{s}: aparece '{v}'"


def test_press_de_hombro_solo_en_su_version_permitida():
    """
    La única excepción del bloque: press con mancuernas, sentado en el piso,
    espalda en el rack y peso moderado. Cualquier otra línea que diga
    'press de hombro' es un error.
    """
    b = BloqueBuilder(nombre_bloque=NOMBRE)
    for n in VARIANTES:
        for s in SEMANAS:
            for l in _todas_las_lineas(b.construir_semana(s, dias=n)):
                if "press de hombro" in l.lower():
                    assert l.startswith("Press de hombro sentado en el piso"), l
                    assert "rack" in l and "db" in l, l


def test_press_de_hombro_no_sube_carga():
    """'Pesos moderados': la carga del press nunca supera la de la S1."""
    import re
    b = BloqueBuilder(nombre_bloque=NOMBRE)
    kg = []
    for s in SEMANAS:
        l = [x for x in _lineas_dia(b.construir_semana(s, dias=3), "FUERZA B")
             if x.startswith("Press de hombro sentado")][0]
        kg.append(float(re.search(r"(\d+(?:,\d+)?) kg", l).group(1).replace(",", ".")))
    assert max(kg) == kg[0], f"el press sube de carga: {kg}"


def test_fuerza_combinada_suma_wall_sit_y_cierre_de_manguito():
    b = BloqueBuilder(nombre_bloque=NOMBRE)
    for s in SEMANAS:
        fc = _lineas_dia(b.construir_semana(s, dias=2), "FUERZA COMBINADA")
        assert any(l.startswith("Wall sit") for l in fc), f"S{s}: FC sin wall sit"
        assert any(l.startswith("Rotación externa en polea") for l in fc), \
            f"S{s}: FC sin cierre de manguito"


def test_fuerza_combinada_referencia_y_no_copia():
    """Si cambia algo en FUERZA A, FC lo refleja sola (componer referencia)."""
    b = BloqueBuilder(nombre_bloque=NOMBRE)
    fa = _dia_por_titulo(b, "FUERZA A")
    for sec in fa.secciones:
        for ej in sec.ejercicios:
            if ej.nombre == "Hang power clean":
                ej.semanas[0] = "9×9 · 99 kg"
        if sec.header.startswith("CALENTAMIENTO"):
            sec.items.append("Línea de prueba de referencia")
    fc = _lineas_dia(b.construir_semana(1, dias=2), "FUERZA COMBINADA")
    assert any("99 kg" in l for l in fc), "FC copió la carga en vez de referenciarla"
    assert "Línea de prueba de referencia" in fc, "FC copió el calentamiento"


def test_unilaterales_empiezan_por_izquierda():
    b = BloqueBuilder(nombre_bloque=NOMBRE)
    lineas = _todas_las_lineas(b.construir_semana(1, dias=3))
    for nombre in ("Curl femoral unilateral", "Step-up lateral",
                   "RDL unilateral con mancuernas", "Pallof press"):
        match = [l for l in lineas if l.startswith(nombre)]
        assert match, f"No encontré '{nombre}'"
        assert "IZQ primero" in match[0], f"'{nombre}' sin cue de lado -> {match[0]}"


def test_dias_de_zona_2_sin_wod_ni_finisher():
    b = BloqueBuilder(nombre_bloque=NOMBRE)
    for n in VARIANTES:
        for s in SEMANAS:
            semana = b.construir_semana(s, dias=n)
            for titulo in ("PACING", "AERÓBICO"):
                if titulo not in [d.titulo for d in semana.dias]:
                    continue
                headers = " ".join(_headers(semana, titulo)).upper()
                assert "WOD" not in headers and "FINISHER" not in headers, \
                    f"{n}d · S{s} · {titulo}: {headers}"


def test_presupuesto_maximo_3_wods():
    b = BloqueBuilder(nombre_bloque=NOMBRE)
    for n in VARIANTES:
        semana = b.construir_semana(1, dias=n)
        con_wod = sum(1 for d in semana.dias
                      if any("WOD" in h.upper() or "FINISHER" in h.upper()
                             for h, _ in d.bloques))
        assert con_wod <= 3, f"{n} días: {con_wod} sesiones con WOD"


def test_el_dia_mas_corto_va_segundo():
    """
    Misma regla que el Bloque 1: en la variante que incluye martes (4 días),
    la 2ª sesión es la más corta. Se calcula de las duraciones del YAML.
    """
    import re
    b = BloqueBuilder(nombre_bloque=NOMBRE)

    def techo(clave):
        nums = [int(x) for x in re.findall(r"\d+", b.program.dias[clave].duracion)]
        return max(nums) if nums else 0

    claves = b.program.variantes[4].dias
    dur = {c: techo(c) for c in claves}
    assert claves[1] == min(dur, key=dur.get), f"2º día {claves[1]}: {dur}"


def test_aerobico_integra_el_catalogo_de_zona_2():
    """AERÓBICO lleva la sección con generador z2; PACING no (es el ancla de RPM)."""
    b = BloqueBuilder(nombre_bloque=NOMBRE)
    aero = _dia_por_titulo(b, "AERÓBICO")
    pacing = _dia_por_titulo(b, "PACING")
    assert any(s.generador == "z2" for s in aero.secciones)
    assert not any(s.generador for s in pacing.secciones)

    for s in SEMANAS:
        semana = b.construir_semana(s, dias=4)
        dia = [d for d in semana.dias if d.titulo == "AERÓBICO"][0]
        sugerida = [ls for h, ls in dia.bloques if "SUGERIDA" in h.upper()]
        assert sugerida, f"S{s}: AERÓBICO sin sesión sugerida"
        if b._z2 is not None:        # con catálogo, tiene que venir una sesión real
            assert len(sugerida[0]) > 2, f"S{s}: sesión sugerida vacía"
            assert not any("no disponible" in l for l in sugerida[0])


def test_cargas_estimadas_marcadas_en_s1():
    b = BloqueBuilder(nombre_bloque=NOMBRE)
    s1 = _todas_las_lineas(b.construir_semana(1, dias=3))
    for nombre in ("Hang power clean", "Front squat", "RDL unilateral con mancuernas"):
        linea = [l for l in s1 if l.startswith(nombre)][0]
        assert "orientativa" in linea, f"{nombre} S1 sin marca: {linea}"


def test_nota_global_dias_libres_y_futbol():
    nota = BloqueBuilder(nombre_bloque=NOMBRE).program.nota_global
    assert "caminata opcional de 30-40 min" in nota
    assert "Fútbol = sesión de intensidad" in nota


def test_resumen_para_el_cli_describe_cada_dia():
    """Lo que necesita el menú 4 (título, subtítulo y duración) en las 3 variantes."""
    for v in BloqueBuilder(nombre_bloque=NOMBRE).resumen_variantes():
        for d in v["dias"]:
            for campo in ("titulo", "subtitulo", "duracion"):
                assert d.get(campo), f"{v['n_dias']}d · {d.get('titulo')}: falta {campo}"


def test_convive_con_el_bloque_1():
    b1 = BloqueBuilder(nombre_bloque="recomposicion")
    assert b1.program.nombre == "Bloque 1 · Recomposición"
    assert b1.dias_disponibles == [3, 4, 5]


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_")]
    fallos = 0
    for nombre, fn in tests:
        try:
            fn()
            print(f"  ✅ {nombre}")
        except Exception as e:  # noqa: BLE001
            fallos += 1
            print(f"  ❌ {nombre}: {e!r}")
    print(f"\n{len(tests) - fallos}/{len(tests)} tests OK")
    sys.exit(1 if fallos else 0)
