# -*- coding: utf-8 -*-

import os
from io import BytesIO

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]


def get_drive_service():
    credentials_path = os.environ.get("GOOGLE_DRIVE_CREDENTIALS")
    if not credentials_path:
        raise RuntimeError(
            "La variable de entorno GOOGLE_DRIVE_CREDENTIALS no está configurada"
        )

    creds = service_account.Credentials.from_service_account_file(
        credentials_path,
        scopes=SCOPES
    )

    return build("drive", "v3", credentials=creds, cache_discovery=False)


def subir_pdf_a_drive(nombre_archivo, pdf_bytes, folder_id):
    if not folder_id:
        raise RuntimeError(
            "No se ha definido el ID de la carpeta de Drive (DRIVE_FOLDER_ID)"
        )

    service = get_drive_service()

    file_metadata = {
        "name": nombre_archivo,
        "parents": [folder_id]
    }

    media = MediaIoBaseUpload(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        resumable=False
    )

    archivo = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, webViewLink"
    ).execute()

    return archivo["id"], archivo["webViewLink"]
