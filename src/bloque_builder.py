"""
Constructor de BLOQUES.

Lee un YAML de data/bloques/*.yaml y arma la semana N pedida, resolviendo
la prescripción de cada ejercicio para esa semana y omitiendo secciones vacías.

No depende de RM ni del atleta (las cargas son literales del YAML), por eso
es totalmente independiente del motor CrossFit (week_builder.py).
"""

import yaml
from pathlib import Path

from src.bloque_models import (
    EjercicioBloque, SeccionBloque, DiaBloque, BloqueProgram,
    DiaSemana, SemanaBloque,
)

# Orden en que se muestran los días (columnas del Excel)
ORDEN_DIAS = ["A", "B", "C", "D"]


class BloqueBuilder:
    """Carga un bloque desde YAML y construye semanas individuales."""

    def __init__(self, base_dir: str = ".", nombre_bloque: str = "reconstruccion"):
        ruta = Path(base_dir) / "data" / "bloques" / f"{nombre_bloque}.yaml"
        if not ruta.exists():
            raise FileNotFoundError(f"No encontré el bloque: {ruta}")
        with open(ruta, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self.program = self._parse(data)

    def _parse(self, data: dict) -> BloqueProgram:
        meta = data["meta"]
        dias: dict[str, DiaBloque] = {}
        for clave, d in data["dias"].items():
            secciones = []
            for sec in d.get("secciones", []):
                ejercicios = [
                    EjercicioBloque(
                        nombre=e["nombre"],
                        semanas=e["semanas"],
                        nota=e.get("nota", ""),
                    )
                    for e in sec.get("ejercicios", [])
                ]
                secciones.append(SeccionBloque(
                    header=sec["header"],
                    items=sec.get("items", []),
                    ejercicios=ejercicios,
                ))
            dias[clave] = DiaBloque(
                clave=clave,
                titulo=d["titulo"],
                subtitulo=d["subtitulo"],
                duracion=d.get("duracion", ""),
                secciones=secciones,
            )
        return BloqueProgram(
            nombre=meta["nombre"],
            atleta=meta.get("atleta", ""),
            tema=meta.get("tema", "arena"),
            total_semanas=meta["total_semanas"],
            semana_deload=meta.get("semana_deload", 0),
            nota_global=meta.get("nota_global", ""),
            fases=meta.get("fases", []),
            dias=dias,
        )

    @property
    def total_semanas(self) -> int:
        return self.program.total_semanas

    def resumen(self) -> list[dict]:
        """Resumen semana → fase, para mostrar en el CLI."""
        return [
            {"semana": i, "fase": self.program.fase(i),
             "deload": i == self.program.semana_deload}
            for i in range(1, self.total_semanas + 1)
        ]

    def construir_semana(self, numero_semana: int) -> SemanaBloque:
        """Arma la semana pedida (1..total_semanas)."""
        if not 1 <= numero_semana <= self.total_semanas:
            raise ValueError(
                f"Semana {numero_semana} fuera de rango (1-{self.total_semanas})"
            )

        dias_semana: list[DiaSemana] = []
        # Respeta ORDEN_DIAS; si el YAML trae otras claves, las agrega al final.
        claves = [k for k in ORDEN_DIAS if k in self.program.dias]
        claves += [k for k in self.program.dias if k not in claves]

        for clave in claves:
            dia = self.program.dias[clave]
            bloques = []
            for sec in dia.secciones:
                lineas = sec.lineas(numero_semana)
                if lineas:                       # omite secciones vacías
                    bloques.append((sec.header, lineas))

            subtitulo = dia.subtitulo
            if dia.duracion:
                subtitulo = f"{dia.subtitulo}\n{dia.duracion}"

            dias_semana.append(DiaSemana(
                titulo=dia.titulo,
                subtitulo=subtitulo,
                bloques=bloques,
            ))

        return SemanaBloque(
            numero_semana=numero_semana,
            total_semanas=self.total_semanas,
            fase=self.program.fase(numero_semana),
            nombre_bloque=self.program.nombre,
            atleta=self.program.atleta,
            nota_global=self.program.nota_global,
            tema=self.program.tema,
            dias=dias_semana,
        )
