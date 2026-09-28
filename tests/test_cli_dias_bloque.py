"""
Tests de la pantalla "¿Cuántos días por semana vas a entrenar?" (menú 4).
Corré:  python tests/test_cli_dias_bloque.py

El motor ya sabe qué días arma cada variante; lo que se prueba acá es que esa
información llegue al CLI DESCRIPTA — que nadie tenga que adivinar qué es "Z2B"
ni qué "DÍA A" le tocó, porque en Reconstrucción hay dos distintos.
"""

import io
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console

import main as cli
from src.bloque_builder import BloqueBuilder

BLOQUES = ("recomposicion", "reconstruccion")


def _capturar(fn, *args, ancho=120):
    """
    Corre fn con la consola del CLI redirigida a memoria.
    Devuelve (texto impreso, valor devuelto).
    """
    original = cli.console
    buffer = io.StringIO()
    cli.console = Console(file=buffer, width=ancho, highlight=False, no_color=True)
    try:
        resultado = fn(*args)
    finally:
        cli.console = original
    return buffer.getvalue(), resultado


def _pantalla(builder, *respuestas):
    """Corre pedir_dias_bloque() con respuestas fijas. Devuelve (texto, elegido)."""
    original = cli.ask
    it = iter(respuestas)
    cli.ask = lambda msg="": next(it, "")
    try:
        return _capturar(cli.pedir_dias_bloque, builder)
    finally:
        cli.ask = original


def _lineas_leyenda(bloque):
    variantes = BloqueBuilder(nombre_bloque=bloque).resumen_variantes()
    texto, _ = _capturar(cli.leyenda_dias, variantes)
    return variantes, [l.strip() for l in texto.splitlines() if l.strip()]


# ═══════════════════════════════════════════════════════════════
# Los datos que el CLI necesita para describir cada día
# ═══════════════════════════════════════════════════════════════

def test_resumen_variantes_describe_cada_dia():
    """Cada día de cada variante viene con título, subtítulo y duración."""
    for bloque in BLOQUES:
        for v in BloqueBuilder(nombre_bloque=bloque).resumen_variantes():
            assert v["dias"], f"{bloque} · {v['n_dias']}d: sin días"
            for d in v["dias"]:
                for campo in ("titulo", "subtitulo", "duracion"):
                    assert d.get(campo), (
                        f"{bloque} · {v['n_dias']}d · {d.get('titulo')}: falta {campo}")


def test_duracion_es_la_de_la_variante():
    """
    Reconstrucción acorta las sesiones en la variante de 5 días (`duracion_5`).
    El menú tiene que mostrar la duración real de la variante elegida, no la
    genérica: si dice ~75 min y vas a entrenar ~55, el dato miente.
    """
    variantes = {v["n_dias"]: v for v in
                 BloqueBuilder(nombre_bloque="reconstruccion").resumen_variantes()}

    def dia_a(n):
        return [d for d in variantes[n]["dias"] if d["titulo"] == "DÍA A"][0]

    assert dia_a(4)["duracion"] == "~75 min", dia_a(4)
    assert dia_a(5)["duracion"] == "~55 min", (
        f"con 5 días el DÍA A dura ~55 min, no {dia_a(5)['duracion']}")


# ═══════════════════════════════════════════════════════════════
# Helpers de presentación
# ═══════════════════════════════════════════════════════════════

def test_clave_visible():
    assert cli.clave_visible("DÍA F1") == "F1"
    assert cli.clave_visible("DÍA Z2B") == "Z2B"
    assert cli.clave_visible("A") == "A"


def test_enumerar_dias():
    assert cli.enumerar_dias([5]) == "5"
    assert cli.enumerar_dias([4, 5]) == "4 y 5"
    assert cli.enumerar_dias([3, 4, 5]) == "3, 4 y 5"


# ═══════════════════════════════════════════════════════════════
# La leyenda: traducir las claves antes de elegir
# ═══════════════════════════════════════════════════════════════

def test_leyenda_traduce_todas_las_claves():
    """Ninguna clave de la columna 'Sesiones' puede quedar sin explicación."""
    for bloque in BLOQUES:
        variantes = BloqueBuilder(nombre_bloque=bloque).resumen_variantes()
        texto, _ = _capturar(cli.leyenda_dias, variantes)
        for v in variantes:
            for d in v["dias"]:
                assert d["subtitulo"] in texto, (
                    f"{bloque}: '{d['titulo']}' sin descripción en la leyenda")


