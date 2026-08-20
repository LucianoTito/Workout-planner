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

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markup import escape
from rich import box

from src.models import Atleta
from src.week_builder import WeekBuilder
from src.excel_exporter import ExcelExporter
from src.rm_calculator import reporte_pesos
from src.bloque_builder import BloqueBuilder
from src.bloque_exporter import BloqueExporter


console = Console(highlight=False)


# ── Paleta de color (C3 · Dorado profundo) ───────────────────────────
# Un solo lugar para cambiar tonos: editá acá y afecta todo el CLI.
PAL = {
    "border":  "#b8860b",        # bordes de paneles / reglas
    "title":   "bold #cba135",   # títulos de paneles
    "num":     "bold #d9b74a",   # números de opción / semana
    "section": "bold #b8860b",   # encabezados de tabla y de sección
    "ok":      "#8fbf6f",        # éxito
    "danger":  "bold #a8432f",   # errores / TEST
    "accent":  "bold #c79a2e",   # días, avisos, énfasis
    "prompt":  "#c79a2e",        # flecha de los prompts
}


# ── Helpers de presentación ──────────────────────────────────────────
def say(msg="", style=None):
    """Imprime texto literal (sin parsear markup), con estilo opcional a toda la línea."""
    console.print(msg, style=style, markup=False, soft_wrap=True)


def ask(msg=""):
    """Prompt con flecha dorada; el texto del mensaje se escapa para no romper por corchetes."""
    return console.input(f"  [{PAL['prompt']}]→[/] " + escape(msg))


def ok(msg):
    say(msg, style=PAL["ok"])


def err(msg):
    say(msg, style=PAL["danger"])


def info(msg):
    say(msg, style="dim")


def warn(msg):
    say(msg, style=PAL["accent"])


def head(msg):
    say(msg, style=PAL["section"])


def sep(titulo=""):
    console.rule(f"[{PAL['title']}]{escape(titulo)}[/]" if titulo else "", style=PAL["border"])


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
        fecha = ask("Fecha de inicio (dd/mm/aaaa): ").strip()
        try:
            datetime.strptime(fecha, "%d/%m/%Y")
            return fecha
        except ValueError:
            err("  ❌ Fecha inválida. Formato dd/mm/aaaa (ej. 31/08/2026)")


def confirmar_nombre_pestana(fecha: str) -> str:
    """Sugiere el nombre de la pestaña y permite confirmarlo o corregirlo (Ruta 1)."""
    sugerido = nombre_pestana_desde_fecha(fecha)
    console.print(f"\n  🏷️  Pestaña sugerida: [{PAL['title']}]{escape(sugerido)}[/]")
    resp = ask("Enter/s para confirmar, o escribí otro nombre: ").strip()
    if resp == "" or resp.lower() == "s":
        return sugerido
    return resp


def cargar_atleta(nombre_archivo: str) -> Atleta:
    """Carga un perfil de atleta desde YAML."""
    ruta = Path("config/atletas") / f"{nombre_archivo}.yaml"
    if not ruta.exists():
        err(f"  ❌ No encontré el archivo {ruta}")
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
    console.print(Panel(
        f"[{PAL['title']}]🏋️  PLANIFICADOR DE ENTRENAMIENTO[/]\n[dim]Ciclo de 8 semanas[/]",
        box=box.ROUNDED, border_style=PAL["border"], padding=(0, 2)))


def menu_principal():
    """Menú principal del CLI."""
    mostrar_banner()
    tabla = Table(box=box.SIMPLE_HEAD, header_style=PAL["section"], padding=(0, 1))
    tabla.add_column("#", justify="center", style=PAL["num"], no_wrap=True)
    tabla.add_column("Opción", style="white")
    tabla.add_row("1", "Generar semana de entrenamiento")
    tabla.add_row("2", "Ver ciclo completo (resumen)")
    tabla.add_row("3", "Ver RM y pesos por semana")
    tabla.add_row("4", "Generar semana de Reconstrucción")
    tabla.add_row("5", f"[{PAL['danger']}]Salir[/]")
    console.print(tabla)
    return console.input(f"\n  [{PAL['prompt']}]→[/] Opción (1-5): ").strip()


