"""
Constructor de Semana.
Orquesta todos los componentes (progresiones, RM, core) para
generar una semana completa de entrenamiento.
"""

from src.models import (
    Atleta, TipoDia, DiaEntrenamiento, SemanaEntrenamiento,
    EjercicioFuerza, SeccionPacing, SeccionPliometria, AccesorioEjercicio,
)
from src.progression_loader import ProgressionLoader
from src.core_selector import CoreSelector
from src.rm_calculator import calcular_peso, formatear_ejercicio


# ═══════════════════════════════════════════════════════════════
# DISTRIBUCIÓN DE BLOQUES SEGÚN CANTIDAD DE DÍAS
# ═══════════════════════════════════════════════════════════════
#
# 5 días: A, B, C, D, E (todos separados)
# 4 días: A, C, D, B+E (combinar gimnasia + recuperación/skills)
# 3 días: A+E(skills), C, D+B(C2B) (comprimir más)
# ═══════════════════════════════════════════════════════════════

DISTRIBUCION_5_DIAS = [
    TipoDia.A_TREN_INFERIOR_T2B,
    TipoDia.B_GIMNASIA_C2B,
    TipoDia.C_FUERZA_ABSOLUTA,
    TipoDia.D_CAPACIDAD_AEROBICA,
    TipoDia.E_RECUPERACION_SKILLS,
]

DISTRIBUCION_4_DIAS = [
    TipoDia.A_TREN_INFERIOR_T2B,
    TipoDia.C_FUERZA_ABSOLUTA,
    TipoDia.D_CAPACIDAD_AEROBICA,
    TipoDia.B_GIMNASIA_C2B,        # Se le agregan skills de E
]

DISTRIBUCION_3_DIAS = [
    TipoDia.A_TREN_INFERIOR_T2B,   # Se le agregan skills de E
    TipoDia.C_FUERZA_ABSOLUTA,
    TipoDia.D_CAPACIDAD_AEROBICA,  # Se le agrega C2B de B
]


def get_distribucion(dias: int) -> list[TipoDia]:
    """Devuelve la distribución de bloques para N días."""
    if dias >= 5:
        return DISTRIBUCION_5_DIAS
    elif dias == 4:
        return DISTRIBUCION_4_DIAS
    else:
        return DISTRIBUCION_3_DIAS


