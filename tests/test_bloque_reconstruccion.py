"""
Tests del Bloque Reconstrucción (carril data-driven, independiente del CrossFit).
Corré:  python tests/test_bloque_reconstruccion.py
"""

import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bloque_builder import BloqueBuilder
from src.bloque_exporter import BloqueExporter


def _lineas_dia(semana, clave_titulo):
    """Devuelve todas las líneas de un día por su título (ej. 'DÍA A')."""
    dia = [d for d in semana.dias if d.titulo == clave_titulo][0]
    lineas = []
    for _, ls in dia.bloques:
        lineas += ls
    return lineas


def _todas_las_lineas(semana):
    """Todas las líneas de todos los días de la semana."""
    lineas = []
    for dia in semana.dias:
        for _, ls in dia.bloques:
            lineas += ls
    return lineas


def test_bloque_carga_metadatos():
    """El bloque debe cargar con 4 semanas, tema arena y 4 días por defecto."""
    b = BloqueBuilder()
    assert b.total_semanas == 4
    assert b.program.tema == "arena"
    assert b.program.atleta == "Luciano"
    assert len(b.construir_semana(1).dias) == 4


def test_semana_fuera_de_rango():
    """Semanas 0 y 5 deben fallar."""
    b = BloqueBuilder()
    for mala in (0, 5):
        try:
            b.construir_semana(mala)
            assert False, f"Semana {mala} debería fallar"
        except ValueError:
            pass


def test_orden_dias():
    """Los días deben salir en orden A, B, C, D."""
    b = BloqueBuilder()
    s = b.construir_semana(1)
    titulos = [d.titulo for d in s.dias]
    assert titulos == ["DÍA A", "DÍA B", "DÍA C", "DÍA D"]


def test_progresion_hip_thrust():
    """Hip thrust del Día A debe subir S1→S3 y bajar en el deload S4."""
    b = BloqueBuilder()
    ht1 = [l for l in _lineas_dia(b.construir_semana(1), "DÍA A") if l.startswith("Hip thrust")][0]
    ht3 = [l for l in _lineas_dia(b.construir_semana(3), "DÍA A") if l.startswith("Hip thrust")][0]
    ht4 = [l for l in _lineas_dia(b.construir_semana(4), "DÍA A") if l.startswith("Hip thrust")][0]
    assert "60 kg · 3×12" in ht1
    assert "65 kg" in ht3
    assert "60 kg · 3×10" in ht4   # deload: mismo peso, menos reps


def test_deload_wall_sit_s4():
    """El Wall sit del Día A en S4 debe marcar el deload."""
    b = BloqueBuilder()
    ws4 = [l for l in _lineas_dia(b.construir_semana(4), "DÍA A") if l.startswith("Wall sit")][0]
    assert "4×40s" in ws4
    assert "deload" in ws4.lower()


def test_cue_tecnico_se_repite():
    """El cue fijo (RPE 7) debe aparecer en todas las semanas del Hip thrust."""
    b = BloqueBuilder()
    for sem in (1, 2, 3, 4):
        ht = [l for l in _lineas_dia(b.construir_semana(sem), "DÍA A") if l.startswith("Hip thrust")][0]
        assert "RPE 7" in ht, f"S{sem}: falta el cue -> {ht}"


def test_items_fijos_constantes():
    """El calentamiento del Día A debe ser igual en S1 y S3."""
    b = BloqueBuilder()
    assert "Bici suave — 4 min" in _lineas_dia(b.construir_semana(1), "DÍA A")
    assert "Bici suave — 4 min" in _lineas_dia(b.construir_semana(3), "DÍA A")


def test_nota_global_rodilla():
    """La nota global de la rodilla debe estar presente."""
    b = BloqueBuilder()
    s = b.construir_semana(2)
    assert "Rodilla izq" in s.nota_global


def test_dias_sin_bloques_vacios():
    """Ningún día debe quedar sin bloques."""
    b = BloqueBuilder()
    for sem in range(1, 5):
        for dia in b.construir_semana(sem).dias:
            assert len(dia.bloques) > 0, f"S{sem} {dia.titulo} sin bloques"


def test_exporter_genera_archivo():
    """El exporter debe generar un .xlsx sin errores."""
    b = BloqueBuilder()
    s = b.construir_semana(1)
    with tempfile.TemporaryDirectory() as tmp:
        exp = BloqueExporter(output_dir=tmp, tema=b.program.tema)
        ruta = exp.exportar_semana(s, "test_recon")
        assert os.path.exists(ruta)
        assert os.path.getsize(ruta) > 0


