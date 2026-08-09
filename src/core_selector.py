"""
Selector Inteligente de Core.
Elige los ejercicios de core más apropiados según el tipo de día,
evitando fatigar los mismos grupos musculares que el trabajo principal.

Formato de salida:
  - Rounds: "3 Rounds" + ejercicios con reps
  - Tabata: "Tabata XX" x YY"" + ejercicios (por tiempo)
"""

import yaml
import random
from pathlib import Path
from dataclasses import dataclass
from src.models import TipoDia, CoreExercise


@dataclass
class CoreBlock:
    """Bloque completo de core para un día."""
    header: str                    # "CORE" o "ESTABILIDAD"
    formato_linea: str             # "3 Rounds" o "Tabata 25\" ON - 10\" OFF"
    ejercicios: list[CoreExercise]

    def to_lines(self) -> list[str]:
        """Genera las líneas tal como aparecen en el Excel."""
        lineas = [self.formato_linea]
        for ej in self.ejercicios:
            lineas.append(ej.nombre)
        return lineas


class CoreSelector:
    """Selecciona ejercicios de core según el tipo de día."""

    DIA_A_CLAVE = {
        TipoDia.A_TREN_INFERIOR_T2B: "dia_a_tren_inferior_t2b",
        TipoDia.B_GIMNASIA_C2B: "dia_b_gimnasia_c2b",
        TipoDia.C_FUERZA_ABSOLUTA: "dia_c_fuerza_absoluta",
        TipoDia.D_CAPACIDAD_AEROBICA: "dia_d_capacidad_aerobica",
        TipoDia.E_RECUPERACION_SKILLS: "dia_e_recuperacion_skills",
    }

    ORDEN_INTENSIDAD = {
        "baja": 1,
        "media": 2,
        "media-alta": 3,
        "alta": 4,
    }

    def __init__(self, catalog_path: str = "data/core_catalog.yaml"):
        with open(catalog_path, "r", encoding="utf-8") as f:
            self._catalog = yaml.safe_load(f)

        # Construir pool de ejercicios por categoría
        self._pools = {}
        categorias = [
            "anti_extension", "anti_rotacion",
            "flexion_dinamica", "carries", "complementarios",
        ]
        for cat in categorias:
            self._pools[cat] = [
                CoreExercise(
                    nombre=ej["nombre"],
                    intensidad=ej["intensidad"],
                    categoria=cat,
                )
                for ej in self._catalog.get(cat, [])
            ]

        self._seleccion_config = self._catalog.get("seleccion_por_dia", {})
        self._usados_semana: set[str] = set()

    def reset_semana(self):
        """Resetea el registro de ejercicios usados (llamar al inicio de cada semana)."""
        self._usados_semana = set()

    def seleccionar(self, tipo_dia: TipoDia, seed: int | None = None) -> CoreBlock:
        """
        Selecciona ejercicios de core apropiados para un tipo de día.

        Returns:
            CoreBlock con header, formato y ejercicios seleccionados
        """
        if seed is not None:
            random.seed(seed)

        clave = self.DIA_A_CLAVE.get(tipo_dia)
        if not clave or clave not in self._seleccion_config:
            return CoreBlock(header="CORE", formato_linea="3 Rounds", ejercicios=[])

        config = self._seleccion_config[clave]
        categorias = config.get("categorias", [])
        cantidad = config.get("cantidad", 2)
        intensidad_max = config.get("intensidad_max", "alta")
        max_nivel = self.ORDEN_INTENSIDAD.get(intensidad_max, 4)
        header = config.get("header", "CORE")

        # Construir línea de formato
        formato = config.get("formato", "rounds")
        if formato == "tabata":
            trabajo = config.get("tabata_trabajo", "30\"")
            descanso = config.get("tabata_descanso", "15\"")
            formato_linea = f"Tabata {trabajo} ON - {descanso} OFF"
        else:
            rondas = config.get("rondas", 3)
            formato_linea = f"{rondas} Rounds"

        # Construir pool filtrado
        candidatos = []
        for cat in categorias:
            for ej in self._pools.get(cat, []):
                nivel = self.ORDEN_INTENSIDAD.get(ej.intensidad, 2)
                if nivel <= max_nivel and ej.nombre not in self._usados_semana:
                    candidatos.append(ej)

        # Seleccionar con variedad: uno de cada categoría primero
        seleccionados = []
        for cat in categorias:
            disponibles = [c for c in candidatos
                           if c.categoria == cat and c not in seleccionados]
            if disponibles:
                elegido = random.choice(disponibles)
                seleccionados.append(elegido)
                if len(seleccionados) >= cantidad:
                    break

        # Si faltan, completar de cualquier categoría
        while len(seleccionados) < cantidad:
            restantes = [c for c in candidatos if c not in seleccionados]
            if not restantes:
                break
            seleccionados.append(random.choice(restantes))

        # Registrar como usados esta semana
        for ej in seleccionados:
            self._usados_semana.add(ej.nombre)

        return CoreBlock(
            header=header,
            formato_linea=formato_linea,
            ejercicios=seleccionados,
        )

    def get_nota_dia(self, tipo_dia: TipoDia) -> str:
        """Devuelve la nota explicativa de por qué se eligió ese tipo de core."""
        clave = self.DIA_A_CLAVE.get(tipo_dia, "")
        config = self._seleccion_config.get(clave, {})
        return config.get("nota", "")
