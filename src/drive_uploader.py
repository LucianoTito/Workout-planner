"""
Subida automática a Google Drive.
Toma un .xlsx local y lo sube a Drive convirtiéndolo en Google Sheets.
"""
from pathlib import Path
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
MIME_GOOGLE_SHEETS = "application/vnd.google-apps.spreadsheet"
MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class DriveUploader:
    def __init__(self, credentials_path="credentials.json", token_path="token.json"):
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)
        self._service = None
        self._creds = None
        self._sheets_service = None

    def _autenticar(self):
        creds = None
        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
        if not creds or not creds.valid:
            renovado = False
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    renovado = True
                except RefreshError:
                    # Token vencido o revocado por Google. En vez de morir con
                    # un invalid_grant, pedimos permiso de nuevo abriendo el
                    # navegador (antes había que borrar token.json a mano).
                    creds = None
            if not renovado:
                if not self.credentials_path.exists():
                    raise FileNotFoundError(
                        f"No encontré '{self.credentials_path}'. "
                        "Descargá el JSON de Google Cloud y ponelo en la raíz."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open(self.token_path, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
        self._creds = creds
        self._service = build("drive", "v3", credentials=creds)
        return self._service

    def obtener_o_crear_carpeta(self, nombre_carpeta, parent_id=None):
        service = self._autenticar()
        query = (
            f"name = '{nombre_carpeta}' "
            "and mimeType = 'application/vnd.google-apps.folder' "
            "and trashed = false"
        )
        if parent_id:
            query += f" and '{parent_id}' in parents"
        resultado = service.files().list(
            q=query, spaces="drive", fields="files(id, name)"
        ).execute()
        carpetas = resultado.get("files", [])
        if carpetas:
            return carpetas[0]["id"]
        metadata = {
            "name": nombre_carpeta,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            metadata["parents"] = [parent_id]
        carpeta = service.files().create(body=metadata, fields="id").execute()
        return carpeta["id"]

    def subir_como_sheets(self, ruta_xlsx, nombre_en_drive=None, carpeta_id=None):
        ruta = Path(ruta_xlsx)
        if not ruta.exists():
            raise FileNotFoundError(f"No encontré el archivo: {ruta}")
        service = self._autenticar()
        if not nombre_en_drive:
            nombre_en_drive = ruta.stem
        file_metadata = {"name": nombre_en_drive, "mimeType": MIME_GOOGLE_SHEETS}
        if carpeta_id:
            file_metadata["parents"] = [carpeta_id]
        media = MediaFileUpload(str(ruta), mimetype=MIME_XLSX, resumable=True)
        archivo = service.files().create(
            body=file_metadata, media_body=media, fields="id, webViewLink"
        ).execute()
        return {"id": archivo.get("id"), "link": archivo.get("webViewLink")}

    def _sheets(self):
        """Devuelve (creando si hace falta) el cliente de la Sheets API."""
        if self._sheets_service is None:
            if self._creds is None:
                self._autenticar()
            self._sheets_service = build("sheets", "v4", credentials=self._creds)
        return self._sheets_service

    def _buscar_sheets_por_nombre(self, nombre, carpeta_id=None):
        """Busca un Google Sheets por nombre. Devuelve su id o None."""
        service = self._autenticar()
        query = (
            f"name = '{nombre}' "
            f"and mimeType = '{MIME_GOOGLE_SHEETS}' "
            "and trashed = false"
        )
        if carpeta_id:
            query += f" and '{carpeta_id}' in parents"
        resultado = service.files().list(
            q=query, spaces="drive", fields="files(id, name)"
        ).execute()
        archivos = resultado.get("files", [])
        return archivos[0]["id"] if archivos else None

    def agregar_semana_como_pestana(self, ruta_xlsx, nombre_pestana,
                                    nombre_maestro, carpeta_id=None):
        """
        Agrega la semana (un .xlsx) como una pestaña dentro del Sheets maestro
        del atleta. La primera vez, el propio archivo pasa a ser el maestro.
        Si ya existe una pestaña con 'nombre_pestana', la reemplaza.
        Devuelve {'id': maestro_id, 'link': webViewLink}.
        """
        maestro_id = self._buscar_sheets_por_nombre(nombre_maestro, carpeta_id)

        # ─── Primera semana del atleta: el archivo ES el maestro ───
        if maestro_id is None:
            res = self.subir_como_sheets(
                ruta_xlsx, nombre_en_drive=nombre_maestro, carpeta_id=carpeta_id
            )
            self._renombrar_unica_pestana(res["id"], nombre_pestana)
            return {"id": res["id"], "link": res["link"]}

        # ─── Semanas siguientes: subir temporal, copiar pestaña, borrar temp ───
        temp = self.subir_como_sheets(
            ruta_xlsx, nombre_en_drive=f"__temp__{nombre_pestana}", carpeta_id=None
        )
        temp_id = temp["id"]
        try:
            nuevo_sheet_id = self._copiar_pestana(temp_id, maestro_id)
            self._reemplazar_y_renombrar(maestro_id, nuevo_sheet_id, nombre_pestana)
        finally:
            self._borrar_archivo(temp_id)

        return {"id": maestro_id, "link": self._link_de(maestro_id)}

    def _renombrar_unica_pestana(self, spreadsheet_id, titulo):
        """Renombra la primera (y única) pestaña de un spreadsheet."""
        sheets = self._sheets()
        info = sheets.spreadsheets().get(
            spreadsheetId=spreadsheet_id, fields="sheets.properties(sheetId,title)"
        ).execute()
        sheet_id = info["sheets"][0]["properties"]["sheetId"]
        sheets.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{
                "updateSheetProperties": {
                    "properties": {"sheetId": sheet_id, "title": titulo},
                    "fields": "title",
                }
            }]},
        ).execute()

    def _copiar_pestana(self, origen_id, destino_id):
        """Copia la primera pestaña de 'origen' dentro de 'destino'. Devuelve el sheetId nuevo."""
        sheets = self._sheets()
        info = sheets.spreadsheets().get(
            spreadsheetId=origen_id, fields="sheets.properties(sheetId)"
        ).execute()
        sheet_origen = info["sheets"][0]["properties"]["sheetId"]
        resp = sheets.spreadsheets().sheets().copyTo(
            spreadsheetId=origen_id,
            sheetId=sheet_origen,
            body={"destinationSpreadsheetId": destino_id},
        ).execute()
        return resp["sheetId"]

    def _reemplazar_y_renombrar(self, maestro_id, nuevo_sheet_id, titulo):
        """
        Renombra la pestaña recién copiada a 'titulo'. Si ya existía otra
        pestaña con ese nombre, la borra primero (en el mismo batch).
        """
        sheets = self._sheets()
        info = sheets.spreadsheets().get(
            spreadsheetId=maestro_id, fields="sheets.properties(sheetId,title)"
        ).execute()

        requests = []
        for s in info["sheets"]:
            props = s["properties"]
            if props["title"] == titulo and props["sheetId"] != nuevo_sheet_id:
                requests.append({"deleteSheet": {"sheetId": props["sheetId"]}})
        requests.append({
            "updateSheetProperties": {
                "properties": {"sheetId": nuevo_sheet_id, "title": titulo},
                "fields": "title",
            }
        })
        sheets.spreadsheets().batchUpdate(
            spreadsheetId=maestro_id, body={"requests": requests}
        ).execute()

    def _borrar_archivo(self, file_id):
        """Borra (definitivamente) un archivo de Drive creado por la app."""
        service = self._autenticar()
        service.files().delete(fileId=file_id).execute()

    def _link_de(self, file_id):
        """Devuelve el webViewLink de un archivo."""
        service = self._autenticar()
        info = service.files().get(fileId=file_id, fields="webViewLink").execute()
        return info.get("webViewLink")

    def pestana_existe(self, nombre_maestro, nombre_pestana, carpeta_id=None):
        """Devuelve True si el maestro del atleta ya tiene una pestaña con ese nombre."""
        maestro_id = self._buscar_sheets_por_nombre(nombre_maestro, carpeta_id)
        if maestro_id is None:
            return False
        info = self._sheets().spreadsheets().get(
            spreadsheetId=maestro_id, fields="sheets.properties(title)"
        ).execute()
        return any(
            s["properties"]["title"] == nombre_pestana for s in info["sheets"]
        )