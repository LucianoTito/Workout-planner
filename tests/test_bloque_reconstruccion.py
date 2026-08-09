"""
Tests del Bloque Reconstrucción (carril data-driven, independiente del CrossFit).
Corré:  python tests/test_bloque_reconstruccion.py
"""

import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bloque_builder import BloqueBuilder
from src.bloque_exporter import BloqueExporter


def _lineas_dia(semana, clave_titulo):
    """Devuelve todas las líneas de un día por su título (ej. 'DÍA A')."""
    dia = [d for d in semana.dias if d.titulo == clave_titulo][0]
    lineas = []
    for _, ls in dia.bloques:
        lineas += ls
    return lineas


def test_bloque_carga_metadatos():
    """El bloque debe cargar con 4 semanas, tema arena y 4 días."""
    b = BloqueBuilder()
    assert b.total_semanas == 4
    assert b.program.tema == "arena"
    assert b.program.atleta == "Luciano"
    assert len(b.program.dias) == 4


def test_semana_fuera_de_rango():
    """Semanas 0 y 5 deben fallar."""
    b = BloqueBuilder()
    for mala in (0, 5):
        try:
            b.construir_semana(mala)
            assert False, f"Semana {mala} debería fallar"
        except ValueError:
            pass


def test_orden_dias():
    """Los días deben salir en orden A, B, C, D."""
    b = BloqueBuilder()
    s = b.construir_semana(1)
    titulos = [d.titulo for d in s.dias]
    assert titulos == ["DÍA A", "DÍA B", "DÍA C", "DÍA D"]


def test_progresion_hip_thrust():
    """Hip thrust del Día A debe subir S1→S3 y bajar en el deload S4."""
    b = BloqueBuilder()
    ht1 = [l for l in _lineas_dia(b.construir_semana(1), "DÍA A") if l.startswith("Hip thrust")][0]
    ht3 = [l for l in _lineas_dia(b.construir_semana(3), "DÍA A") if l.startswith("Hip thrust")][0]
    ht4 = [l for l in _lineas_dia(b.construir_semana(4), "DÍA A") if l.startswith("Hip thrust")][0]
    assert "60 kg · 3×12" in ht1
    assert "65 kg" in ht3
    assert "60 kg · 3×10" in ht4   # deload: mismo peso, menos reps


def test_deload_wall_sit_s4():
    """El Wall sit del Día A en S4 debe marcar el deload."""
    b = BloqueBuilder()
    ws4 = [l for l in _lineas_dia(b.construir_semana(4), "DÍA A") if l.startswith("Wall sit")][0]
    assert "4×40s" in ws4
    assert "deload" in ws4.lower()


def test_cue_tecnico_se_repite():
    """El cue fijo (RPE 7) debe aparecer en todas las semanas del Hip thrust."""
    b = BloqueBuilder()
    for sem in (1, 2, 3, 4):
        ht = [l for l in _lineas_dia(b.construir_semana(sem), "DÍA A") if l.startswith("Hip thrust")][0]
        assert "RPE 7" in ht, f"S{sem}: falta el cue -> {ht}"


def test_items_fijos_constantes():
    """El calentamiento del Día A debe ser igual en S1 y S3."""
    b = BloqueBuilder()
    assert "Bici suave — 4 min" in _lineas_dia(b.construir_semana(1), "DÍA A")
    assert "Bici suave — 4 min" in _lineas_dia(b.construir_semana(3), "DÍA A")


def test_nota_global_rodilla():
    """La nota global de la rodilla debe estar presente."""
    b = BloqueBuilder()
    s = b.construir_semana(2)
    assert "Rodilla izq" in s.nota_global


def test_dias_sin_bloques_vacios():
    """Ningún día debe quedar sin bloques."""
    b = BloqueBuilder()
    for sem in range(1, 5):
        for dia in b.construir_semana(sem).dias:
            assert len(dia.bloques) > 0, f"S{sem} {dia.titulo} sin bloques"


def test_exporter_genera_archivo():
    """El exporter debe generar un .xlsx sin errores."""
    b = BloqueBuilder()
    s = b.construir_semana(1)
    with tempfile.TemporaryDirectory() as tmp:
        exp = BloqueExporter(output_dir=tmp, tema=b.program.tema)
        ruta = exp.exportar_semana(s, "test_recon")
        assert os.path.exists(ruta)
        assert os.path.getsize(ruta) > 0


if __name__ == "__main__":
    tests = [
        test_bloque_carga_metadatos,
        test_semana_fuera_de_rango,
        test_orden_dias,
        test_progresion_hip_thrust,
        test_deload_wall_sit_s4,
        test_cue_tecnico_se_repite,
        test_items_fijos_constantes,
        test_nota_global_rodilla,
        test_dias_sin_bloques_vacios,
        test_exporter_genera_archivo,
    ]

    print("🧪 Corriendo tests del Bloque Reconstrucción...\n")
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
