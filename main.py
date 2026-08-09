#!/usr/bin/env python3
"""
🏋️ Planificador de Entrenamiento — CLI
Genera semanas de entrenamiento con progresiones automáticas.
"""

import sys
import math
import yaml
from datetime import datetime
from pathlib import Path

from src.models import Atleta
from src.week_builder import WeekBuilder
from src.excel_exporter import ExcelExporter
from src.rm_calculator import reporte_pesos


MESES_ES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre",
]


def nombre_pestana_desde_fecha(fecha_str: str) -> str:
    """
    Convierte 'dd/mm/aaaa' en 'Mes - Semana N'.
    N = techo(día / 7): días 1-7→1, 8-14→2, 15-21→3, 22-28→4, 29-31→5.
    El mes sale de la propia fecha.
    """
    d = datetime.strptime(fecha_str, "%d/%m/%Y")
    mes = MESES_ES[d.month - 1]
    semana_mes = math.ceil(d.day / 7)
    return f"{mes} - Semana {semana_mes}"


def pedir_fecha() -> str:
    """Pide una fecha dd/mm/aaaa válida (ahora es obligatoria)."""
    while True:
        fecha = input("  → Fecha de inicio (dd/mm/aaaa): ").strip()
        try:
            datetime.strptime(fecha, "%d/%m/%Y")
            return fecha
        except ValueError:
            print("  ❌ Fecha inválida. Formato dd/mm/aaaa (ej. 31/08/2026)")


def confirmar_nombre_pestana(fecha: str) -> str:
    """Sugiere el nombre de la pestaña y permite confirmarlo o corregirlo (Ruta 1)."""
    sugerido = nombre_pestana_desde_fecha(fecha)
    print(f"\n  🏷️  Pestaña sugerida: '{sugerido}'")
    resp = input("  → Enter/s para confirmar, o escribí otro nombre: ").strip()
    if resp == "" or resp.lower() == "s":
        return sugerido
    return resp


