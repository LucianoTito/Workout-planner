"""
Cargador de Progresiones.
Lee los archivos YAML de progresiones y devuelve los datos
correspondientes a cada semana del ciclo.
"""

import yaml
from pathlib import Path


class ProgressionLoader:
    """Carga y gestiona las tablas de progresión desde archivos YAML."""

    def __init__(self, data_dir: str = "data/progresiones"):
        self.data_dir = Path(data_dir)
        self._gimnasticos = None
        self._strength = None
        self._pacing = None
        self._hip_thrust = None
        self._pliometria = None
        self._accesorios = None
        self._acompanantes = None

    def _cargar_yaml(self, nombre: str) -> dict:
        """Carga un archivo YAML y devuelve su contenido."""
        ruta = self.data_dir / f"{nombre}.yaml"
        with open(ruta, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    @property
    def gimnasticos(self) -> dict:
        if self._gimnasticos is None:
            self._gimnasticos = self._cargar_yaml("gimnasticos")
        return self._gimnasticos

    @property
    def strength(self) -> dict:
        if self._strength is None:
            self._strength = self._cargar_yaml("strength")
        return self._strength

    @property
    def pacing(self) -> dict:
        if self._pacing is None:
            self._pacing = self._cargar_yaml("pacing")
        return self._pacing

    @property
    def hip_thrust(self) -> dict:
        if self._hip_thrust is None:
            self._hip_thrust = self._cargar_yaml("hip_thrust")
        return self._hip_thrust

    @property
    def pliometria(self) -> dict:
        if self._pliometria is None:
            self._pliometria = self._cargar_yaml("pliometria")
        return self._pliometria

    @property
    def accesorios(self) -> dict:
        if self._accesorios is None:
            self._accesorios = self._cargar_yaml("accesorios")
        return self._accesorios

    @property
    def acompanantes(self) -> dict:
        if self._acompanantes is None:
            self._acompanantes = self._cargar_yaml("acompanantes")
        return self._acompanantes

    def get_gimnasticos(self, semana: int) -> dict:
        """
        Devuelve los protocolos de gimnásticos para una semana.

        Returns:
            {"c2b": "...", "t2b": "...", "hsw": "..."}
        """
        clave = f"S{semana}"
        return self.gimnasticos["semanas"].get(clave, {})

    def get_strength(self, semana: int) -> dict:
        """
        Devuelve los datos de fuerza/levantamiento para una semana.

        Returns:
            {
                "fase": "Intensificación 2",
                "fuerza_base": {"series": 4, "reps": 4, "porcentaje_rm": 82, ...},
                "skill_cj": "4 Rondas: ...",
                "accesorios": {"series": 3, "reps": 6, "intensidad": "RPE 8-9", ...}
            }
        """
        clave = f"S{semana}"
        return self.strength["semanas"].get(clave, {})

    def get_pacing(self, semana: int) -> dict:
        """
        Devuelve el protocolo de pacing para una semana.

        Returns:
            {
                "formato": "EMOM 20 min",
                "bloque1": "45\" Trabajo / 15\" Rest",
                "bloque2": "45\" Pedaleo suave / 15\" Rest",
                "metrica": "Clavar las 44 RPM"
            }
        """
        clave = f"S{semana}"
        return self.pacing["semanas"].get(clave, {})

    def get_hip_thrust(self, semana: int) -> dict:
        """
        Devuelve los datos de hip thrust para una semana.

        Returns:
            {"series": 4, "reps": 10, "porcentaje_rm": 65, "descripcion": "..."}
        """
        clave = f"S{semana}"
        return self.hip_thrust["semanas"].get(clave, {})

    def get_pliometria(self, semana: int) -> dict:
        """
        Devuelve el protocolo de pliometría para una semana.

        Returns:
            {"series": 4, "reps": 3, "altura": "...", "foco": "..."}
        """
        clave = f"S{semana}"
        return self.pliometria["semanas"].get(clave, {})

    def get_accesorios(self, semana: int) -> dict:
        """
        Devuelve los datos de accesorios para una semana.

        Returns:
            {"fase": "...", "series": 3, "reps": 12, "rpe": 6, "descripcion": "..."}
        """
        clave = f"S{semana}"
        return self.accesorios["semanas"].get(clave, {})

    def get_accesorios_ejercicios(self) -> list:
        """Devuelve la lista fija de ejercicios accesorios (batería)."""
        return self.accesorios.get("ejercicios", [])

    def get_copenhague(self, semana: int) -> dict:
        """Devuelve datos del Copenhague Plank para una semana (Día 1)."""
        clave = f"S{semana}"
        cop = self.acompanantes.get("copenhague", {})
        data = cop.get("semanas", {}).get(clave, {})
        if data:
            return {
                "nombre": cop.get("nombre", "Copenhague Plank"),
                "unidad": cop.get("unidad", "por pierna"),
                **data,
            }
        return {}

    def get_bulgara(self, semana: int) -> dict:
        """Devuelve datos de la Sentadilla Búlgara para una semana (Día Fuerza)."""
        clave = f"S{semana}"
        bul = self.acompanantes.get("bulgara", {})
        data = bul.get("semanas", {}).get(clave, {})
        if data:
            return {
                "nombre": bul.get("nombre", "Sentadilla Búlgara"),
                "unidad": bul.get("unidad", "por pierna"),
                **data,
            }
        return {}

    def get_fase(self, semana: int) -> str:
        """Devuelve el nombre de la fase para una semana."""
        strength = self.get_strength(semana)
        return strength.get("fase", f"Semana {semana}")

    def validar_semana(self, semana: int) -> bool:
        """Verifica que existan datos para la semana indicada."""
        clave = f"S{semana}"
        tiene_gim = clave in self.gimnasticos.get("semanas", {})
        tiene_str = clave in self.strength.get("semanas", {})
        tiene_pac = clave in self.pacing.get("semanas", {})
        return tiene_gim and tiene_str and tiene_pac

    def resumen_ciclo(self) -> list[dict]:
        """Devuelve un resumen de todas las semanas del ciclo."""
        resumen = []
        for i in range(1, 9):
            strength = self.get_strength(i)
            resumen.append({
                "semana": i,
                "fase": strength.get("fase", "?"),
                "porcentaje_rm": strength.get("fuerza_base", {}).get("porcentaje_rm", 0),
                "formato_pacing": self.get_pacing(i).get("formato", "?"),
            })
        return resumen