class WeekBuilder:
    """Construye una semana de entrenamiento completa."""

    def __init__(self, base_dir: str = "."):
        self.loader = ProgressionLoader(f"{base_dir}/data/progresiones")
        self.core_selector = CoreSelector(f"{base_dir}/data/core_catalog.yaml")

    def construir_semana(
        self,
        atleta: Atleta,
        numero_semana: int,
        dias_disponibles: int = 5,
        fecha_inicio: str = "",
        seed: int | None = None,
    ) -> SemanaEntrenamiento:
        """
        Construye una semana completa de entrenamiento.

        Args:
            atleta: Datos del atleta (RM, RPM, etc.)
            numero_semana: Número de semana del ciclo (1-8)
            dias_disponibles: Cuántos días puede entrenar (3-5)
            fecha_inicio: Fecha del primer día de la semana
            seed: Semilla para reproducibilidad del core

        Returns:
            SemanaEntrenamiento completamente armada
        """
        if not self.loader.validar_semana(numero_semana):
            raise ValueError(f"No hay datos para la semana {numero_semana}")

        # Cargar progresiones de esta semana
        gim = self.loader.get_gimnasticos(numero_semana)
        strength = self.loader.get_strength(numero_semana)
        pacing = self.loader.get_pacing(numero_semana)
        fase = self.loader.get_fase(numero_semana)

        # Datos de fuerza base
        fb = strength.get("fuerza_base", {})
        series = fb.get("series", 0)
        reps = fb.get("reps", 0)
        porcentaje = fb.get("porcentaje_rm", 0)

        # Reset del selector de core para la semana
        self.core_selector.reset_semana()

        # Obtener distribución de días
        distribucion = get_distribucion(dias_disponibles)

        # Cargar las nuevas progresiones de esta semana
        hip_thrust_data = self.loader.get_hip_thrust(numero_semana)
        pliometria_data = self.loader.get_pliometria(numero_semana)
        accesorios_data = self.loader.get_accesorios(numero_semana)
        accesorios_ejercicios = self.loader.get_accesorios_ejercicios()
        copenhague_data = self.loader.get_copenhague(numero_semana)
        bulgara_data = self.loader.get_bulgara(numero_semana)

        # Construir cada día
        dias = []
        for i, tipo_dia in enumerate(distribucion, 1):
            dia = self._construir_dia(
                numero=i,
                tipo=tipo_dia,
                atleta=atleta,
                gim=gim,
                strength=strength,
                pacing_data=pacing,
                hip_thrust_data=hip_thrust_data,
                pliometria_data=pliometria_data,
                accesorios_data=accesorios_data,
                accesorios_ejercicios=accesorios_ejercicios,
                copenhague_data=copenhague_data,
                bulgara_data=bulgara_data,
                series=series,
                reps=reps,
                porcentaje=porcentaje,
                dias_disponibles=dias_disponibles,
                seed=(seed + i) if seed is not None else None,
            )
            dias.append(dia)

        return SemanaEntrenamiento(
            numero_semana=numero_semana,
            fase=fase,
            atleta=atleta,
            dias=dias,
            fecha_inicio=fecha_inicio,
            dias_disponibles=dias_disponibles,
        )

    def _construir_dia(
        self,
        numero: int,
        tipo: TipoDia,
        atleta: Atleta,
        gim: dict,
        strength: dict,
        pacing_data: dict,
        hip_thrust_data: dict,
        pliometria_data: dict,
        accesorios_data: dict,
        accesorios_ejercicios: list,
        copenhague_data: dict,
        bulgara_data: dict,
        series: int,
        reps: int,
        porcentaje: float,
        dias_disponibles: int,
        seed: int | None,
    ) -> DiaEntrenamiento:
        """Construye un día individual de entrenamiento."""
        dia = DiaEntrenamiento(numero=numero, tipo=tipo)

        # ─── CORE ───
        dia.core_block = self.core_selector.seleccionar(tipo, seed=seed)

        # ─── SKILLS GIMNÁSTICOS ───
        if tipo == TipoDia.A_TREN_INFERIOR_T2B:
            dia.skill_nombre = "SKILL T2B"
            dia.skill_gimnastico = gim.get("t2b", "")

        elif tipo == TipoDia.B_GIMNASIA_C2B:
            dia.skill_nombre = "SKILL PULL-UPS & C2B"
            dia.skill_gimnastico = gim.get("c2b", "")
            # Si 4 días, B absorbe skills de E
            if dias_disponibles == 4:
                dia.skill_cj = strength.get("skill_cj", "")

        elif tipo == TipoDia.E_RECUPERACION_SKILLS:
            dia.skill_nombre = "SKILL HSW"
            dia.skill_gimnastico = gim.get("hsw", "")
            dia.skill_cj = strength.get("skill_cj", "")

        # Si 3 días: A absorbe HSW+C&J, D absorbe C2B
        if dias_disponibles == 3:
            if tipo == TipoDia.A_TREN_INFERIOR_T2B:
                dia.skill_cj = strength.get("skill_cj", "")
            elif tipo == TipoDia.D_CAPACIDAD_AEROBICA:
                dia.skill_gimnastico = gim.get("c2b", "")
                dia.skill_nombre = "SKILL C2B + PACING"

        # ─── MUSCULACIÓN (FUERZA BASE) ───
        if tipo == TipoDia.A_TREN_INFERIOR_T2B:
            # Front Squat
            rm_fs = atleta.rm.get("front_squat", 0)
            if rm_fs > 0 and porcentaje > 0:
                peso = calcular_peso(rm_fs, porcentaje)
                dia.musculacion.append(EjercicioFuerza(
                    nombre="Front Squat",
                    series=series, reps=reps,
                    porcentaje_rm=porcentaje, peso_kg=peso,
                ))
                dia.musculacion[-1].generar_display()

            # Hip Thrust (progresión propia por % RM)
            rm_ht = atleta.rm.get("hip_thrust", 0)
            ht_pct = hip_thrust_data.get("porcentaje_rm", 0)
            ht_series = hip_thrust_data.get("series", 0)
            ht_reps = hip_thrust_data.get("reps", 0)
            if rm_ht > 0 and ht_pct > 0:
                if ht_pct == 100:
                    # Semana de testeo
                    ej_ht = EjercicioFuerza(
                        nombre="Hip Thrust", series=0, reps=0,
                        porcentaje_rm=100, peso_kg=rm_ht,
                    )
                    ej_ht.generar_display()
                    dia.musculacion.append(ej_ht)
                else:
                    peso_ht = calcular_peso(rm_ht, ht_pct)
                    ej_ht = EjercicioFuerza(
                        nombre="Hip Thrust", series=ht_series, reps=ht_reps,
                        porcentaje_rm=ht_pct, peso_kg=peso_ht,
                    )
                    ej_ht.generar_display()
                    # Agregar tempo/nota del hip thrust
                    tempo = hip_thrust_data.get("descripcion", "")
                    if "Tempo" in tempo:
                        nota_tempo = tempo.split("Tempo:")[-1].strip()
                        ej_ht.display += f" · Tempo: {nota_tempo}"
                    dia.musculacion.append(ej_ht)

            # Copenhague Plank (acompañante fijo del Día 1)
            if copenhague_data and copenhague_data.get("series", 0) > 0:
                cop_series = copenhague_data.get("series", 0)
                cop_reps = copenhague_data.get("reps", 0)
                cop_unidad = copenhague_data.get("unidad", "por pierna")
                esquema = f"{cop_series}x{cop_reps}"
                if cop_unidad:
                    esquema += f"/{cop_unidad.replace('por ', '')}"
                dia.acompanantes.append(AccesorioEjercicio(
                    nombre=copenhague_data.get("nombre", "Copenhague Plank"),
                    esquema=esquema,
                    rpe=0,
                    nota=copenhague_data.get("nota", ""),
                ))

        elif tipo == TipoDia.C_FUERZA_ABSOLUTA:
            # Sumo Deadlift + Back Squat
            for key, nombre in [("sumo_deadlift", "Sumo Deadlift"),
                                ("back_squat_cuadriceps", "Back Squat (Cuádriceps)")]:
                rm_val = atleta.rm.get(key, 0)
                if rm_val > 0 and porcentaje > 0:
                    peso = calcular_peso(rm_val, porcentaje)
                    ej = EjercicioFuerza(
                        nombre=nombre,
                        series=series, reps=reps,
                        porcentaje_rm=porcentaje, peso_kg=peso,
                    )
                    ej.generar_display()
                    dia.musculacion.append(ej)

            # Sentadilla Búlgara (acompañante fijo del Día Fuerza)
            if bulgara_data and bulgara_data.get("series", 0) > 0:
                bul_series = bulgara_data.get("series", 0)
                bul_reps = bulgara_data.get("reps", 0)
                bul_rpe = bulgara_data.get("rpe", 0)
                bul_unidad = bulgara_data.get("unidad", "por pierna")
                esquema = f"{bul_series}x{bul_reps}"
                if bul_unidad:
                    esquema += f"/{bul_unidad.replace('por ', '')}"
                dia.acompanantes.append(AccesorioEjercicio(
                    nombre=bulgara_data.get("nombre", "Sentadilla Búlgara"),
                    esquema=esquema,
                    rpe=bul_rpe,
                    nota=bulgara_data.get("nota", ""),
                ))
        # Pliometría acompaña al Skill C&J → cae en el día que lo absorbe:
        #   5 días → Día E · 4 días → Día B · 3 días → Día A
        plio_en_este_dia = (
            (dias_disponibles == 5 and tipo == TipoDia.E_RECUPERACION_SKILLS)
            or (dias_disponibles == 4 and tipo == TipoDia.B_GIMNASIA_C2B)
            or (dias_disponibles == 3 and tipo == TipoDia.A_TREN_INFERIOR_T2B)
        )
        if plio_en_este_dia and pliometria_data:
            dia.pliometria = SeccionPliometria(
                series=pliometria_data.get("series", 0),
                reps=pliometria_data.get("reps", 0),
                altura=pliometria_data.get("altura", ""),
                foco=pliometria_data.get("foco", ""),
                ejercicio=pliometria_data.get("ejercicio", "Seated Box Jump"),
            )

        # ─── BATERÍA DE ACCESORIOS — va en Día B (Estética) ───
        if tipo == TipoDia.B_GIMNASIA_C2B:
            acc_series = accesorios_data.get("series", 0)
            acc_reps = accesorios_data.get("reps", 0)
            acc_rpe = accesorios_data.get("rpe", 0)
            if acc_series > 0:
                for ej in accesorios_ejercicios:
                    texto_fijo = ej.get("texto_fijo", "")
                    if texto_fijo:
                        # Burnout: reps fijas propias, solo anteponemos series.
                        override = f"{ej['nombre']} — {acc_series} series: {texto_fijo}"
                        nota = ej.get("nota", "")
                        if nota:
                            override += f" ({nota})"
                        dia.accesorios_lista.append(AccesorioEjercicio(
                            nombre=ej["nombre"], esquema="", rpe=0,
                            display_override=override,
                        ))
                    else:
                        unidad = ej.get("unidad", "")
                        esquema = f"{acc_series}x{acc_reps}"
                        if unidad:
                            esquema += f"/{unidad.replace('por ', '')}"
                        dia.accesorios_lista.append(AccesorioEjercicio(
                            nombre=ej["nombre"],
                            esquema=esquema,
                            rpe=acc_rpe,
                            nota=ej.get("nota", ""),
                        ))

        # ─── PACING + 2º toque C&J técnico (completa el estímulo 2×/semana) ───
        if tipo == TipoDia.D_CAPACIDAD_AEROBICA:
            dia.pacing = SeccionPacing(
                formato=pacing_data.get("formato", ""),
                bloque1=pacing_data.get("bloque1", ""),
                bloque2=pacing_data.get("bloque2", ""),
                metrica=pacing_data.get("metrica", ""),
            )
            dia.skill_cj_tecnico = strength.get("skill_cj_ligero", "")

        return dia

    def preview_ciclo(self, atleta: Atleta) -> str:
        """Genera un resumen textual del ciclo completo de 8 semanas."""
        lineas = [
            f"═══ CICLO DE 8 SEMANAS — {atleta.nombre} ═══\n",
            f"RPM Crucero: {atleta.crucero_rpm}",
            f"Último testeo RM: {atleta.ultimo_testeo}\n",
        ]

        for sem in self.loader.resumen_ciclo():
            s = sem["semana"]
            fase = sem["fase"]
            pct = sem["porcentaje_rm"]
            fmt = sem["formato_pacing"]

            # Calcular pesos de referencia
            rm_fs = atleta.rm.get("front_squat", 0)
            peso_fs = calcular_peso(rm_fs, pct) if rm_fs > 0 and pct > 0 else 0

            lineas.append(
                f"S{s} | {fase:<22} | "
                f"Fuerza: {pct}% RM"
                f"{f' (FS: {peso_fs:.1f}kg)' if peso_fs else ''} | "
                f"Pacing: {fmt}"
            )

        return "\n".join(lineas)
