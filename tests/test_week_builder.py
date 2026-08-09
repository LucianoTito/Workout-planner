"""
Tests del constructor de semanas.
Verifica que las semanas se armen correctamente.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models import Atleta, TipoDia
from src.progression_loader import ProgressionLoader
from src.week_builder import WeekBuilder


# Atleta de prueba con RM de la novia
ATLETA_TEST = Atleta(
    nombre="Test",
    rm={
        "front_squat": 90,
        "sumo_deadlift": 100,
        "back_squat_cuadriceps": 93,
        "hip_thrust": 150,
        "rumanian_deadlift": 90,
        "clean": 65,
        "clean_and_jerk": 40,
    },
    crucero_rpm=44,
)


def test_loader_semanas_validas():
    """Todas las semanas S1-S8 deben existir."""
    loader = ProgressionLoader("data/progresiones")
    for i in range(1, 9):
        assert loader.validar_semana(i), f"Semana {i} no es válida"


def test_loader_gimnasticos_s3():
    """S3 de gimnásticos debe tener los protocolos correctos."""
    loader = ProgressionLoader("data/progresiones")
    gim = loader.get_gimnasticos(3)
    assert "4 Chest-to-Bar" in gim["c2b"]
    assert "EMOM 7" in gim["t2b"]
    assert "Kick-ups" in gim["hsw"]


def test_loader_strength_porcentajes():
    """Los porcentajes deben seguir la progresión correcta."""
    loader = ProgressionLoader("data/progresiones")
    esperados = {1: 75, 2: 78, 3: 82, 4: 60, 5: 85, 6: 88, 7: 90, 8: 100}
    for sem, pct in esperados.items():
        strength = loader.get_strength(sem)
        fb = strength["fuerza_base"]
        assert fb["porcentaje_rm"] == pct, (
            f"S{sem}: esperaba {pct}%, obtuve {fb['porcentaje_rm']}%"
        )


def test_loader_fases():
    """Las fases deben estar en orden correcto."""
    loader = ProgressionLoader("data/progresiones")
    fases = [loader.get_fase(i) for i in range(1, 9)]
    assert fases[0] == "Adaptación a Carga"
    assert fases[3] == "Descarga Técnica"
    assert fases[7] == "TOMA DE MARCAS"


def test_construir_semana_5_dias():
    """Una semana de 5 días debe tener 5 días con los tipos correctos."""
    builder = WeekBuilder()
    semana = builder.construir_semana(ATLETA_TEST, 3, dias_disponibles=5, seed=42)

    assert len(semana.dias) == 5
    assert semana.dias[0].tipo == TipoDia.A_TREN_INFERIOR_T2B
    assert semana.dias[1].tipo == TipoDia.B_GIMNASIA_C2B
    assert semana.dias[2].tipo == TipoDia.C_FUERZA_ABSOLUTA
    assert semana.dias[3].tipo == TipoDia.D_CAPACIDAD_AEROBICA
    assert semana.dias[4].tipo == TipoDia.E_RECUPERACION_SKILLS


def test_construir_semana_4_dias():
    """Una semana de 4 días no debe tener bloque E separado."""
    builder = WeekBuilder()
    semana = builder.construir_semana(ATLETA_TEST, 3, dias_disponibles=4, seed=42)

    assert len(semana.dias) == 4
    tipos = [d.tipo for d in semana.dias]
    assert TipoDia.E_RECUPERACION_SKILLS not in tipos


def test_construir_semana_3_dias():
    """Una semana de 3 días debe tener exactamente 3 días."""
    builder = WeekBuilder()
    semana = builder.construir_semana(ATLETA_TEST, 3, dias_disponibles=3, seed=42)
    assert len(semana.dias) == 3


def test_pesos_semana_3():
    """S3 con 82% RM: Front Squat 90kg * 0.82 = 73.8 → 75.0kg"""
    builder = WeekBuilder()
    semana = builder.construir_semana(ATLETA_TEST, 3, seed=42)

    dia_a = semana.dias[0]  # Tren Inferior + T2B
    assert len(dia_a.musculacion) > 0
    fs = dia_a.musculacion[0]
    assert fs.nombre == "Front Squat"
    assert fs.porcentaje_rm == 82
    assert fs.peso_kg == 75.0  # 90 * 0.82 = 73.8 → redondeado 75.0


def test_pesos_en_display():
    """El display debe mostrar porcentaje Y kg."""
    builder = WeekBuilder()
    semana = builder.construir_semana(ATLETA_TEST, 3, seed=42)

    dia_c = semana.dias[2]  # Fuerza Absoluta
    for ej in dia_c.musculacion:
        assert "% RM" in ej.display, f"Falta % RM en: {ej.display}"
        assert "kg" in ej.display, f"Falta kg en: {ej.display}"


def test_core_no_vacio():
    """Todos los días deben tener ejercicios de core."""
    builder = WeekBuilder()
    semana = builder.construir_semana(ATLETA_TEST, 1, seed=42)
    for dia in semana.dias:
        assert dia.core_block is not None, f"Día {dia.numero} sin core_block"
        assert len(dia.core_block.ejercicios) > 0, f"Día {dia.numero} sin ejercicios de core"


def test_pacing_solo_dia_d():
    """Solo el día D debe tener pacing."""
    builder = WeekBuilder()
    semana = builder.construir_semana(ATLETA_TEST, 1, seed=42)
    for dia in semana.dias:
        if dia.tipo == TipoDia.D_CAPACIDAD_AEROBICA:
            assert dia.pacing is not None
        else:
            assert dia.pacing is None


def test_skill_t2b_en_dia_a():
    """El día A debe tener skill T2B."""
    builder = WeekBuilder()
    semana = builder.construir_semana(ATLETA_TEST, 1, seed=42)
    dia_a = semana.dias[0]
    assert "T2B" in dia_a.skill_nombre


def test_skill_c2b_en_dia_b():
    """El día B debe tener skill C2B."""
    builder = WeekBuilder()
    semana = builder.construir_semana(ATLETA_TEST, 1, seed=42)
    dia_b = semana.dias[1]
    assert "C2B" in dia_b.skill_nombre or "PULL" in dia_b.skill_nombre


def test_hip_thrust_en_dia_a():
    """El día A debe incluir Hip Thrust además del Front Squat."""
    builder = WeekBuilder()
    semana = builder.construir_semana(ATLETA_TEST, 1, seed=42)
    dia_a = semana.dias[0]
    nombres = [ej.nombre for ej in dia_a.musculacion]
    assert "Front Squat" in nombres
    assert "Hip Thrust" in nombres


def test_hip_thrust_porcentaje_s1():
    """S1: Hip Thrust al 65% de 150kg = 97.5kg."""
    builder = WeekBuilder()
    semana = builder.construir_semana(ATLETA_TEST, 1, seed=42)
    dia_a = semana.dias[0]
    ht = [ej for ej in dia_a.musculacion if ej.nombre == "Hip Thrust"][0]
    assert ht.porcentaje_rm == 65
    assert ht.peso_kg == 97.5  # 150 * 0.65 = 97.5


def test_hip_thrust_muestra_porcentaje_y_kg():
    """El display del Hip Thrust debe incluir % RM y kg."""
    builder = WeekBuilder()
    semana = builder.construir_semana(ATLETA_TEST, 3, seed=42)
    dia_a = semana.dias[0]
    ht = [ej for ej in dia_a.musculacion if ej.nombre == "Hip Thrust"][0]
    assert "% RM" in ht.display
    assert "kg" in ht.display


def test_pliometria_en_dia_e():
    """El día E debe tener pliometría (Seated Box Jump)."""
    builder = WeekBuilder()
    semana = builder.construir_semana(ATLETA_TEST, 1, dias_disponibles=5, seed=42)
    dia_e = semana.dias[4]
    assert dia_e.pliometria is not None
    assert dia_e.pliometria.series == 4
    assert dia_e.pliometria.reps == 3


def test_pliometria_progresion_reps():
    """La pliometría debe cambiar de esquema entre semanas."""
    builder = WeekBuilder()
    s1 = builder.construir_semana(ATLETA_TEST, 1, seed=42)
    s6 = builder.construir_semana(ATLETA_TEST, 6, seed=42)
    plio1 = s1.dias[4].pliometria
    plio6 = s6.dias[4].pliometria
    # S1: 4x3, S6: 5x2 (reps bajan al subir intensidad)
    assert plio1.reps == 3
    assert plio6.reps == 2


def test_accesorios_en_dia_b():
    """El día B debe tener la batería de accesorios."""
    builder = WeekBuilder()
    semana = builder.construir_semana(ATLETA_TEST, 1, dias_disponibles=5, seed=42)
    dia_b = semana.dias[1]
    assert len(dia_b.accesorios_lista) > 0
    nombres = [ej.nombre for ej in dia_b.accesorios_lista]
    assert any("RDL" in n for n in nombres)
    assert any("Landmine" in n for n in nombres)


def test_accesorios_rpe_progresion():
    """El RPE de accesorios debe subir de S1 a S3."""
    builder = WeekBuilder()
    s1 = builder.construir_semana(ATLETA_TEST, 1, seed=42)
    s3 = builder.construir_semana(ATLETA_TEST, 3, seed=42)
    rpe_s1 = s1.dias[1].accesorios_lista[0].rpe
    rpe_s3 = s3.dias[1].accesorios_lista[0].rpe
    assert rpe_s1 == 6
    assert rpe_s3 == 8


def test_accesorios_fijos():
    """Los accesorios deben ser los mismos ejercicios en todas las semanas."""
    builder = WeekBuilder()
    s1 = builder.construir_semana(ATLETA_TEST, 1, seed=42)
    s5 = builder.construir_semana(ATLETA_TEST, 5, seed=42)
    nombres_s1 = [ej.nombre for ej in s1.dias[1].accesorios_lista]
    nombres_s5 = [ej.nombre for ej in s5.dias[1].accesorios_lista]
    assert nombres_s1 == nombres_s5  # Misma batería fija


def test_hip_thrust_descarga_s4():
    """S4 (descarga): Hip Thrust al 55% de 150 = 82.5kg."""
    builder = WeekBuilder()
    semana = builder.construir_semana(ATLETA_TEST, 4, seed=42)
    dia_a = semana.dias[0]
    ht = [ej for ej in dia_a.musculacion if ej.nombre == "Hip Thrust"][0]
    assert ht.porcentaje_rm == 55
    assert ht.peso_kg == 82.5


def test_copenhague_en_dia_a():
    """El Día A debe incluir Copenhague Plank como acompañante."""
    builder = WeekBuilder()
    semana = builder.construir_semana(ATLETA_TEST, 1, seed=42)
    dia_a = semana.dias[0]
    nombres = [ej.nombre for ej in dia_a.acompanantes]
    assert any("Copenhague" in n for n in nombres)


def test_bulgara_en_dia_fuerza():
    """El Día de Fuerza Absoluta debe incluir la Búlgara como acompañante."""
    builder = WeekBuilder()
    semana = builder.construir_semana(ATLETA_TEST, 1, dias_disponibles=5, seed=42)
    dia_c = semana.dias[2]  # Fuerza Absoluta
    nombres = [ej.nombre for ej in dia_c.acompanantes]
    assert any("Búlgara" in n for n in nombres)


def test_bulgara_no_en_dia_a():
    """La Búlgara NO debe estar en el Día A (solo Copenhague)."""
    builder = WeekBuilder()
    semana = builder.construir_semana(ATLETA_TEST, 1, seed=42)
    dia_a = semana.dias[0]
    nombres = [ej.nombre for ej in dia_a.acompanantes]
    assert not any("Búlgara" in n for n in nombres)


def test_hamstring_bridge_en_accesorios():
    """El nuevo Single-Leg Hamstring Bridge debe estar en la batería."""
    builder = WeekBuilder()
    semana = builder.construir_semana(ATLETA_TEST, 1, dias_disponibles=5, seed=42)
    dia_b = semana.dias[1]
    nombres = [ej.nombre for ej in dia_b.accesorios_lista]
    assert any("Hamstring Bridge" in n for n in nombres)
    # El viejo ya no debe estar
    assert not any("Prone Banded" in n for n in nombres)


def test_superserie_reps_fijas():
    """El burnout de glúteo debe tener 15 monster / 20 frog fijos en toda semana."""
    builder = WeekBuilder()
    # S3 tiene reps generales de 8, pero el burnout debe mantener 15 y 20
    for semana_num in [1, 3, 6]:
        semana = builder.construir_semana(ATLETA_TEST, semana_num, dias_disponibles=5, seed=42)
        dia_b = semana.dias[1]
        burnout = [ej for ej in dia_b.accesorios_lista
                   if "Superserie" in ej.display][0]
        assert "15 Monster" in burnout.display, f"S{semana_num}: {burnout.display}"
        assert "20 Frog" in burnout.display, f"S{semana_num}: {burnout.display}"


def test_superserie_orden_monster_primero():
    """Monster Walks debe ir ANTES que Frog Pumps."""
    builder = WeekBuilder()
    semana = builder.construir_semana(ATLETA_TEST, 3, dias_disponibles=5, seed=42)
    dia_b = semana.dias[1]
    burnout = [ej for ej in dia_b.accesorios_lista
               if "Superserie" in ej.display][0]
    pos_monster = burnout.display.find("Monster")
    pos_frog = burnout.display.find("Frog")
    assert pos_monster < pos_frog, "Monster Walks debe ir primero"


def test_superserie_setup_front_rack():
    """El burnout debe aclarar banda + Kb en front rack."""
    builder = WeekBuilder()
    semana = builder.construir_semana(ATLETA_TEST, 3, dias_disponibles=5, seed=42)
    dia_b = semana.dias[1]
    burnout = [ej for ej in dia_b.accesorios_lista
               if "Superserie" in ej.display][0]
    assert "front rack" in burnout.display.lower()
    assert "banda" in burnout.display.lower()
    """El nuevo Single-Leg Hamstring Bridge debe estar en la batería."""
    builder = WeekBuilder()
    semana = builder.construir_semana(ATLETA_TEST, 1, dias_disponibles=5, seed=42)
    dia_b = semana.dias[1]
    nombres = [ej.nombre for ej in dia_b.accesorios_lista]
    assert any("Hamstring Bridge" in n for n in nombres)
    # El viejo ya no debe estar
    assert not any("Prone Banded" in n for n in nombres)


def test_bloques_dia_fuerza_no_tiene_pacing():
    """Verifica que el exportador omita bloques vacíos: Día Fuerza sin pacing."""
    from src.excel_exporter import ExcelExporter
    builder = WeekBuilder()
    semana = builder.construir_semana(ATLETA_TEST, 1, dias_disponibles=5, seed=42)
    exporter = ExcelExporter(output_dir="/tmp/test_output")
    dia_c = semana.dias[2]  # Fuerza Absoluta
    bloques = exporter._bloques_de_dia(dia_c)
    headers = [h for h, _ in bloques]
    assert "PACING" not in headers
    assert "PLIOMETRÍA" not in headers
    assert "MUSCULACIÓN" in headers  # este sí debe estar


def test_bloques_dia_a_estructura():
    """El Día A debe tener CORE, SKILL T2B, MUSCULACIÓN, WOD (y nada de pacing)."""
    from src.excel_exporter import ExcelExporter
    builder = WeekBuilder()
    semana = builder.construir_semana(ATLETA_TEST, 1, seed=42)
    exporter = ExcelExporter(output_dir="/tmp/test_output")
    dia_a = semana.dias[0]
    bloques = exporter._bloques_de_dia(dia_a)
    headers = [h for h, _ in bloques]
    assert "CORE" in headers
    assert "MUSCULACIÓN" in headers
    assert "WOD" in headers
    assert "PACING" not in headers
    assert "ACCESORIOS" not in headers


if __name__ == "__main__":
    tests = [
        test_loader_semanas_validas,
        test_loader_gimnasticos_s3,
        test_loader_strength_porcentajes,
        test_loader_fases,
        test_construir_semana_5_dias,
        test_construir_semana_4_dias,
        test_construir_semana_3_dias,
        test_pesos_semana_3,
        test_pesos_en_display,
        test_core_no_vacio,
        test_pacing_solo_dia_d,
        test_skill_t2b_en_dia_a,
        test_skill_c2b_en_dia_b,
        test_hip_thrust_en_dia_a,
        test_hip_thrust_porcentaje_s1,
        test_hip_thrust_muestra_porcentaje_y_kg,
        test_hip_thrust_descarga_s4,
        test_copenhague_en_dia_a,
        test_bulgara_en_dia_fuerza,
        test_bulgara_no_en_dia_a,
        test_hamstring_bridge_en_accesorios,
        test_superserie_reps_fijas,
        test_superserie_orden_monster_primero,
        test_superserie_setup_front_rack,
        test_bloques_dia_fuerza_no_tiene_pacing,
        test_bloques_dia_a_estructura,
        test_pliometria_en_dia_e,
        test_pliometria_progresion_reps,
        test_accesorios_en_dia_b,
        test_accesorios_rpe_progresion,
        test_accesorios_fijos,
    ]

    print("🧪 Corriendo tests del constructor de semanas...\n")
    passed = 0
    failed = 0

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