def cargar_atleta(nombre_archivo: str) -> Atleta:
    """Carga un perfil de atleta desde YAML."""
    ruta = Path("config/atletas") / f"{nombre_archivo}.yaml"
    if not ruta.exists():
        print(f"  ❌ No encontré el archivo {ruta}")
        sys.exit(1)

    with open(ruta, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return Atleta(
        nombre=data["nombre"],
        rm=data.get("rm", {}),
        crucero_rpm=data.get("crucero_rpm", 0),
        ultimo_testeo=data.get("ultimo_testeo", ""),
        notas=data.get("notas", ""),
    )


def listar_atletas() -> list[str]:
    """Lista los perfiles de atletas disponibles."""
    carpeta = Path("config/atletas")
    return [f.stem for f in carpeta.glob("*.yaml")]


def mostrar_banner():
    print("\n" + "═" * 56)
    print("  🏋️  PLANIFICADOR DE ENTRENAMIENTO — CICLO 8 SEMANAS")
    print("═" * 56)


def menu_principal():
    """Menú principal del CLI."""
    mostrar_banner()
    print("\n  1 │ Generar semana de entrenamiento")
    print("  2 │ Ver ciclo completo (resumen)")
    print("  3 │ Ver RM y pesos por semana")
    print("  4 │ Salir")

    return input("\n  → Opción (1-4): ").strip()


def seleccionar_atleta() -> Atleta:
    """Permite al usuario seleccionar un atleta."""
    atletas = listar_atletas()
    print("\n  📋 Atletas disponibles:")
    for i, nombre in enumerate(atletas, 1):
        print(f"    {i} │ {nombre}")

    idx = int(input(f"\n  → Elegí atleta (1-{len(atletas)}): ")) - 1
    if 0 <= idx < len(atletas):
        atleta = cargar_atleta(atletas[idx])
        print(f"  ✅ Atleta: {atleta.nombre}")
        return atleta
    else:
        print("  ❌ Opción inválida")
        sys.exit(1)


def flujo_generar_semana():
    """Flujo completo para generar una semana."""
    atleta = seleccionar_atleta()

    # Mostrar RM actual
    print(f"\n  📊 RM actual de {atleta.nombre}:")
    for key, val in atleta.rm.items():
        if val > 0:
            nombre = key.replace("_", " ").title()
            print(f"    • {nombre}: {val} kg")
    print(f"    • RPM Crucero: {atleta.crucero_rpm}")

    # Seleccionar semana
    builder = WeekBuilder()
    print("\n  📅 Ciclo de 8 semanas:")
    resumen = builder.loader.resumen_ciclo()
    for s in resumen:
        print(f"    S{s['semana']} │ {s['fase']:<24} │ {s['porcentaje_rm']}% RM")

    semana_num = int(input("\n  → ¿Qué semana del ciclo? (1-8): "))
    if not 1 <= semana_num <= 8:
        print("  ❌ Semana inválida (debe ser 1-8)")
        return

    # Días disponibles
    dias = int(input("  → ¿Cuántos días de entrenamiento? (3-5): "))
    if not 3 <= dias <= 5:
        print("  ❌ Debe ser entre 3 y 5 días")
        return

    if dias < 5:
        print(f"\n  ℹ️  Con {dias} días, la distribución será:")
        if dias == 4:
            print("    Día 1: Tren Inferior + T2B")
            print("    Día 2: Fuerza Absoluta")
            print("    Día 3: Capacidad Aeróbica + Pacing")
            print("    Día 4: Gimnasia + C2B + Skills (HSW/C&J combinados)")
        elif dias == 3:
            print("    Día 1: Tren Inferior + T2B + Skills (HSW/C&J)")
            print("    Día 2: Fuerza Absoluta")
            print("    Día 3: Capacidad Aeróbica + Pacing + C2B")

        confirma = input("  → ¿Confirmar? (s/n): ").strip().lower()
        if confirma != "s":
            print("  ❌ Cancelado")
            return

    # Fecha de inicio (obligatoria: define el nombre de la pestaña)
    fecha = pedir_fecha()

    # Generar
    print(f"\n  ⏳ Generando Semana {semana_num} ({resumen[semana_num - 1]['fase']})...")

    semana = builder.construir_semana(
        atleta=atleta,
        numero_semana=semana_num,
        dias_disponibles=dias,
        fecha_inicio=fecha,
        seed=semana_num * 100,  # Reproducible pero diferente cada semana
    )

    # Preview en consola
    print(f"\n  {'─' * 52}")
    print(f"  SEMANA {semana.numero_semana} — {semana.fase}")
    print(f"  {'─' * 52}")

    for dia in semana.dias:
        print(f"\n  📌 {dia.titulo} │ {dia.subtitulo}")
        print(f"  {'·' * 48}")

        # Core
        cb = dia.core_block
        if cb and cb.ejercicios:
            print(f"  {cb.header}:")
            print(f"    {cb.formato_linea}")
            for ej in cb.ejercicios:
                print(f"    {ej.nombre}")

        # Skill
        if dia.skill_nombre:
            print(f"  {dia.skill_nombre}:")
            print(f"    {dia.skill_gimnastico}")

        # Musculación
        if dia.musculacion or dia.acompanantes:
            print("  MUSCULACIÓN:")
            for ej in dia.musculacion:
                print(f"    {ej.display}")
            for ej in dia.acompanantes:
                print(f"    {ej.display}")

        # Pliometría
        if dia.pliometria:
            p = dia.pliometria
            print("  PLIOMETRÍA:")
            if p.series > 0:
                print(f"    Seated Box Jump {p.series}x{p.reps}")
            else:
                print(f"    Seated Box Jump — TEST")
            print(f"    Altura: {p.altura}")
            print(f"    Foco: {p.foco}")

        # Accesorios (batería)
        if dia.accesorios_lista:
            print("  ACCESORIOS:")
            for ej in dia.accesorios_lista:
                print(f"    {ej.display}")

        # C&J
        if dia.skill_cj:
            print(f"  SKILL C&J:")
            print(f"    {dia.skill_cj}")

        # Pacing
        if dia.pacing:
            p = dia.pacing
            print(f"  PACING ({p.formato}):")
            print(f"    Min Impares: {p.bloque1}")
            print(f"    Min Pares: {p.bloque2}")
            print(f"    Métrica: {p.metrica}")

        print(f"  WOD: [COMPLETAR MANUALMENTE]")

    # Exportar a Excel
    print(f"\n  {'─' * 52}")
    exportar = input("  → ¿Exportar a Excel? (s/n): ").strip().lower()
    if exportar == "s":
        print("\n  🎨 Tema de colores:")
        print("    1 │ Rosa (Brisa)")
        print("    2 │ Arena (Luciano)")
        op_tema = input("  → Elegí tema (1-2) [1]: ").strip()
        tema = "arena" if op_tema == "2" else "rosa"

        exporter = ExcelExporter(tema=tema)
        nombre = f"S{semana.numero_semana}_{atleta.nombre}_{fecha or 'ciclo'}"
        nombre = nombre.replace("/", "-")
        ruta = exporter.exportar_semana(semana, nombre)
        print(f"  ✅ Archivo generado: {ruta}")

        # Ofrecer subida automática a Google Drive
        subir = input("  → ¿Subir a Drive como pestaña del maestro? (s/n): ").strip().lower()
        if subir == "s":
            d = datetime.strptime(fecha, "%d/%m/%Y")
            mes = MESES_ES[d.month - 1]
            nombre_pestana = confirmar_nombre_pestana(fecha)
            nombre_maestro = f"{mes} - {atleta.nombre}"          # Agosto - Brisa
            subcarpeta = f"{atleta.nombre} - {d.year}"           # Brisa - 2026
            subir_a_drive(ruta, nombre_pestana, nombre_maestro, subcarpeta)
        else:
            print(f"  📱 Podés subir el archivo a Drive manualmente cuando quieras")
    else:
        print("  ℹ️  No se exportó a Excel")


def subir_a_drive(ruta_xlsx: str, nombre_pestana: str, nombre_maestro: str, subcarpeta: str):
    """Agrega la semana como una pestaña dentro del Sheets maestro del atleta."""
    try:
        # Importación local: solo se carga si el usuario elige subir.
        from src.drive_uploader import DriveUploader

        print("  ⏳ Conectando con Google Drive...")
        uploader = DriveUploader()
        raiz_id = uploader.obtener_o_crear_carpeta("Workout Planner")
        carpeta_id = uploader.obtener_o_crear_carpeta(subcarpeta, parent_id=raiz_id)

        # Red de seguridad: no pisar una pestaña editada a mano sin avisar
        if uploader.pestana_existe(nombre_maestro, nombre_pestana, carpeta_id):
            print(f"  ⚠️  Ya existe la pestaña '{nombre_pestana}' en '{nombre_maestro}'.")
            resp = input("  → ¿La reemplazo? (s/n): ").strip().lower()
            if resp != "s":
                print("  ❌ Cancelado. No se tocó el maestro.")
                return

        print("  ⏳ Subiendo y agregando la pestaña al maestro...")
        resultado = uploader.agregar_semana_como_pestana(
            ruta_xlsx,
            nombre_pestana=nombre_pestana,
            nombre_maestro=nombre_maestro,
            carpeta_id=carpeta_id,
        )

        print(f"  ✅ ¡Listo! Pestaña '{nombre_pestana}' en '{nombre_maestro}'")
        print(f"  🔗 Link: {resultado['link']}")
    except FileNotFoundError as e:
        print(f"  ❌ {e}")
    except ImportError:
        print("  ❌ Faltan las librerías de Google. Instalá con:")
        print("     pip install google-auth google-auth-oauthlib google-api-python-client")
    except Exception as e:
        print(f"  ❌ Error al subir a Drive: {e}")
        print("  ℹ️  El Excel quedó generado localmente igual.")


def flujo_ver_ciclo():
    """Muestra resumen del ciclo completo."""
    atleta = seleccionar_atleta()
    builder = WeekBuilder()
    print(f"\n{builder.preview_ciclo(atleta)}")


def flujo_ver_pesos():
    """Muestra los pesos calculados para cada semana."""
    atleta = seleccionar_atleta()
    builder = WeekBuilder()

    print(f"\n  📊 TABLA DE PESOS — {atleta.nombre}")
    print(f"  {'─' * 68}")
    print(f"  {'Semana':<8} {'Fase':<24} {'%RM':>4} │ {'Front Sq':>10} {'Sumo DL':>10} {'Back Sq':>10}")
    print(f"  {'─' * 68}")

    for s in builder.loader.resumen_ciclo():
        num = s["semana"]
        fase = s["fase"]
        pct = s["porcentaje_rm"]

        from src.rm_calculator import calcular_peso

        fs = calcular_peso(atleta.rm.get("front_squat", 0), pct) if pct > 0 else 0
        sd = calcular_peso(atleta.rm.get("sumo_deadlift", 0), pct) if pct > 0 else 0
        bs = calcular_peso(atleta.rm.get("back_squat_cuadriceps", 0), pct) if pct > 0 else 0

        if pct == 100:
            print(f"  S{num:<7} {fase:<24} {pct:>3}% │ {'¡TEST!':>10} {'¡TEST!':>10} {'¡TEST!':>10}")
        elif pct == 0:
            print(f"  S{num:<7} {fase:<24}  {'—':>3} │ {'—':>10} {'—':>10} {'—':>10}")
        else:
            print(f"  S{num:<7} {fase:<24} {pct:>3}% │ {fs:>8.1f}kg {sd:>8.1f}kg {bs:>8.1f}kg")

    print(f"  {'─' * 68}")
    print(f"  RM Base: FS={atleta.rm.get('front_squat',0)}kg "
          f"SD={atleta.rm.get('sumo_deadlift',0)}kg "
          f"BS={atleta.rm.get('back_squat_cuadriceps',0)}kg")


def main():
    """Punto de entrada principal."""
    while True:
        opcion = menu_principal()

        if opcion == "1":
            flujo_generar_semana()
        elif opcion == "2":
            flujo_ver_ciclo()
        elif opcion == "3":
            flujo_ver_pesos()
        elif opcion == "4":
            print("\n  👋 ¡Hasta la próxima! A romperla en el box 💪\n")
            break
        else:
            print("  ❌ Opción no válida")

        input("\n  Presioná Enter para continuar...")


if __name__ == "__main__":
    main()