# ═══════════════════════════════════════════════════════════════
# VARIANTES DE DÍAS (3 / 4 / 5)
# ═══════════════════════════════════════════════════════════════

def test_variantes_declaradas():
    """El YAML debe ofrecer 3, 4 y 5 días, con 4 como default."""
    b = BloqueBuilder()
    assert b.dias_disponibles == [3, 4, 5]
    assert b.program.variante_default == 4


def test_variante_4_es_el_comportamiento_historico():
    """Sin argumento y con dias=4 debe salir exactamente lo mismo: A, B, C, D."""
    b = BloqueBuilder()
    por_defecto = b.construir_semana(2)
    explicito = b.construir_semana(2, dias=4)
    assert [d.titulo for d in por_defecto.dias] == ["DÍA A", "DÍA B", "DÍA C", "DÍA D"]
    assert _todas_las_lineas(por_defecto) == _todas_las_lineas(explicito)
    assert [d.subtitulo for d in por_defecto.dias] == [d.subtitulo for d in explicito.dias]


def test_variante_dias_invalida():
    """Pedir 6 días (o 2) debe fallar con ValueError."""
    b = BloqueBuilder()
    for malo in (2, 6):
        try:
            b.construir_semana(1, dias=malo)
            assert False, f"{malo} días debería fallar"
        except ValueError:
            pass


def test_variante_3_estructura():
    """3 días: lower fusionado + upper + zona 2."""
    b = BloqueBuilder()
    s = b.construir_semana(1, dias=3)
    assert [d.titulo for d in s.dias] == ["DÍA A", "DÍA B", "DÍA C"]
    assert "LOWER completo" in s.dias[0].subtitulo


def test_variante_3_fusiona_los_dos_lower():
    """El día fusionado debe traer bisagra (hip thrust/RDL) Y sentadilla (front squat)."""
    b = BloqueBuilder()
    lineas = _lineas_dia(b.construir_semana(1, dias=3), "DÍA A")
    assert any(l.startswith("Hip thrust") for l in lineas)
    assert any(l.startswith("RDL con barra") for l in lineas)
    assert any(l.startswith("Front squat") for l in lineas)
    assert any(l.startswith("Step-up lateral") for l in lineas)


def test_variante_3_sin_repetidos():
    """En el día fusionado, hip thrust y wall sit deben aparecer una sola vez."""
    b = BloqueBuilder()
    lineas = _lineas_dia(b.construir_semana(1, dias=3), "DÍA A")
    assert len([l for l in lineas if l.startswith("Hip thrust")]) == 1
    assert len([l for l in lineas if l.startswith("Wall sit")]) == 1
    # Split squat sale de la fusión (pisa el patrón del step-up lateral)
    assert not any(l.startswith("Split squat") for l in lineas)


def test_variante_3_referencia_cargas_no_las_copia():
    """
    Si cambia una carga en el Día A, el día fusionado debe reflejarla sola.
    Esto prueba que `componer:` referencia y no duplica.
    """
    b = BloqueBuilder()
    for sec in b.program.dias["A"].secciones:
        for ej in sec.ejercicios:
            if ej.nombre == "Hip thrust":
                ej.semanas[0] = "99 kg · 3×1"
    lineas = _lineas_dia(b.construir_semana(1, dias=3), "DÍA A")
    assert any("99 kg · 3×1" in l for l in lineas), "El día AD copió la carga en vez de referenciarla"


def test_variante_5_estructura():
    """5 días: A, B, C, D + el día E de accesorios."""
    b = BloqueBuilder()
    s = b.construir_semana(1, dias=5)
    assert [d.titulo for d in s.dias] == ["DÍA A", "DÍA B", "DÍA C", "DÍA D", "DÍA E"]
    assert "~55 min" in s.dias[0].subtitulo     # duracion_5 del Día A


def test_variante_5_muda_accesorios_al_dia_e():
    """Brazos, RDL a una pierna y core se van al Día E; salen de A y B."""
    b = BloqueBuilder()
    s = b.construir_semana(1, dias=5)
    a = _lineas_dia(s, "DÍA A")
    bb = _lineas_dia(s, "DÍA B")
    e = _lineas_dia(s, "DÍA E")

    assert not any(l.startswith("RDL a una pierna") for l in a)
    assert any(l.startswith("RDL a una pierna") for l in e)
    assert not any(l.startswith("Curl bíceps") for l in bb)
    assert any(l.startswith("Curl bíceps") for l in e)
    assert not any(l.startswith("Plancha frontal") for l in a)
    assert any(l.startswith("Plancha frontal") for l in e)


