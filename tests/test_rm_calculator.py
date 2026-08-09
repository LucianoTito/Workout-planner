"""
Tests del calculador de RM.
Verifica que los cálculos de porcentajes y redondeo sean correctos.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rm_calculator import calcular_peso, formatear_ejercicio, reporte_pesos


def test_calculo_basico():
    """82% de 100kg = 82.5kg (redondeado a 2.5)"""
    assert calcular_peso(100, 82) == 82.5


def test_calculo_front_squat():
    """75% de 90kg = 67.5kg"""
    assert calcular_peso(90, 75) == 67.5


def test_calculo_sumo_dl():
    """82% de 100kg = 82.5kg"""
    assert calcular_peso(100, 82) == 82.5


def test_calculo_back_squat():
    """82% de 93kg = 75.0kg (redondeo)"""
    resultado = calcular_peso(93, 82)
    # 93 * 0.82 = 76.26 → redondeado a 2.5 → 77.5
    assert resultado == 77.5


def test_calculo_descarga():
    """60% de 90kg = 55.0kg"""
    resultado = calcular_peso(90, 60)
    # 90 * 0.60 = 54 → redondeado a 2.5 → 55.0
    assert resultado == 55.0


def test_calculo_pico_fuerza():
    """90% de 100kg = 90.0kg"""
    assert calcular_peso(100, 90) == 90.0


def test_calculo_hip_thrust():
    """75% de 150kg = 112.5kg"""
    assert calcular_peso(150, 75) == 112.5


def test_formatear_ejercicio_normal():
    """Verifica formato: 'Nombre SxR al X% RM (Y kg)'"""
    resultado = formatear_ejercicio("Front Squat", 4, 4, 82, 90)
    assert "Front Squat" in resultado
    assert "4x4" in resultado
    assert "82% RM" in resultado
    assert "kg" in resultado


def test_formatear_ejercicio_testeo():
    """Semana 8 = testeo de RM"""
    resultado = formatear_ejercicio("Front Squat", 0, 0, 100, 90)
    assert "Testeo" in resultado
    assert "90 kg" in resultado


def test_reporte_pesos():
    """Verifica reporte completo con múltiples ejercicios."""
    rm = {"front_squat": 90, "sumo_deadlift": 100}
    reporte = reporte_pesos(rm, 82, 4, 4)

    assert "front_squat" in reporte
    assert "sumo_deadlift" in reporte
    assert reporte["front_squat"]["peso_kg"] == 75.0
    assert reporte["sumo_deadlift"]["peso_kg"] == 82.5


def test_redondeo_a_multiplo_2_5():
    """Todos los pesos deben ser múltiplos de 2.5"""
    casos = [
        (90, 75),   # 67.5
        (93, 82),   # 76.26 → 77.5
        (100, 88),  # 88.0 → 87.5
        (65, 70),   # 45.5 → 45.0
        (150, 60),  # 90.0
    ]
    for rm, pct in casos:
        peso = calcular_peso(rm, pct)
        assert peso % 2.5 == 0, f"RM={rm}, {pct}% = {peso} no es múltiplo de 2.5"


if __name__ == "__main__":
    tests = [
        test_calculo_basico,
        test_calculo_front_squat,
        test_calculo_sumo_dl,
        test_calculo_back_squat,
        test_calculo_descarga,
        test_calculo_pico_fuerza,
        test_calculo_hip_thrust,
        test_formatear_ejercicio_normal,
        test_formatear_ejercicio_testeo,
        test_reporte_pesos,
        test_redondeo_a_multiplo_2_5,
    ]

    print("🧪 Corriendo tests del calculador de RM...\n")
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
