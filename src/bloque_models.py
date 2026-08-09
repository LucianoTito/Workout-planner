"""
Modelos del sistema de BLOQUES (programas fijos data-driven).

A diferencia del ciclo CrossFit de 8 semanas (models.py + week_builder.py),
un "bloque" se define 100% en un YAML (data/bloques/*.yaml): cada día tiene
secciones, y cada ejercicio lleva su prescripción por semana (S1..Sn).

Este módulo NO toca el motor CrossFit: es un carril paralelo.
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class EjercicioBloque:
    """Un ejercicio con una prescripción distinta por semana."""
    nombre: str
    semanas: list[str]          # ["S1", "S2", "S3", "S4"] — carga/esquema
    nota: str = ""              # cue técnico fijo (se repite todas las semanas)

    def prescripcion(self, semana: int) -> str:
        """Línea final para la semana pedida (1-indexado)."""
        carga = self.semanas[semana - 1] if 1 <= semana <= len(self.semanas) else ""
        linea = f"{self.nombre} — {carga}" if carga else self.nombre
        if self.nota:
            linea += f" · {self.nota}"
        return linea


@dataclass
class SeccionBloque:
    """Un bloque dentro de un día (CALENTAMIENTO, FUERZA, CORE, ...)."""
    header: str
    items: list[str] = field(default_factory=list)          # líneas fijas
    ejercicios: list[EjercicioBloque] = field(default_factory=list)  # por semana

    def lineas(self, semana: int) -> list[str]:
        """Todas las líneas de la sección para la semana (fijas + por semana)."""
        salida = list(self.items)
        salida += [e.prescripcion(semana) for e in self.ejercicios]
        return salida


@dataclass
class DiaBloque:
    """Definición de un día del bloque (plantilla, todas las semanas)."""
    clave: str                 # "A", "B", "C", "D"
    titulo: str                # "DÍA A"
    subtitulo: str             # "LOWER · Glúteo/Femoral + rodilla"
    duracion: str = ""         # "~75 min"
    secciones: list[SeccionBloque] = field(default_factory=list)


@dataclass
class BloqueProgram:
    """El bloque completo, tal como viene del YAML."""
    nombre: str
    atleta: str
    tema: str
    total_semanas: int
    semana_deload: int
    nota_global: str
    fases: list[str]
    dias: dict[str, DiaBloque]

    def fase(self, semana: int) -> str:
        if 1 <= semana <= len(self.fases):
            return self.fases[semana - 1]
        return f"Semana {semana}"


# ─── Estructuras ya "resueltas" para una semana concreta (las usa el exporter) ───

@dataclass
class DiaSemana:
    titulo: str
    subtitulo: str             # incluye la duración en 2ª línea si existe
    bloques: list[tuple[str, list[str]]]  # [(header, [lineas]), ...]


@dataclass
class SemanaBloque:
    numero_semana: int
    total_semanas: int
    fase: str
    nombre_bloque: str
    atleta: str
    nota_global: str
    tema: str
    dias: list[DiaSemana] = field(default_factory=list)
