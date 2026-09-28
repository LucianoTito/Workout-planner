"""
Constructor de BLOQUES.

Lee un YAML de data/bloques/*.yaml y arma la semana N pedida, resolviendo
la prescripción de cada ejercicio para esa semana y omitiendo secciones vacías.

No depende de RM ni del atleta (las cargas son literales del YAML), por eso
es totalmente independiente del motor CrossFit (week_builder.py).

VARIANTES DE DÍAS
─────────────────
`construir_semana(n, dias=X)` arma la semana con X días por semana, según el
bloque `variantes:` del YAML. Tres mecanismos, todos data-driven:

  1. Selección    → la variante lista qué claves de día salen y en qué orden.
  2. Composición  → un día con `componer:` se arma referenciando secciones y
                    ejercicios de otros días (no duplica cargas). Ej: día AD.
  3. Reubicación  → si la variante trae `aplicar_mover_a_e: true`, las secciones
                    y ejercicios marcados `mover_a_e` se mudan al Día E.

Si el YAML no declara `variantes:`, se mantiene el comportamiento histórico
(todos los días, en orden ORDEN_DIAS).
"""

import yaml
from pathlib import Path

from src.bloque_models import (
    EjercicioBloque, SeccionBloque, DiaBloque, BloqueProgram,
    DiaSemana, SemanaBloque, VarianteBloque,
)

# Orden en que se muestran los días cuando el YAML no declara variantes
ORDEN_DIAS = ["A", "B", "C", "D"]

# Clave del día que recibe los accesorios en la variante de 5 días
CLAVE_DIA_ACCESORIOS = "E"