def seleccionar_atleta() -> Atleta:
    """Permite al usuario seleccionar un atleta."""
    atletas = listar_atletas()
    head("\n  📋 Atletas disponibles:")
    tabla = Table(box=box.ROUNDED, header_style=PAL["section"], padding=(0, 1))
    tabla.add_column("#", justify="center", style=PAL["num"])
    tabla.add_column("Atleta", style="white")
    for i, archivo in enumerate(atletas, 1):
        tabla.add_row(str(i), escape(cargar_atleta(archivo).nombre))  # "Brisa" / "Luciano"
    console.print(tabla)

    idx = int(console.input(f"\n  [{PAL['prompt']}]→[/] Elegí atleta (1-{len(atletas)}): ")) - 1
    if 0 <= idx < len(atletas):
        atleta = cargar_atleta(atletas[idx])
        console.print(f"  [{PAL['ok']}]✅ Atleta:[/] [bold]{escape(atleta.nombre)}[/]")
        return atleta
    else:
        err("  ❌ Opción inválida")
        sys.exit(1)


def flujo_generar_semana():
    """Flujo completo para generar una semana."""
    atleta = seleccionar_atleta()

    # Mostrar RM actual
    head(f"\n  📊 RM actual de {atleta.nombre}:")
    for key, val in atleta.rm.items():
        if val > 0:
            nombre = key.replace("_", " ").title()
            say(f"    • {nombre}: {val} kg")
    say(f"    • RPM Crucero: {atleta.crucero_rpm}")

    # Seleccionar semana
    builder = WeekBuilder()
    head("\n  📅 Ciclo de 8 semanas:")
    resumen = builder.loader.resumen_ciclo()
    tabla = Table(box=box.SIMPLE, header_style=PAL["section"], padding=(0, 1))
    tabla.add_column("Sem", justify="center", style=PAL["num"])
    tabla.add_column("Fase", style="white")
    tabla.add_column("%RM", justify="right", style=PAL["ok"])
    for s in resumen:
        tabla.add_row(f"S{s['semana']}", s['fase'], f"{s['porcentaje_rm']}%")
    console.print(tabla)

    semana_num = int(ask("¿Qué semana del ciclo? (1-8): "))
    if not 1 <= semana_num <= 8:
        err("  ❌ Semana inválida (debe ser 1-8)")
        return

    # Días disponibles
    dias = int(ask("¿Cuántos días de entrenamiento? (3-5): "))
    if not 3 <= dias <= 5:
        err("  ❌ Debe ser entre 3 y 5 días")
        return

    if dias < 5:
        info(f"\n  ℹ️  Con {dias} días, la distribución será:")
        if dias == 4:
            say("    Día 1: Tren Inferior + T2B")
            say("    Día 2: Fuerza Absoluta")
            say("    Día 3: Capacidad Aeróbica + Pacing")
            say("    Día 4: Gimnasia + C2B + Skills (HSW/C&J combinados)")
        elif dias == 3:
            say("    Día 1: Tren Inferior + T2B + Skills (HSW/C&J)")
            say("    Día 2: Fuerza Absoluta")
            say("    Día 3: Capacidad Aeróbica + Pacing + C2B")

        confirma = ask("¿Confirmar? (s/n): ").strip().lower()
        if confirma != "s":
            err("  ❌ Cancelado")
            return

    # Fecha de inicio (obligatoria: define el nombre de la pestaña)
    fecha = pedir_fecha()

    # Generar
    console.print(f"\n  [{PAL['accent']}]⏳ Generando Semana {semana_num} "
                  f"({escape(resumen[semana_num - 1]['fase'])})...[/]")

    semana = builder.construir_semana(
        atleta=atleta,
        numero_semana=semana_num,
        dias_disponibles=dias,
        fecha_inicio=fecha,
        seed=semana_num * 100,  # Reproducible pero diferente cada semana
    )

    # Preview en consola
    sep(f"SEMANA {semana.numero_semana} — {semana.fase}")

    for dia in semana.dias:
        console.print(f"\n  [{PAL['accent']}]📌 {escape(dia.titulo)}[/] "
                      f"[dim]│ {escape(dia.subtitulo)}[/]")
        say("  " + "·" * 48, style="dim")

        # Core
        cb = dia.core_block
        if cb and cb.ejercicios:
            head(f"  {cb.header}:")
            say(f"    {cb.formato_linea}")
            for ej in cb.ejercicios:
                say(f"    {ej.nombre}")

        # Skill
        if dia.skill_nombre:
            head(f"  {dia.skill_nombre}:")
            say(f"    {dia.skill_gimnastico}")

        # Musculación
        if dia.musculacion or dia.acompanantes:
            head("  MUSCULACIÓN:")
            for ej in dia.musculacion:
                say(f"    {ej.display}")
            for ej in dia.acompanantes:
                say(f"    {ej.display}")

        # Pliometría
        if dia.pliometria:
            p = dia.pliometria
            head("  PLIOMETRÍA:")
            if p.series > 0:
                say(f"    {p.ejercicio} {p.series}x{p.reps}")
                say(f"    Altura: {p.altura}")
            else:
                say(f"    {p.ejercicio} — {p.altura}")
            if p.foco:
                say(f"    Foco: {p.foco}")

        # Accesorios (batería)
        if dia.accesorios_lista:
            head("  ACCESORIOS:")
            for ej in dia.accesorios_lista:
                say(f"    {ej.display}")

        # C&J
        if dia.skill_cj:
            head("  SKILL C&J:")
            say(f"    {dia.skill_cj}")

        # C&J técnico (2º toque ligero, 2×/sem)
        if dia.skill_cj_tecnico:
            head("  SKILL C&J (TÉCNICO):")
            say(f"    {dia.skill_cj_tecnico}")

        # Pacing
        if dia.pacing:
            p = dia.pacing
            head(f"  PACING ({p.formato}):")
            say(f"    Min Impares: {p.bloque1}")
            say(f"    Min Pares: {p.bloque2}")
            say(f"    Métrica: {p.metrica}")

        say("  WOD: [COMPLETAR MANUALMENTE]", style="dim")

    # Exportar a Excel
    sep()
    exportar = ask("¿Exportar a Excel? (s/n): ").strip().lower()
    if exportar == "s":
        head("\n  🎨 Tema de colores:")
        tabla = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
        tabla.add_column("#", justify="center", style=PAL["num"])
        tabla.add_column("Tema", style="white")
        tabla.add_row("1", "Rosa (Brisa)")
        tabla.add_row("2", "Arena (Luciano)")
        console.print(tabla)
        op_tema = ask("Elegí tema (1-2) [1]: ").strip()
        tema = "arena" if op_tema == "2" else "rosa"

        exporter = ExcelExporter(tema=tema)
        nombre = f"S{semana.numero_semana}_{atleta.nombre}_{fecha or 'ciclo'}"
        nombre = nombre.replace("/", "-")
        ruta = exporter.exportar_semana(semana, nombre)
        ok(f"  ✅ Archivo generado: {ruta}")

        # Ofrecer subida automática a Google Drive
        subir = ask("¿Subir a Drive como pestaña del maestro? (s/n): ").strip().lower()
        if subir == "s":
            d = datetime.strptime(fecha, "%d/%m/%Y")
            mes = MESES_ES[d.month - 1]
            nombre_pestana = confirmar_nombre_pestana(fecha)
            nombre_maestro = f"{mes} - {atleta.nombre}"          # Agosto - Brisa
            subcarpeta = f"{atleta.nombre} - {d.year}"           # Brisa - 2026
            subir_a_drive(ruta, nombre_pestana, nombre_maestro, subcarpeta)
        else:
            info("  📱 Podés subir el archivo a Drive manualmente cuando quieras")
    else:
        info("  ℹ️  No se exportó a Excel")


