"""Supabase Storage：服务端 service_role 上传/下载。"""
import requests
from flask import current_app


def storage_configured() -> bool:
    c = current_app.config
    return bool(c.get("SUPABASE_URL") and c.get("SUPABASE_SERVICE_ROLE_KEY"))


def _headers():
    key = current_app.config["SUPABASE_SERVICE_ROLE_KEY"]
    return {"Authorization": f"Bearer {key}", "apikey": key}


def upload_object(bucket: str, object_path: str, data: bytes, content_type: str = "application/octet-stream") -> bool:
    base = current_app.config["SUPABASE_URL"]
    url = f"{base}/storage/v1/object/{bucket}/{object_path}"
    r = requests.post(
        url,
        headers={**_headers(), "Content-Type": content_type},
        data=data,
        timeout=600,
    )
    if r.status_code in (200, 201):
        return True
    current_app.logger.error("Storage upload failed %s: %s", r.status_code, r.text[:500])
    return False


def download_object(bucket: str, object_path: str, dest_path: str) -> bool:
    base = current_app.config["SUPABASE_URL"]
    url = f"{base}/storage/v1/object/{bucket}/{object_path}"
    r = requests.get(url, headers=_headers(), timeout=600)
    if r.status_code != 200:
        current_app.logger.error("Storage download failed %s: %s", r.status_code, r.text[:300])
        return False
    with open(dest_path, "wb") as f:
        f.write(r.content)
    return True
