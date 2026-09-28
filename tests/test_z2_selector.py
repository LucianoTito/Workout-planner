"""
Tests del selector de sesiones de Zona 2.
Corré:  python tests/test_z2_selector.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.z2_selector import Z2Selector, DERIVA_ALTA, DERIVA_SUAVE
from src.bloque_builder import BloqueBuilder

VEDADOS = ["push press", "thruster", "jerk", "press de hombro", "vuelo lateral",
           "pistol", "dobles", "box jump", "muscle-up", "fondos", "press banca"]


def _sel():
    return Z2Selector()


# ═══════════════════════════════════════════════════════════════
# Catálogo
# ═══════════════════════════════════════════════════════════════

def test_catalogo_carga():
    s = _sel()
    assert len(s.todas()) >= 15, f"solo {len(s.todas())} sesiones"


def test_ids_unicos():
    ids = [x.id for x in _sel().todas()]
    assert len(ids) == len(set(ids))


def test_toda_sesion_tiene_estructura():
    for x in _sel().todas():
        assert x.estructura, f"{x.id} sin estructura"
        assert x.duracion and x.formato, f"{x.id} sin duración o formato"


def test_ninguna_sesion_tiene_movimientos_vedados():
    """Hombro derecho y rodilla izquierda: filtros duros."""
    for x in _sel().todas():
        texto = (" ".join(x.estructura) + " " + x.nota).lower()
        for v in VEDADOS:
            assert v not in texto, f"{x.id} incluye '{v}'"


def test_no_hay_carrera():
    """Correr queda fuera hasta confirmar tolerancia de rodilla."""
    for x in _sel().todas():
        texto = (" ".join(x.estructura) + " " + x.nota).lower()
        for palabra in ("correr", "corriendo", "trote", "trotar", "running"):
            assert palabra not in texto, f"{x.id} menciona '{palabra}'"


def test_deriva_declarada():
    validas = {"muy baja", "baja", "moderada", "moderada-alta", "alta"}
    for x in _sel().todas():
        assert x.deriva in validas, f"{x.id}: deriva '{x.deriva}'"


def test_sesiones_de_deriva_alta_avisan():
    for x in _sel().todas():
        if x.deriva in DERIVA_ALTA:
            assert any("135" in l for l in x.to_lines()), f"{x.id} sin aviso de techo"


def test_unilateral_avisa_izquierda():
    for x in _sel().todas():
        if x.unilateral:
            assert any("izquierda" in l.lower() for l in x.to_lines()), x.id


# ═══════════════════════════════════════════════════════════════
# Selección
# ═══════════════════════════════════════════════════════════════

def test_seleccion_reproducible():
    a = [_sel().seleccionar(s, semana_deload=4, seed=7).id for s in range(1, 5)]
    b = [_sel().seleccionar(s, semana_deload=4, seed=7).id for s in range(1, 5)]
    assert a == b, f"{a} != {b}"


def test_no_repite_semana_consecutiva():
    for seed in (None, 1, 42, 99):
        ids = [_sel().seleccionar(s, semana_deload=4, seed=seed).id for s in range(1, 5)]
        for i in range(1, len(ids)):
            assert ids[i] != ids[i - 1], f"seed={seed}: repitió {ids[i]}"


def test_deload_sin_mixtas():
    for seed in (None, 1, 42, 99, 123):
        x = _sel().seleccionar(4, semana_deload=4, seed=seed)
        assert x.categoria != "mixtas", f"seed={seed}: {x.id} en deload"


def test_deload_solo_deriva_suave():
    """
    En descarga el objetivo de pulso baja a 115-125: la sesión no puede ser de
    las que se escapan solas, aunque su categoría esté permitida. El caso que
    lo motivó: bear crawl es `recuperacion` pero tiene deriva moderada.
    """
    for seed in (None, 1, 42, 99, 123, 2026):
        x = _sel().seleccionar(4, semana_deload=4, seed=seed)
        assert x.deriva in DERIVA_SUAVE, f"seed={seed}: {x.id} con deriva '{x.deriva}'"


def test_deriva_alta_no_dos_semanas_seguidas():
    for seed in (None, 1, 42, 99, 123):
        s = _sel()
        ids = [s.seleccionar(w, semana_deload=4, seed=seed) for w in range(1, 5)]
        for i in range(1, len(ids)):
            if ids[i - 1].deriva in DERIVA_ALTA:
                assert ids[i].deriva not in DERIVA_ALTA, \
                    f"seed={seed}: {ids[i-1].id} → {ids[i].id}"


def test_forzar_id():
    x = _sel().seleccionar(1, forzar_id="z2_mix_04")
    assert x.id == "z2_mix_04"


def test_forzar_id_inexistente_falla():
    try:
        _sel().seleccionar(1, forzar_id="no_existe")
        assert False, "debería fallar"
    except ValueError:
        pass


# ═══════════════════════════════════════════════════════════════
# Integración con el motor de bloques
# ═══════════════════════════════════════════════════════════════

def _bloque_aero(b, semana, **kw):
    s = b.construir_semana(semana, dias=4, **kw)
    dia = [d for d in s.dias if d.titulo == "AERÓBICO"][0]
    for h, ls in dia.bloques:
        if "SUGERIDA" in h.upper():
            return ls
    return []


def test_se_inyecta_en_el_dia_aerobico():
    b = BloqueBuilder(nombre_bloque="recomposicion")
    for sem in range(1, 5):
        ls = _bloque_aero(b, sem)
        assert len(ls) > 2, f"S{sem}: sección vacía"


def test_inyeccion_reproducible():
    b = BloqueBuilder(nombre_bloque="recomposicion")
    assert _bloque_aero(b, 2, seed=5) == _bloque_aero(b, 2, seed=5)


def test_z2_id_manda():
    b = BloqueBuilder(nombre_bloque="recomposicion")
    ls = _bloque_aero(b, 1, z2_id="z2_mono_01")
    assert any("Rotación de tres máquinas" in l for l in ls), ls


def test_pacing_no_recibe_sesion_generada():
    """El día PACING es el ancla de RPM: no se le inyecta nada."""
    b = BloqueBuilder(nombre_bloque="recomposicion")
    dia = [d for d in b.construir_semana(1, dias=4).dias if d.titulo == "PACING"][0]
    headers = " ".join(h for h, _ in dia.bloques).upper()
    assert "SUGERIDA" not in headers


def test_reconstruccion_no_se_ve_afectada():
    """El bloque viejo no usa `generador`: tiene que salir idéntico."""
    b = BloqueBuilder(nombre_bloque="reconstruccion")
    s = b.construir_semana(1)
    assert [d.titulo for d in s.dias] == ["DÍA A", "DÍA B", "DÍA C", "DÍA D"]
    for d in s.dias:
        for h, _ in d.bloques:
            assert "SUGERIDA" not in h.upper()


def test_builder_funciona_sin_catalogo(tmpdir=None):
    """Si falta z2_catalog.yaml, el motor no puede romperse."""
    import shutil
    origen, backup = "data/z2_catalog.yaml", "data/z2_catalog.yaml.bak"
    shutil.move(origen, backup)
    try:
        b = BloqueBuilder(nombre_bloque="recomposicion")
        assert b._z2 is None
        s = b.construir_semana(1, dias=4)          # no debe explotar
        assert len(s.dias) == 4
        b2 = BloqueBuilder(nombre_bloque="reconstruccion")
        assert len(b2.construir_semana(1).dias) == 4
    finally:
        shutil.move(backup, origen)


if __name__ == "__main__":
    tests = [
        test_catalogo_carga,
        test_ids_unicos,
        test_toda_sesion_tiene_estructura,
        test_ninguna_sesion_tiene_movimientos_vedados,
        test_no_hay_carrera,
        test_deriva_declarada,
        test_sesiones_de_deriva_alta_avisan,
        test_unilateral_avisa_izquierda,
        test_seleccion_reproducible,
        test_no_repite_semana_consecutiva,
        test_deload_sin_mixtas,
        test_deload_solo_deriva_suave,
        test_deriva_alta_no_dos_semanas_seguidas,
        test_forzar_id,
        test_forzar_id_inexistente_falla,
        test_se_inyecta_en_el_dia_aerobico,
        test_inyeccion_reproducible,
        test_z2_id_manda,
        test_pacing_no_recibe_sesion_generada,
        test_reconstruccion_no_se_ve_afectada,
        test_builder_funciona_sin_catalogo,
    ]

    print("🧪 Corriendo tests del selector de Zona 2...\n")
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