def subir_a_drive(ruta_xlsx: str, nombre_pestana: str, nombre_maestro: str, subcarpeta: str):
    """Agrega la semana como una pestaña dentro del Sheets maestro del atleta."""
    try:
        # Importación local: solo se carga si el usuario elige subir.
        from src.drive_uploader import DriveUploader

        info("  ⏳ Conectando con Google Drive...")
        uploader = DriveUploader()
        raiz_id = uploader.obtener_o_crear_carpeta("Workout Planner")
        carpeta_id = uploader.obtener_o_crear_carpeta(subcarpeta, parent_id=raiz_id)

        # Red de seguridad: no pisar una pestaña editada a mano sin avisar
        if uploader.pestana_existe(nombre_maestro, nombre_pestana, carpeta_id):
            warn(f"  ⚠️  Ya existe la pestaña '{nombre_pestana}' en '{nombre_maestro}'.")
            resp = ask("¿La reemplazo? (s/n): ").strip().lower()
            if resp != "s":
                err("  ❌ Cancelado. No se tocó el maestro.")
                return

        info("  ⏳ Subiendo y agregando la pestaña al maestro...")
        resultado = uploader.agregar_semana_como_pestana(
            ruta_xlsx,
            nombre_pestana=nombre_pestana,
            nombre_maestro=nombre_maestro,
            carpeta_id=carpeta_id,
        )

        ok(f"  ✅ ¡Listo! Pestaña '{nombre_pestana}' en '{nombre_maestro}'")
        say(f"  🔗 Link: {resultado['link']}", style="blue")
    except FileNotFoundError as e:
        err(f"  ❌ {e}")
    except ImportError:
        err("  ❌ Faltan las librerías de Google. Instalá con:")
        info("     pip install google-auth google-auth-oauthlib google-api-python-client")
    except Exception as e:
        err(f"  ❌ Error al subir a Drive: {e}")
        info("  ℹ️  El Excel quedó generado localmente igual.")


