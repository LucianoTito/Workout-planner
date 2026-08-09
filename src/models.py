"""
Modelos de datos del planificador de entrenamiento.
Usa dataclasses para definir las estructuras principales.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from src.core_selector import CoreBlock


class Fase(Enum):
    ADAPTACION = "Adaptación a Carga"
    INTENSIFICACION_1 = "Intensificación 1"
    INTENSIFICACION_2 = "Intensificación 2"
    DESCARGA = "Descarga Técnica"
    FUERZA_MAXIMA_1 = "Fuerza Máxima 1"
    FUERZA_MAXIMA_2 = "Fuerza Máxima 2"
    PICO_FUERZA = "Pico de Fuerza"
    TOMA_MARCAS = "TOMA DE MARCAS"


class TipoDia(Enum):
    """Los 5 bloques funcionales que rotan en la semana."""
    A_TREN_INFERIOR_T2B = "TREN INFERIOR + SKILL T2B"
    B_GIMNASIA_C2B = "GIMNASIA + SKILL C2B"
    C_FUERZA_ABSOLUTA = "FUERZA ABSOLUTA"
    D_CAPACIDAD_AEROBICA = "CAPACIDAD AERÓBICA + PACING"
    E_RECUPERACION_SKILLS = "RECUPERACIÓN + HSW + C&J"


@dataclass
class Atleta:
    nombre: str
    rm: dict[str, float]       # {"front_squat": 90, "sumo_deadlift": 100, ...}
    crucero_rpm: float
    ultimo_testeo: str = ""
    notas: str = ""


@dataclass
class EjercicioFuerza:
    nombre: str
    series: int
    reps: int
    porcentaje_rm: float       # Ej: 82.0
    peso_kg: float             # Calculado: %RM * RM del atleta
    display: str = ""          # "Front Squat 4x4 al 82% RM (73.8 kg)"

    def generar_display(self) -> str:
        if self.porcentaje_rm == 100:
            self.display = f"{self.nombre} — ¡Testeo de 1 RM Absoluto!"
        elif self.porcentaje_rm == 0:
            self.display = f"{self.nombre} — No aplica esta semana"
        else:
            self.display = (
                f"{self.nombre} {self.series}x{self.reps} "
                f"al {self.porcentaje_rm:.0f}% RM ({self.peso_kg:.1f} kg)"
            )
        return self.display


@dataclass
class CoreExercise:
    nombre: str
    intensidad: str            # "baja", "media", "media-alta", "alta"
    categoria: str             # "anti_extension", "anti_rotacion", etc.


@dataclass
class SeccionPacing:
    formato: str               # "EMOM 20 min"
    bloque1: str               # "45\" Trabajo / 15\" Rest"
    bloque2: str               # "45\" Pedaleo suave / 15\" Rest"
    metrica: str               # "Clavar las 44 RPM"


@dataclass
class SeccionPliometria:
    series: int
    reps: int
    altura: str                # Descripción relativa de altura
    foco: str                  # Foco técnico de la semana

    @property
    def display(self) -> str:
        if self.series == 0:
            return f"Seated Box Jump — {self.altura}"
        return f"Seated Box Jump {self.series}x{self.reps} — {self.altura}"


@dataclass
class AccesorioEjercicio:
    nombre: str
    esquema: str               # "3x12" o "3x8/pierna"
    rpe: int
    nota: str = ""
    display_override: str = ""  # Si está seteado, se usa en vez del display armado

    @property
    def display(self) -> str:
        if self.display_override:
            return self.display_override
        base = f"{self.nombre} {self.esquema}"
        if self.rpe > 0:
            base += f" — RPE {self.rpe}"
        if self.nota:
            base += f" ({self.nota})"
        return base


@dataclass
class DiaEntrenamiento:
    numero: int                # 1-5
    tipo: TipoDia
    core_block: Optional[object] = None  # CoreBlock del core_selector
    skill_gimnastico: str = ""     # Protocolo de gimnásticos
    skill_nombre: str = ""         # "SKILL T2B", "SKILL C2B", etc.
    musculacion: list[EjercicioFuerza] = field(default_factory=list)
    acompanantes: list[AccesorioEjercicio] = field(default_factory=list)
    accesorios: str = ""           # Descripción de accesorios (RPE) - legacy
    skill_cj: str = ""            # Protocolo de Clean & Jerk
    pacing: Optional[SeccionPacing] = None
    pliometria: Optional[SeccionPliometria] = None
    accesorios_lista: list[AccesorioEjercicio] = field(default_factory=list)
    wod: str = "[COMPLETAR MANUALMENTE]"
    notas: str = ""

    @property
    def titulo(self) -> str:
        return f"DÍA {self.numero}"

    @property
    def subtitulo(self) -> str:
        return self.tipo.value


@dataclass
class SemanaEntrenamiento:
    numero_semana: int         # 1-8
    fase: str                  # "Adaptación a Carga", etc.
    atleta: Atleta
    dias: list[DiaEntrenamiento] = field(default_factory=list)
    fecha_inicio: str = ""
    dias_disponibles: int = 5

    @property
    def clave_semana(self) -> str:
        return f"S{self.numero_semana}"