def test_leyenda_marca_los_dias_opcionales():
    """
    El piso innegociable va sin aclaración porque está en todas las variantes;
    los días opcionales tienen que avisar en cuáles aparecen.

    Los días salen del YAML a propósito, sin nombrarlos acá: el bloque activo ya
    cambió de claves una vez (F1/Z2/Z2B → FUERZA A/PACING/AERÓBICO) y un test que
    los hardcodea se rompe por el cambio de nombre, no por un bug.
    """
    for bloque in BLOQUES:
        variantes, lineas = _lineas_leyenda(bloque)
        apariciones = {}
        for v in variantes:
            for d in v["dias"]:
                apariciones.setdefault(
                    (cli.clave_visible(d["titulo"]), d["subtitulo"]), []).append(v["n_dias"])

        for (clave, subtitulo), en_variantes in apariciones.items():
            match = [l for l in lineas if l.startswith(clave) and subtitulo in l]
            assert match, f"{bloque}: '{clave}' no aparece en la leyenda"
            linea = match[0]
            # La aclaración de variantes va al final y siempre cierra con "días)".
            # (No alcanza con buscar un paréntesis: hay subtítulos que ya traen.)
            aclara = linea.endswith("días)")
            if len(en_variantes) == len(variantes):
                assert not aclara, (
                    f"{bloque}: '{clave}' está en todas las variantes, "
                    f"no lleva aclaración -> {linea}")
            else:
                assert aclara, (
                    f"{bloque}: '{clave}' no está en todas y no lo aclara -> {linea}")
                assert cli.enumerar_dias(en_variantes) in linea, (
                    f"{bloque}: '{clave}' aclara mal las variantes -> {linea}")


def test_leyenda_distingue_dias_homonimos():
    """
    En Reconstrucción el 'DÍA A' de la variante de 3 días es otro día que el de
    4 y 5 (clave AD vs A). La leyenda tiene que mostrar los dos, aclarando
    cuál es cuál, en vez de pisar uno con el otro.
    """
    _, todas = _lineas_leyenda("reconstruccion")
    lineas = [l for l in todas if l.split()[0] == "A"]
    assert len(lineas) == 2, f"Esperaba dos entradas para 'A', hay {len(lineas)}: {lineas}"
    assert "solo con 3 días" in lineas[0]
    assert "con 4 y 5 días" in lineas[1]
    assert lineas[0] != lineas[1]


# ═══════════════════════════════════════════════════════════════
# El flujo completo de la pantalla
# ═══════════════════════════════════════════════════════════════

def test_preview_describe_los_dias_elegidos():
    """Al confirmar, cada día sale con su subtítulo y su duración."""
    b = BloqueBuilder(nombre_bloque="recomposicion")
    texto, _ = _pantalla(b, "5", "s")

    esperado = {d["titulo"]: d for d in
                [v for v in b.resumen_variantes() if v["n_dias"] == 5][0]["dias"]}
    preview = texto.split("la semana queda así:")[1]
    for titulo, d in esperado.items():
        assert titulo in preview, f"falta {titulo} en el preview"
        assert d["subtitulo"] in preview, f"{titulo} sin subtítulo"
        assert d["duracion"] in preview, f"{titulo} sin duración"


def test_devuelve_el_default_con_enter():
    """Enter sigue devolviendo la variante por defecto, sin preguntar nada más."""
    _, elegido = _pantalla(BloqueBuilder(nombre_bloque="recomposicion"), "")
    assert elegido == 4


def test_opcion_invalida_no_rompe():
    b = BloqueBuilder(nombre_bloque="recomposicion")
    for mala in ("7", "hola"):
        _, resultado = _pantalla(b, mala)
        assert resultado is False, f"'{mala}' debería devolver False"


if __name__ == "__main__":
    tests = [
        test_resumen_variantes_describe_cada_dia,
        test_duracion_es_la_de_la_variante,
        test_clave_visible,
        test_enumerar_dias,
        test_leyenda_traduce_todas_las_claves,
        test_leyenda_marca_los_dias_opcionales,
        test_leyenda_distingue_dias_homonimos,
        test_preview_describe_los_dias_elegidos,
        test_devuelve_el_default_con_enter,
        test_opcion_invalida_no_rompe,
    ]

    print("🧪 Corriendo tests de la pantalla de días del menú 4...\n")
    passed = failed = 0
    for test in tests:
        try:
            test()
            print(f"  ✅ {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  ❌ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ {test.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n📊 Resultados: {passed} pasaron, {failed} fallaron")
    sys.exit(1 if failed else 0)