def flujo_ver_ciclo():
    """Muestra resumen del ciclo completo."""
    from src.rm_calculator import calcular_peso

    atleta = seleccionar_atleta()
    builder = WeekBuilder()

    console.print(Panel(
        f"[{PAL['title']}]📅 CICLO DE 8 SEMANAS — {escape(atleta.nombre)}[/]\n"
        f"[dim]RPM Crucero: {atleta.crucero_rpm}   ·   "
        f"Último testeo RM: {escape(str(atleta.ultimo_testeo))}[/]",
        box=box.ROUNDED, border_style=PAL["border"], padding=(0, 2)))

    tabla = Table(box=box.SIMPLE_HEAD, header_style=PAL["section"], padding=(0, 1))
    tabla.add_column("Sem", justify="center", style=PAL["num"])
    tabla.add_column("Fase", style="white")
    tabla.add_column("%RM", justify="right", style=PAL["ok"])
    tabla.add_column("Front Sq", justify="right")
    tabla.add_column("Pacing", style="white")

    for sem in builder.loader.resumen_ciclo():
        s = sem["semana"]
        fase = sem["fase"]
        pct = sem["porcentaje_rm"]
        fmt = sem["formato_pacing"]
        rm_fs = atleta.rm.get("front_squat", 0)
        peso_fs = calcular_peso(rm_fs, pct) if rm_fs > 0 and pct > 0 else 0

        if pct == 100:
            pct_txt = f"[{PAL['danger']}]100%[/]"
            fs_txt = f"[{PAL['danger']}]¡TEST![/]"
        elif pct == 0:
            pct_txt, fs_txt = "—", "—"
        else:
            pct_txt = f"{pct}%"
            fs_txt = f"{peso_fs:.1f} kg" if peso_fs else "—"

        tabla.add_row(f"S{s}", fase, pct_txt, fs_txt, fmt)

    console.print(tabla)