def test_variante_5_conserva_lo_principal():
    """Los bloques principales NO se mudan: siguen en su día."""
    b = BloqueBuilder()
    s = b.construir_semana(1, dias=5)
    a = _lineas_dia(s, "DÍA A")
    bb = _lineas_dia(s, "DÍA B")
    d = _lineas_dia(s, "DÍA D")

    assert any(l.startswith("Hip thrust") for l in a)
    assert any(l.startswith("Split squat") for l in a)        # se queda en A
    assert any(l.startswith("Chin-ups") for l in bb)
    assert any(l.startswith("Front squat") for l in d)
    assert any(l.startswith("Curl femoral unilateral") for l in d)   # se queda en D
    # El manguito rotador es salud, no accesorio: no se muda
    assert any(l.startswith("Rotación externa en polea") for l in bb)


def test_variante_5_dia_e_sin_duplicados():
    """El CORE del Día E recibe A y D: no debe repetir líneas idénticas."""
    b = BloqueBuilder()
    for sem in range(1, 5):
        e = _lineas_dia(b.construir_semana(sem, dias=5), "DÍA E")
        assert len(e) == len(set(e)), f"S{sem}: líneas repetidas en el Día E -> {e}"


def test_variante_5_no_se_pierde_nada():
    """Todo lo que sale de A, B y D tiene que reaparecer en el Día E."""
    b = BloqueBuilder()
    cuatro = set(_todas_las_lineas(b.construir_semana(1, dias=4)))
    cinco = set(_todas_las_lineas(b.construir_semana(1, dias=5)))
    perdidas = cuatro - cinco
    assert not perdidas, f"Se perdieron líneas al pasar a 5 días: {perdidas}"


def test_dia_e_solo_en_variante_5():
    """El Día E y el día AD no deben colarse en otras variantes."""
    b = BloqueBuilder()
    for n in (3, 4):
        titulos = [d.titulo for d in b.construir_semana(1, dias=n).dias]
        assert "DÍA E" not in titulos, f"{n} días: se coló el Día E"


def test_todas_las_variantes_sin_dias_vacios():
    """Ninguna variante, en ninguna semana, debe dejar un día sin bloques."""
    b = BloqueBuilder()
    for n in (3, 4, 5):
        for sem in range(1, 5):
            for dia in b.construir_semana(sem, dias=n).dias:
                assert len(dia.bloques) > 0, f"{n} días · S{sem} · {dia.titulo} sin bloques"


def test_exporter_todas_las_variantes():
    """El exporter debe generar el .xlsx para 3, 4 y 5 días."""
    b = BloqueBuilder()
    with tempfile.TemporaryDirectory() as tmp:
        exp = BloqueExporter(output_dir=tmp, tema=b.program.tema)
        for n in (3, 4, 5):
            s = b.construir_semana(1, dias=n)
            ruta = exp.exportar_semana(s, f"test_recon_{n}d")
            assert os.path.exists(ruta) and os.path.getsize(ruta) > 0


if __name__ == "__main__":
    tests = [
        test_bloque_carga_metadatos,
        test_semana_fuera_de_rango,
        test_orden_dias,
        test_progresion_hip_thrust,
        test_deload_wall_sit_s4,
        test_cue_tecnico_se_repite,
        test_items_fijos_constantes,
        test_nota_global_rodilla,
        test_dias_sin_bloques_vacios,
        test_exporter_genera_archivo,
        # ── variantes de días (3 / 4 / 5) ──
        test_variantes_declaradas,
        test_variante_4_es_el_comportamiento_historico,
        test_variante_dias_invalida,
        test_variante_3_estructura,
        test_variante_3_fusiona_los_dos_lower,
        test_variante_3_sin_repetidos,
        test_variante_3_referencia_cargas_no_las_copia,
        test_variante_5_estructura,
        test_variante_5_muda_accesorios_al_dia_e,
        test_variante_5_conserva_lo_principal,
        test_variante_5_dia_e_sin_duplicados,
        test_variante_5_no_se_pierde_nada,
        test_dia_e_solo_en_variante_5,
        test_todas_las_variantes_sin_dias_vacios,
        test_exporter_todas_las_variantes,
    ]

    print("🧪 Corriendo tests del Bloque Reconstrucción...\n")
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
