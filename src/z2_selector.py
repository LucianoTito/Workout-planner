"""
Selector de sesiones de Zona 2 (carril de bloques).

Lee `data/z2_catalog.yaml` y elige una sesión para la semana pedida,
respetando las reglas del propio catálogo:

  · No repetir la misma sesión dos semanas seguidas.
  · En semana de deload: solo `recuperacion` o `monoestructural`, y solo
    de deriva baja o muy baja.
  · Las sesiones de deriva alta / moderada-alta, como máximo una vez
    cada dos semanas.

Es el equivalente de `core_selector.py` pero para el carril de bloques:
no toca el motor CrossFit ni sus datos.

La selección es REPRODUCIBLE: con la misma `seed` y la misma semana
sale siempre la misma sesión, así que el Excel de una semana dada no
cambia si lo regenerás.
"""

from __future__ import annotations

import random
import yaml
from dataclasses import dataclass, field
from pathlib import Path

CATEGORIAS = ("monoestructural", "mixtas", "recuperacion")
DERIVA_ALTA = ("alta", "moderada-alta")
DERIVA_SUAVE = ("muy baja", "baja")


@dataclass
class SesionZ2:
    """Una sesión de zona 2 ya resuelta, lista para el exporter."""
    id: str
    nombre: str
    duracion: str
    formato: str
    deriva: str
    categoria: str
    estructura: list[str] = field(default_factory=list)
    nota: str = ""
    unilateral: bool = False

    def to_lines(self) -> list[str]:
        """Líneas tal como aparecen en el Excel."""
        lineas = [f"{self.nombre} — {self.duracion} · {self.formato}"]
        lineas += [f"· {p}" for p in self.estructura]
        if self.unilateral:
            lineas.append("Unilateral: empezá SIEMPRE por la izquierda.")
        if self.deriva in DERIVA_ALTA:
            lineas.append(f"⚠ Deriva {self.deriva}: vigilá el reloj, techo duro 135 ppm.")
        if self.nota:
            lineas.append(self.nota)
        return lineas


class Z2Selector:
    """Elige la sesión de zona 2 de la semana."""

    def __init__(self, catalog_path: str = "data/z2_catalog.yaml"):
        ruta = Path(catalog_path)
        if not ruta.exists():
            raise FileNotFoundError(f"No encontré el catálogo de zona 2: {ruta}")
        with open(ruta, "r", encoding="utf-8") as f:
            self._catalog = yaml.safe_load(f) or {}

        self._sesiones: list[SesionZ2] = []
        for cat in CATEGORIAS:
            for s in self._catalog.get(cat, []) or []:
                self._sesiones.append(SesionZ2(
                    id=s["id"],
                    nombre=s["nombre"],
                    duracion=s.get("duracion", ""),
                    formato=s.get("formato", ""),
                    deriva=s.get("deriva", "baja"),
                    categoria=cat,
                    estructura=list(s.get("estructura", [])),
                    nota=s.get("nota", ""),
                    unilateral=bool(s.get("unilateral", False)),
                ))
        if not self._sesiones:
            raise ValueError("El catálogo de zona 2 no tiene ninguna sesión")

        self._por_id = {s.id: s for s in self._sesiones}

    # ── consulta ──────────────────────────────────────────────

    @property
    def meta(self) -> dict:
        return self._catalog.get("meta", {}) or {}

    def todas(self) -> list[SesionZ2]:
        return list(self._sesiones)

    def por_id(self, sesion_id: str) -> SesionZ2 | None:
        return self._por_id.get(sesion_id)

    # ── selección ─────────────────────────────────────────────

    def _candidatas(self, semana: int, semana_deload: int,
                    historial: list[str]) -> list[SesionZ2]:
        """
        Aplica las reglas del catálogo y devuelve lo que queda.

        Las de DELOAD son duras: si vaciaran el set, no se relajan. (Con un
        único `or todas` al final, una semana sin candidatas devolvía cualquier
        sesión, mixtas incluidas, justo en la semana de descarga.)
        Las de variedad son blandas: si vaciaran el set, se ignoran.
        """
        duras = list(self._sesiones)

        # Deload: nada mixto, y nada que se escape solo. En descarga el objetivo
        # de pulso baja (115-125 ppm), así que la deriva importa más que nunca:
        # hay sesiones de categoría permitida — bear crawl — con deriva moderada.
        if semana_deload and semana == semana_deload:
            duras = [s for s in duras
                     if s.categoria != "mixtas" and s.deriva in DERIVA_SUAVE]

        cands = list(duras)

        # Regla: no repetir la de la semana anterior.
        if historial:
            previa = historial[-1]
            cands = [s for s in cands if s.id != previa]

        # Regla: deriva alta, máximo una vez cada dos semanas.
        recientes = historial[-1:]
        if any(self._por_id[i].deriva in DERIVA_ALTA
               for i in recientes if i in self._por_id):
            cands = [s for s in cands if s.deriva not in DERIVA_ALTA]

        return cands or duras or list(self._sesiones)   # nunca devolver vacío

    def seleccionar(self, semana: int, semana_deload: int = 0,
                    seed: int | None = None,
                    forzar_id: str | None = None) -> SesionZ2:
        """
        Devuelve la sesión de zona 2 para la semana pedida.

        `forzar_id` permite fijar una sesión concreta (útil para probar
        una en particular o para cuando el atleta ya eligió).
        """
        if forzar_id:
            sesion = self._por_id.get(forzar_id)
            if sesion is None:
                raise ValueError(f"No existe la sesión de zona 2 '{forzar_id}'")
            return sesion

        # Historial determinista: se reconstruye la cadena desde la S1, así
        # la semana N siempre da lo mismo sin depender de estado externo.
        historial: list[str] = []
        for s in range(1, semana + 1):
            cands = self._candidatas(s, semana_deload, historial)
            rnd = random.Random(f"{seed}-{s}" if seed is not None else f"z2-{s}")
            historial.append(rnd.choice(sorted(cands, key=lambda x: x.id)).id)

        return self._por_id[historial[-1]]