def flujo_ver_pesos():
    """Muestra los pesos calculados para cada semana."""
    from src.rm_calculator import calcular_peso

    atleta = seleccionar_atleta()
    builder = WeekBuilder()

    head(f"\n  📊 TABLA DE PESOS — {atleta.nombre}")
    tabla = Table(box=box.SIMPLE_HEAD, header_style=PAL["section"], padding=(0, 1))
    tabla.add_column("Sem", justify="center", style=PAL["num"])
    tabla.add_column("Fase", style="white")
    tabla.add_column("%RM", justify="right", style=PAL["ok"])
    tabla.add_column("Front Sq", justify="right")
    tabla.add_column("Sumo DL", justify="right")
    tabla.add_column("Back Sq", justify="right")

    for s in builder.loader.resumen_ciclo():
        num = s["semana"]
        fase = s["fase"]
        pct = s["porcentaje_rm"]

        fs = calcular_peso(atleta.rm.get("front_squat", 0), pct) if pct > 0 else 0
        sd = calcular_peso(atleta.rm.get("sumo_deadlift", 0), pct) if pct > 0 else 0
        bs = calcular_peso(atleta.rm.get("back_squat_cuadriceps", 0), pct) if pct > 0 else 0

        if pct == 100:
            tabla.add_row(f"S{num}", fase, f"{pct}%",
                          f"[{PAL['danger']}]¡TEST![/]", f"[{PAL['danger']}]¡TEST![/]",
                          f"[{PAL['danger']}]¡TEST![/]")
        elif pct == 0:
            tabla.add_row(f"S{num}", fase, "—", "—", "—", "—")
        else:
            tabla.add_row(f"S{num}", fase, f"{pct}%",
                          f"{fs:.1f} kg", f"{sd:.1f} kg", f"{bs:.1f} kg")

    console.print(tabla)
    say(f"  RM Base: FS={atleta.rm.get('front_squat', 0)}kg "
        f"SD={atleta.rm.get('sumo_deadlift', 0)}kg "
        f"BS={atleta.rm.get('back_squat_cuadriceps', 0)}kg", style="dim")


def pedir_dias_bloque(builder):
    """
    Pregunta cuántos días por semana se entrenan y muestra qué días arma cada
    variante, para confirmar antes de generar.

    Devuelve el número elegido, None si el bloque no declara variantes
    (comportamiento histórico), o False si el usuario canceló.
    """
    variantes = builder.resumen_variantes()
    if not variantes:
        return None

    opciones = [v["n_dias"] for v in variantes]
    default = next((v["n_dias"] for v in variantes if v["default"]), opciones[0])

    head("\n  🗓️  ¿Cuántos días por semana vas a entrenar?")
    tabla = Table(box=box.SIMPLE, header_style=PAL["section"], padding=(0, 1))
    tabla.add_column("Días", justify="center", style=PAL["num"])
    tabla.add_column("Estructura", style="white")
    tabla.add_column("Sesiones", style="dim")
    for v in variantes:
        marca = "  ← por defecto" if v["default"] else ""
        tabla.add_row(f"{v['n_dias']}{marca}", v["descripcion"],
                      " · ".join(t.replace("DÍA ", "") for t in v["titulos"]))
    console.print(tabla)

    rango = "/".join(str(o) for o in opciones)
    resp = ask(f"Días ({rango}) [{default}]: ").strip()
    if resp == "":
        return default
    try:
        elegido = int(resp)
    except ValueError:
        err("  ❌ Ingresá un número")
        return False
    if elegido not in opciones:
        err(f"  ❌ Opción inválida (disponibles: {rango})")
        return False

    # Preview de la distribución antes de generar
    var = next(v for v in variantes if v["n_dias"] == elegido)
    info(f"\n  ℹ️  Con {elegido} días, la semana queda así:")
    for titulo in var["titulos"]:
        say(f"    {titulo}")
    if elegido != default:
        if ask("¿Confirmar? (s/n): ").strip().lower() != "s":
            err("  ❌ Cancelado")
            return False
    return elegido


