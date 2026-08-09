"""
Calculadora de RM.
Convierte porcentajes de RM a kilogramos reales,
redondeando al múltiplo de 2.5 kg más cercano (discos disponibles en gym).
"""

import math


def calcular_peso(rm: float, porcentaje: float, redondeo: float = 2.5) -> float:
    """
    Calcula el peso real a partir de un RM y un porcentaje.

    Args:
        rm: Repetición máxima en kg (ej: 100)
        porcentaje: Porcentaje del RM (ej: 82 para 82%)
        redondeo: Múltiplo al que redondear (default: 2.5 kg)

    Returns:
        Peso redondeado en kg

    Example:
        >>> calcular_peso(100, 82)
        82.5
        >>> calcular_peso(90, 75)
        67.5
        >>> calcular_peso(93, 82)
        77.5
    """
    peso_exacto = rm * porcentaje / 100
    peso_redondeado = round(peso_exacto / redondeo) * redondeo
    return peso_redondeado


def formatear_ejercicio(nombre: str, series: int, reps: int,
                         porcentaje: float, rm: float) -> str:
    """
    Genera el display completo de un ejercicio con su carga.

    Args:
        nombre: Nombre del ejercicio
        series: Número de series
        reps: Número de repeticiones
        porcentaje: % del RM
        rm: RM del atleta para ese ejercicio

    Returns:
        String formateado: "Front Squat 4x4 al 82% RM (73.8 kg)"

    Example:
        >>> formatear_ejercicio("Front Squat", 4, 4, 82, 90)
        'Front Squat 4x4 al 82% RM (75.0 kg)'
    """
    if porcentaje == 100:
        return f"{nombre} — ¡Testeo de 1 RM Absoluto! (RM actual: {rm} kg)"

    peso = calcular_peso(rm, porcentaje)
    return f"{nombre} {series}x{reps} al {porcentaje:.0f}% RM ({peso:.1f} kg)"


def reporte_pesos(rm_dict: dict, porcentaje: float,
                   series: int, reps: int) -> dict:
    """
    Genera un reporte de pesos para todos los ejercicios de fuerza base.

    Args:
        rm_dict: Dict con los RM del atleta
        porcentaje: % del RM a aplicar
        series: Número de series
        reps: Número de repeticiones

    Returns:
        Dict con ejercicio -> (peso_kg, display_string)

    Example:
        >>> rm = {"front_squat": 90, "sumo_deadlift": 100}
        >>> reporte = reporte_pesos(rm, 82, 4, 4)
    """
    # Mapeo de keys YAML a nombres legibles
    nombres = {
        "front_squat": "Front Squat",
        "sumo_deadlift": "Sumo Deadlift",
        "back_squat_cuadriceps": "Back Squat (Cuádriceps)",
        "hip_thrust": "Hip Thrust",
        "rumanian_deadlift": "Rumanian Deadlift",
        "clean": "Clean",
        "clean_and_jerk": "Clean & Jerk",
    }

    resultado = {}
    for key, rm in rm_dict.items():
        if rm > 0:
            nombre = nombres.get(key, key.replace("_", " ").title())
            peso = calcular_peso(rm, porcentaje)
            display = formatear_ejercicio(nombre, series, reps, porcentaje, rm)
            resultado[key] = {
                "nombre": nombre,
                "rm": rm,
                "porcentaje": porcentaje,
                "peso_kg": peso,
                "display": display,
            }

    return resultado
