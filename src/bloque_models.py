"""
Modelos del sistema de BLOQUES (programas fijos data-driven).

A diferencia del ciclo CrossFit de 8 semanas (models.py + week_builder.py),
un "bloque" se define 100% en un YAML (data/bloques/*.yaml): cada día tiene
secciones, y cada ejercicio lleva su prescripción por semana (S1..Sn).

Este módulo NO toca el motor CrossFit: es un carril paralelo.

Variantes de días (3 / 4 / 5): el YAML puede declarar qué días salen según
cuántos se entrene por semana. Ver `VarianteBloque` y el bloque `variantes:`
del YAML. Si el YAML no declara variantes, el bloque se comporta como siempre.
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class EjercicioBloque:
    """Un ejercicio con una prescripción distinta por semana."""
    nombre: str
    semanas: list[str]          # ["S1", "S2", "S3", "S4"] — carga/esquema
    nota: str = ""              # cue técnico fijo (se repite todas las semanas)
    mover_a_e: bool = False     # en la variante de 5 días, se muda al Día E

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
    mover_a_e: bool = False     # en la variante de 5 días, la sección entera va al Día E
    header_e: str = ""          # header bajo el que cae en el Día E (default: header)
    generador: str = ""         # si != "", el motor inyecta líneas generadas (ej. "z2")

    @property
    def destino_e(self) -> str:
        """Header con el que esta sección (o sus ejercicios sueltos) aterriza en el Día E."""
        return self.header_e or self.header

    def lineas(self, semana: int, sin_accesorios: bool = False) -> list[str]:
        """
        Todas las líneas de la sección para la semana (fijas + por semana).

        sin_accesorios=True omite los ejercicios marcados `mover_a_e`
        (se usa en la variante de 5 días, donde esos ejercicios van al Día E).
        """
        salida = list(self.items)
        for e in self.ejercicios:
            if sin_accesorios and e.mover_a_e:
                continue
            salida.append(e.prescripcion(semana))
        return salida

    def tiene_contenido(self, semana: int, sin_accesorios: bool = False) -> bool:
        return bool(self.lineas(semana, sin_accesorios))


@dataclass
class DiaBloque:
    """Definición de un día del bloque (plantilla, todas las semanas)."""
    clave: str                 # "A", "B", "C", "D", "E", "AD"
    titulo: str                # "DÍA A"
    subtitulo: str             # "LOWER · Glúteo/Femoral + rodilla"
    duracion: str = ""         # "~75 min"
    duracion_5: str = ""       # duración cuando se entrena 5 días (sesión corta)
    secciones: list[SeccionBloque] = field(default_factory=list)
    # ── Solo para días especiales de una variante ──
    solo_en_variante: int = 0                                # 0 = disponible siempre
    orden_secciones: list[str] = field(default_factory=list)  # orden final (Día E)
    componer: list[dict] = field(default_factory=list)        # receta de fusión (Día AD)

    def duracion_para(self, n_dias: int) -> str:
        """Duración a mostrar según la variante (5 días = sesiones cortas)."""
        if n_dias == 5 and self.duracion_5:
            return self.duracion_5
        return self.duracion


@dataclass
class VarianteBloque:
    """Una configuración de días por semana (3, 4 o 5 días)."""
    n_dias: int
    dias: list[str]                    # claves de día, en orden de columna
    descripcion: str = ""
    aplicar_mover_a_e: bool = False    # activa las marcas `mover_a_e` del YAML


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
    variantes: dict[int, VarianteBloque] = field(default_factory=dict)
    variante_default: int = 0

    def fase(self, semana: int) -> str:
        if 1 <= semana <= len(self.fases):
            return self.fases[semana - 1]
        return f"Semana {semana}"

    def variante(self, n_dias: int) -> VarianteBloque | None:
        return self.variantes.get(n_dias)

    @property
    def dias_disponibles(self) -> list[int]:
        """Opciones de días por semana, ordenadas (ej. [3, 4, 5])."""
        return sorted(self.variantes.keys())


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
    n_dias: int = 0            # variante usada (3, 4 o 5)