def flujo_generar_reconstruccion():
    """Flujo para generar una semana del Bloque Reconstrucción (4 semanas)."""
    builder = BloqueBuilder()
    prog = builder.program

    console.print(Panel(
        f"[{PAL['title']}]🦵 {escape(prog.nombre.upper())}[/]\n"
        f"[dim]{escape(prog.atleta)} · {builder.total_semanas} semanas[/]",
        box=box.ROUNDED, border_style=PAL["border"], padding=(0, 2)))
    tabla = Table(box=box.SIMPLE, header_style=PAL["section"], padding=(0, 1))
    tabla.add_column("Sem", justify="center", style=PAL["num"])
    tabla.add_column("Fase", style="white")
    for r in builder.resumen():
        marca = "  ← deload" if r["deload"] else ""
        tabla.add_row(f"S{r['semana']}", f"{r['fase']}{marca}")
    console.print(tabla)

    try:
        semana_num = int(ask(f"¿Qué semana del bloque? (1-{builder.total_semanas}): "))
    except ValueError:
        err("  ❌ Ingresá un número")
        return
    if not 1 <= semana_num <= builder.total_semanas:
        err(f"  ❌ Semana inválida (1-{builder.total_semanas})")
        return

    dias = pedir_dias_bloque(builder)
    if dias is False:                      # cancelado en la confirmación
        return

    fecha = pedir_fecha()
    semana = builder.construir_semana(semana_num, dias=dias)

    # Preview en consola
    sep(f"{semana.nombre_bloque.upper()} — SEMANA {semana.numero_semana} de "
        f"{semana.total_semanas} · {semana.fase}")
    if semana.nota_global:
        warn(f"  ⚠️  {semana.nota_global}")
    for dia in semana.dias:
        console.print(f"\n  [{PAL['accent']}]📌 {escape(dia.titulo)}[/] "
                      f"[dim]│ {escape(dia.subtitulo.replace(chr(10), ' · '))}[/]")
        say("  " + "·" * 48, style="dim")
        for header_txt, lineas in dia.bloques:
            head(f"  {header_txt}:")
            for linea in lineas:
                say(f"    {linea}")

    # Exportar
    sep()
    if ask("¿Exportar a Excel? (s/n): ").strip().lower() != "s":
        info("  ℹ️  No se exportó a Excel")
        return

    exporter = BloqueExporter(tema=prog.tema)
    # El sufijo de días solo se agrega si NO es la variante por defecto,
    # así los archivos de 4 días conservan el nombre de siempre.
    sufijo = "" if dias in (None, prog.variante_default) else f"_{dias}dias"
    nombre = (f"S{semana.numero_semana}_{prog.nombre.replace(' ', '_')}"
              f"_{fecha}{sufijo}").replace("/", "-")
    ruta = exporter.exportar_semana(semana, nombre)
    ok(f"  ✅ Archivo generado: {ruta}")

    if ask("¿Subir a Drive como pestaña del maestro? (s/n): ").strip().lower() == "s":
        d = datetime.strptime(fecha, "%d/%m/%Y")
        mes = MESES_ES[d.month - 1]
        nombre_pestana = confirmar_nombre_pestana(fecha)
        subir_a_drive(ruta, nombre_pestana, f"{mes} - {prog.atleta}", f"{prog.atleta} - {d.year}")
    else:
        info("  📱 Podés subir el archivo a Drive manualmente cuando quieras")


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
            flujo_generar_reconstruccion()
        elif opcion == "5":
            console.print(f"\n  [{PAL['accent']}]👋 ¡Hasta la próxima! A romperla en el box 💪[/]\n")
            break
        else:
            err("  ❌ Opción no válida")

        console.input("\n  [dim]Presioná Enter para continuar...[/]")


if __name__ == "__main__":
    main()