class BloqueBuilder:
    """Carga un bloque desde YAML y construye semanas individuales."""

    def __init__(self, base_dir: str = ".", nombre_bloque: str = "reconstruccion"):
        ruta = Path(base_dir) / "data" / "bloques" / f"{nombre_bloque}.yaml"
        if not ruta.exists():
            raise FileNotFoundError(f"No encontré el bloque: {ruta}")
        with open(ruta, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self.program = self._parse(data)

        # Catálogo de zona 2: opcional. Si no está, los bloques que no lo usan
        # siguen funcionando igual (Reconstrucción, por ejemplo).
        self._z2 = None
        self._z2_ctx: dict = {}
        try:
            from src.z2_selector import Z2Selector
            self._z2 = Z2Selector(str(Path(base_dir) / "data" / "z2_catalog.yaml"))
        except (FileNotFoundError, ValueError, ImportError):
            pass

    # ─────────────────────────── parseo del YAML ───────────────────────────

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
                        mover_a_e=bool(e.get("mover_a_e", False)),
                    )
                    for e in sec.get("ejercicios", [])
                ]
                secciones.append(SeccionBloque(
                    header=sec["header"],
                    items=sec.get("items", []),
                    ejercicios=ejercicios,
                    mover_a_e=bool(sec.get("mover_a_e", False)),
                    header_e=sec.get("header_e", ""),
                    generador=sec.get("generador", ""),
                ))
            dias[str(clave)] = DiaBloque(
                clave=str(clave),
                titulo=d["titulo"],
                subtitulo=d["subtitulo"],
                duracion=d.get("duracion", ""),
                duracion_5=d.get("duracion_5", ""),
                secciones=secciones,
                solo_en_variante=int(d.get("solo_en_variante", 0)),
                orden_secciones=d.get("orden_secciones", []),
                componer=d.get("componer", []),
            )

        variantes: dict[int, VarianteBloque] = {}
        for n, v in (data.get("variantes") or {}).items():
            n = int(n)
            variantes[n] = VarianteBloque(
                n_dias=n,
                dias=[str(c) for c in v["dias"]],
                descripcion=v.get("descripcion", ""),
                aplicar_mover_a_e=bool(v.get("aplicar_mover_a_e", False)),
            )

        default = int(data.get("variante_default", 0))
        if variantes and default not in variantes:
            default = sorted(variantes)[0]

        prog = BloqueProgram(
            nombre=meta["nombre"],
            atleta=meta.get("atleta", ""),
            tema=meta.get("tema", "arena"),
            total_semanas=meta["total_semanas"],
            semana_deload=meta.get("semana_deload", 0),
            nota_global=meta.get("nota_global", ""),
            fases=meta.get("fases", []),
            dias=dias,
            variantes=variantes,
            variante_default=default,
        )
        self._validar_variantes(prog)
        return prog

    @staticmethod
    def _validar_variantes(prog: BloqueProgram) -> None:
        """Falla temprano ante un typo en el YAML, en vez de generar un día vacío."""
        for n, var in prog.variantes.items():
            for clave in var.dias:
                if clave not in prog.dias:
                    raise ValueError(
                        f"Variante de {n} días: el día '{clave}' no existe en `dias:`"
                    )
                dia = prog.dias[clave]
                if dia.solo_en_variante and dia.solo_en_variante != n:
                    raise ValueError(
                        f"Variante de {n} días incluye el día '{clave}', "
                        f"pero está marcado `solo_en_variante: {dia.solo_en_variante}`"
                    )

    # ─────────────────────────── API pública ───────────────────────────

    @property
    def total_semanas(self) -> int:
        return self.program.total_semanas

    @property
    def dias_disponibles(self) -> list[int]:
        """Opciones de días por semana (ej. [3, 4, 5]). Vacío si el YAML no las declara."""
        return self.program.dias_disponibles

    def resumen(self) -> list[dict]:
        """Resumen semana → fase, para mostrar en el CLI."""
        return [
            {"semana": i, "fase": self.program.fase(i),
             "deload": i == self.program.semana_deload}
            for i in range(1, self.total_semanas + 1)
        ]

    def resumen_variantes(self) -> list[dict]:
        """
        Resumen de las variantes de días, para el menú del CLI.

        Cada día viene ya descripto (título, subtítulo y duración) para que el
        CLI no tenga que traducir a mano claves como "F1" o "Z2B". La duración
        se pide para esa variante: la de 5 días usa las sesiones cortas cuando
        el YAML declara `duracion_5`.
        """
        salida = []
        for n in self.program.dias_disponibles:
            var = self.program.variantes[n]
            salida.append({
                "n_dias": n,
                "descripcion": var.descripcion,
                "dias": [
                    {
                        "titulo": self.program.dias[c].titulo,
                        "subtitulo": self.program.dias[c].subtitulo,
                        "duracion": self.program.dias[c].duracion_para(n),
                    }
                    for c in var.dias
                ],
                "default": n == self.program.variante_default,
            })
        return salida

    def construir_semana(self, numero_semana: int, dias: int | None = None,
                         seed: int | None = None,
                         z2_id: str | None = None) -> SemanaBloque:
        """
        Arma la semana pedida (1..total_semanas) con `dias` días de entrenamiento.

        `dias=None` usa `variante_default` del YAML (4 en Reconstrucción), o sea
        el comportamiento histórico.

        `seed` y `z2_id` solo afectan a las secciones con `generador: z2`.
        Si el bloque no las tiene, se ignoran por completo.
        """
        if not 1 <= numero_semana <= self.total_semanas:
            raise ValueError(
                f"Semana {numero_semana} fuera de rango (1-{self.total_semanas})"
            )

        variante = self._resolver_variante(dias)
        claves = self._claves_de_dia(variante)
        aplicar_e = bool(variante and variante.aplicar_mover_a_e)
        n_dias = variante.n_dias if variante else len(claves)

        # Secciones que se mudan al Día E, acumuladas por header de destino.
        # dict conserva orden de inserción → refleja el orden de aparición en A, B, D.
        pendientes_e: dict[str, SeccionBloque] = {}

        self._z2_ctx = {"semana": numero_semana, "seed": seed, "forzar_id": z2_id}

        dias_semana: dict[str, DiaSemana] = {}
        for clave in claves:
            if aplicar_e and clave == CLAVE_DIA_ACCESORIOS:
                continue  # el Día E se arma al final, ya con todo lo recibido
            dias_semana[clave] = self._construir_dia(
                clave, numero_semana, n_dias, aplicar_e, pendientes_e
            )

        if aplicar_e and CLAVE_DIA_ACCESORIOS in claves:
            dias_semana[CLAVE_DIA_ACCESORIOS] = self._construir_dia_accesorios(
                CLAVE_DIA_ACCESORIOS, numero_semana, n_dias, pendientes_e
            )

        return SemanaBloque(
            numero_semana=numero_semana,
            total_semanas=self.total_semanas,
            fase=self.program.fase(numero_semana),
            nombre_bloque=self.program.nombre,
            atleta=self.program.atleta,
            nota_global=self.program.nota_global,
            tema=self.program.tema,
            dias=[dias_semana[c] for c in claves],
            n_dias=n_dias,
        )

    # ─────────────────────────── internos ───────────────────────────

    def _resolver_variante(self, dias: int | None) -> VarianteBloque | None:
        if not self.program.variantes:
            return None  # YAML viejo, sin variantes: comportamiento histórico
        if dias is None:
            dias = self.program.variante_default
        var = self.program.variante(dias)
        if var is None:
            opciones = ", ".join(str(n) for n in self.program.dias_disponibles)
            raise ValueError(f"No existe variante de {dias} días (disponibles: {opciones})")
        return var

    def _claves_de_dia(self, variante: VarianteBloque | None) -> list[str]:
        if variante:
            return list(variante.dias)
        # Sin variantes: respeta ORDEN_DIAS y agrega al final las claves sueltas,
        # salteando los días marcados como exclusivos de una variante.
        claves = [k for k in ORDEN_DIAS if k in self.program.dias]
        claves += [
            k for k, d in self.program.dias.items()
            if k not in claves and not d.solo_en_variante
        ]
        return claves

    def _construir_dia(self, clave, semana, n_dias, aplicar_e, pendientes_e) -> DiaSemana:
        dia = self.program.dias[clave]
        secciones = self._componer(dia) if dia.componer else dia.secciones

        bloques = []
        for sec in secciones:
            if aplicar_e and sec.mover_a_e:
                self._acumular_en_e(pendientes_e, sec, sec.ejercicios, sec.items)
                continue

            if aplicar_e:
                sueltos = [e for e in sec.ejercicios if e.mover_a_e]
                if sueltos:
                    self._acumular_en_e(pendientes_e, sec, sueltos, [])

            lineas = sec.lineas(semana, sin_accesorios=aplicar_e)
            if sec.generador:
                lineas = lineas + self._lineas_generadas(sec.generador, semana)
            if lineas:                       # omite secciones vacías
                bloques.append((sec.header, lineas))

        return self._armar_dia_semana(dia, bloques, n_dias)

    # ── generadores dinámicos ─────────────────────────────────
    def _lineas_generadas(self, generador: str, semana: int) -> list[str]:
        """Líneas que no vienen del YAML del bloque sino de un catálogo aparte."""
        if generador != "z2":
            return []
        if self._z2 is None:
            return ["(catálogo de zona 2 no disponible)"]
        ctx = getattr(self, "_z2_ctx", {})
        sesion = self._z2.seleccionar(
            semana=semana,
            semana_deload=self.program.semana_deload,
            seed=ctx.get("seed"),
            forzar_id=ctx.get("forzar_id"),
        )
        return sesion.to_lines()

    def _construir_dia_accesorios(self, clave, semana, n_dias, pendientes_e) -> DiaSemana:
        """Día E: sus propias secciones + todo lo que le mandaron A, B y D."""
        dia = self.program.dias[clave]

        secciones: dict[str, SeccionBloque] = {}
        for sec in dia.secciones:
            secciones[sec.header] = sec
        for header, sec in pendientes_e.items():
            if header in secciones:          # fusiona con una sección propia del Día E
                base = secciones[header]
                secciones[header] = SeccionBloque(
                    header=header,
                    items=list(base.items) + list(sec.items),
                    ejercicios=list(base.ejercicios) + list(sec.ejercicios),
                )
            else:
                secciones[header] = sec

        # Orden final: el declarado en `orden_secciones`; el resto queda al final.
        orden = [h for h in dia.orden_secciones if h in secciones]
        orden += [h for h in secciones if h not in orden]

        bloques = []
        for header in orden:
            lineas = secciones[header].lineas(semana)
            if lineas:
                bloques.append((header, lineas))

        return self._armar_dia_semana(dia, bloques, n_dias)

    @staticmethod
    def _acumular_en_e(pendientes_e, seccion, ejercicios, items) -> None:
        """
        Suma una sección (o unos ejercicios sueltos) al Día E, fusionando por header.

        Deduplica lo IDÉNTICO: si el CORE de A y el de D mandan los dos
        "Plancha frontal — 3×30s", en el Día E aparece una sola vez. Si difieren
        (distinto texto / distinta prescripción), se conservan las dos.
        """
        destino = seccion.destino_e
        if destino not in pendientes_e:
            pendientes_e[destino] = SeccionBloque(header=destino, items=[], ejercicios=[])
        acum = pendientes_e[destino]

        for item in items:
            if item not in acum.items:
                acum.items.append(item)

        for ej in ejercicios:
            gemelo = next((x for x in acum.ejercicios if x.nombre == ej.nombre), None)
            if gemelo is None:
                acum.ejercicios.append(ej)
            elif gemelo.semanas != ej.semanas or gemelo.nota != ej.nota:
                # Mismo nombre pero distinta prescripción: no se puede fusionar
                # en silencio, así que entra igual (vas a verlo dos veces y decidís).
                acum.ejercicios.append(ej)

    @staticmethod
    def _armar_dia_semana(dia: DiaBloque, bloques: list, n_dias: int) -> DiaSemana:
        subtitulo = dia.subtitulo
        duracion = dia.duracion_para(n_dias)
        if duracion:
            subtitulo = f"{dia.subtitulo}\n{duracion}"
        return DiaSemana(titulo=dia.titulo, subtitulo=subtitulo, bloques=bloques)

    # ── Composición de un día fusionado (ej. AD = A + D) ──

    def _componer(self, dia: DiaBloque) -> list[SeccionBloque]:
        """Resuelve la receta `componer:` en una lista de secciones concretas."""
        salida: list[SeccionBloque] = []
        for spec in dia.componer:
            if "seccion" in spec:
                salida.append(self._componer_seccion_entera(dia, spec))
            elif "header" in spec:
                salida.append(self._componer_seccion_nueva(dia, spec))
            else:
                raise ValueError(
                    f"Día '{dia.clave}': entrada de `componer` sin `seccion` ni `header`"
                )
        return salida

    def _componer_seccion_entera(self, dia: DiaBloque, spec: dict) -> SeccionBloque:
        origen = self._buscar_seccion(dia, spec["dia"], spec["seccion"])
        excluir = set(spec.get("excluir", []))
        for nombre in excluir:
            if not any(e.nombre == nombre for e in origen.ejercicios):
                raise ValueError(
                    f"Día '{dia.clave}': `excluir` apunta a '{nombre}', "
                    f"que no está en {spec['dia']} / {spec['seccion']}"
                )
        return SeccionBloque(
            header=spec.get("header", origen.header),
            items=list(origen.items) + list(spec.get("agregar_items", [])),
            ejercicios=[e for e in origen.ejercicios if e.nombre not in excluir],
        )

    def _componer_seccion_nueva(self, dia: DiaBloque, spec: dict) -> SeccionBloque:
        ejercicios = [
            self._buscar_ejercicio(dia, t["dia"], t["ejercicio"])
            for t in spec.get("tomar", [])
        ]
        return SeccionBloque(
            header=spec["header"],
            items=list(spec.get("items", [])),
            ejercicios=ejercicios,
        )

    def _buscar_seccion(self, dia: DiaBloque, clave_origen: str, header: str) -> SeccionBloque:
        origen = self.program.dias.get(str(clave_origen))
        if origen is None:
            raise ValueError(
                f"Día '{dia.clave}': `componer` referencia el día '{clave_origen}', que no existe"
            )
        for sec in origen.secciones:
            if sec.header == header:
                return sec
        raise ValueError(
            f"Día '{dia.clave}': no encontré la sección '{header}' en el día '{clave_origen}'"
        )

    def _buscar_ejercicio(self, dia: DiaBloque, clave_origen: str, nombre: str) -> EjercicioBloque:
        origen = self.program.dias.get(str(clave_origen))
        if origen is None:
            raise ValueError(
                f"Día '{dia.clave}': `tomar` referencia el día '{clave_origen}', que no existe"
            )
        for sec in origen.secciones:
            for ej in sec.ejercicios:
                if ej.nombre == nombre:
                    return ej
        raise ValueError(
            f"Día '{dia.clave}': no encontré el ejercicio '{nombre}' en el día '{clave_origen}'"
        )
