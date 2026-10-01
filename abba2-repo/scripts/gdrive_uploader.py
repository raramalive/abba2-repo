"""
ABBA 2 — Google Drive Uploader
Uploads final video + assets to Google Drive folder named "JESUS".
Uses service account credentials from secrets/google_service_account.json.
"""

import json
import os
import sys
from pathlib import Path

SECRETS_DIR = Path(__file__).parent.parent / "secrets"
SA_KEY_FILE = SECRETS_DIR / "google_service_account.json"
TARGET_FOLDER_NAME = "JESUS"

# Google Drive API v3 endpoints
DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
DRIVE_UPLOAD_BASE = "https://www.googleapis.com/upload/drive/v3"


def _get_access_token() -> str:
    """Get OAuth2 access token using service account JWT."""
    import time
    import json
    import base64
    import hashlib
    import hmac
    import struct
    import math
    import requests

    with open(SA_KEY_FILE) as f:
        sa = json.load(f)

    # Build JWT
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claim = {
        "iss": sa["client_email"],
        "scope": "https://www.googleapis.com/auth/drive",
        "aud": sa["token_uri"],
        "iat": now,
        "exp": now + 3600,
    }

    def _b64(data):
        if isinstance(data, dict):
            data = json.dumps(data, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    unsigned = f"{_b64(header)}.{_b64(claim)}"

    # Sign with RSA private key
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.backends import default_backend

    private_key = serialization.load_pem_private_key(
        sa["private_key"].encode(),
        password=None,
        backend=default_backend(),
    )
    signature = private_key.sign(
        unsigned.encode(),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    jwt_token = f"{unsigned}.{_b64(signature)}"

    # Exchange JWT for access token
    resp = requests.post(
        sa["token_uri"],
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": jwt_token,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _get_or_create_folder(token: str, folder_name: str, parent_id: str = None) -> str:
    """Find or create a Google Drive folder. Returns folder ID."""
    import requests

    headers = {"Authorization": f"Bearer {token}"}
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    resp = requests.get(
        f"{DRIVE_API_BASE}/files",
        headers=headers,
        params={"q": query, "fields": "files(id, name)"},
        timeout=30,
    )
    resp.raise_for_status()
    files = resp.json().get("files", [])

    if files:
        folder_id = files[0]["id"]
        print(f"[GDrive] Found existing folder '{folder_name}': {folder_id}")
        return folder_id

    # Create the folder
    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        metadata["parents"] = [parent_id]

    resp = requests.post(
        f"{DRIVE_API_BASE}/files",
        headers={**headers, "Content-Type": "application/json"},
        json=metadata,
        timeout=30,
    )
    resp.raise_for_status()
    folder_id = resp.json()["id"]
    print(f"[GDrive] Created folder '{folder_name}': {folder_id}")
    return folder_id


def _upload_file(token: str, file_path: str, folder_id: str, mime_type: str = None) -> dict:
    """Upload a file to Google Drive in the specified folder."""
    import requests
    import mimetypes

    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if mime_type is None:
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type is None:
            mime_type = "application/octet-stream"

    headers = {"Authorization": f"Bearer {token}"}
    metadata = {
        "name": file_path.name,
        "parents": [folder_id],
    }

    # Multipart upload
    from requests_toolbelt import MultipartEncoder
    # Fallback if requests_toolbelt not available
    try:
        from requests_toolbelt import MultipartEncoder
        m = MultipartEncoder(
            fields={
                "metadata": ("metadata", json.dumps(metadata), "application/json; charset=UTF-8"),
                "file": (file_path.name, open(file_path, "rb"), mime_type),
            }
        )
        resp = requests.post(
            f"{DRIVE_UPLOAD_BASE}/files?uploadType=multipart",
            headers={**headers, "Content-Type": m.content_type},
            data=m,
            timeout=600,
        )
    except ImportError:
        # Simple multipart without library
        import io
        boundary = "==BOUNDARY=="
        body = (
            f"--{boundary}\r\n"
            f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
            f"{json.dumps(metadata)}\r\n"
            f"--{boundary}\r\n"
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode()
        body += file_path.read_bytes()
        body += f"\r\n--{boundary}--".encode()

        resp = requests.post(
            f"{DRIVE_UPLOAD_BASE}/files?uploadType=multipart",
            headers={**headers, "Content-Type": f"multipart/related; boundary={boundary}"},
            data=body,
            timeout=600,
        )

    resp.raise_for_status()
    result = resp.json()
    print(f"[GDrive] Uploaded '{file_path.name}': {result.get('id')}")
    return result


def upload_to_jesus_folder(files_to_upload: list) -> list:
    """
    Upload a list of file paths to the JESUS folder in Google Drive.
    files_to_upload: list of file path strings.
    Returns list of upload results.
    """
    print(f"[GDrive] Authenticating with service account...")
    token = _get_access_token()

    print(f"[GDrive] Locating/creating '{TARGET_FOLDER_NAME}' folder...")
    folder_id = _get_or_create_folder(token, TARGET_FOLDER_NAME)

    results = []
    for file_path in files_to_upload:
        print(f"[GDrive] Uploading: {file_path}")
        result = _upload_file(token, file_path, folder_id)
        results.append(result)

    print(f"[GDrive] Successfully uploaded {len(results)} file(s) to '{TARGET_FOLDER_NAME}'")
    return results


if __name__ == "__main__":
    # CLI usage: python gdrive_uploader.py file1.mp4 file2.py file3.json
    files = sys.argv[1:]
    if not files:
        print("Usage: python gdrive_uploader.py <file1> [file2] ...")
        sys.exit(1)
    results = upload_to_jesus_folder(files)
    print(json.dumps(results, indent=2))
