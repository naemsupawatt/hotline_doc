"""Private file storage; only authorized API handlers may issue download links.

Cloud references carry a prefix so existing local files keep their location.
Browser uploads go to staging; only validated bytes are saved as permanent versions.
"""

from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlsplit

import httpx
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response

from app.core.config import settings

CLOUD_PREFIX = "supabase:"


class StorageError(Exception):
    status_code = 503
    detail = "ระบบจัดเก็บไฟล์ขัดข้องชั่วคราว กรุณาลองใหม่อีกครั้ง"


class StorageMissing(StorageError):
    status_code = 404
    detail = "ไม่พบไฟล์ในระบบจัดเก็บ กรุณาอัปโหลดใหม่"


class StorageTooLarge(StorageError):
    status_code = 422
    detail = "ไฟล์ใหญ่เกินขนาดที่ระบบรองรับ กรุณาย่อขนาดไฟล์แล้วลองใหม่"


def _key(key: str) -> str:
    if not key or key.startswith("/") or "\\" in key or ".." in key.split("/"):
        raise StorageError()
    return str(PurePosixPath(key))


def _base() -> str:
    if not settings.SUPABASE_URL or not settings.SUPABASE_SECRET_KEY:
        raise StorageError()
    return settings.SUPABASE_URL.rstrip("/") + "/storage/v1"


def _headers() -> dict[str, str]:
    # New sb_secret_ keys go in apikey; legacy service_role JWTs also use Bearer.
    key = settings.SUPABASE_SECRET_KEY
    headers = {"apikey": key}
    if not key.startswith("sb_secret_"):
        headers["Authorization"] = f"Bearer {key}"
    return headers


def _object(key: str) -> str:
    return quote(settings.SUPABASE_STORAGE_BUCKET, safe="") + "/" + quote(_key(key), safe="/")


def _check(response: httpx.Response) -> None:
    if response.is_success:
        return
    try:
        code = str(response.json().get("statusCode", response.status_code))
    except ValueError:
        code = str(response.status_code)
    if code == "404":
        raise StorageMissing()
    # Never expose provider responses, tokens or URLs to the user/logs.
    raise StorageError()


def request(method: str, path: str, **kwargs) -> httpx.Response:
    headers = {**_headers(), **kwargs.pop("headers", {})}
    try:
        with httpx.Client(timeout=30) as client:
            response = client.request(method, _base() + path, headers=headers, **kwargs)
        _check(response)
        return response
    except httpx.HTTPError:
        raise StorageError() from None


def _signed_url(value: str) -> str:
    url = _base() + "/" + value.lstrip("/")
    if value.startswith("https://"):
        url = value
    if urlsplit(url).netloc != urlsplit(settings.SUPABASE_URL).netloc:
        raise StorageError()
    return url


def upload_url(key: str) -> str:
    response = request("POST", "/object/upload/sign/" + _object(key), json={})
    return _signed_url(response.json()["url"])


def cloud_read(key: str, limit: int) -> tuple[bytes, str]:
    try:
        with httpx.Client(timeout=30) as client:
            with client.stream(
                "GET", _base() + "/object/" + _object(key), headers=_headers()
            ) as response:
                if not response.is_success:
                    response.read()
                    _check(response)
                data = bytearray()
                for chunk in response.iter_bytes():
                    if len(data) + len(chunk) > limit:
                        raise StorageTooLarge()
                    data.extend(chunk)
                mime = response.headers.get("content-type", "").split(";", 1)[0].strip()
                return bytes(data), mime
    except httpx.HTTPError:
        raise StorageError() from None


def write(key: str, data: bytes, mime: str) -> str:
    key = _key(key)
    if settings.STORAGE_BACKEND == "supabase":
        request(
            "POST",
            "/object/" + _object(key),
            content=data,
            headers={
                "Content-Type": mime,
                "x-upsert": "false",
                "Cache-Control": "no-store",
            },
        )
        return CLOUD_PREFIX + key
    path = Path(settings.STORAGE_DIR) / key
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as file:
        file.write(data)
    return key


def delete(reference: str) -> None:
    if reference.startswith(CLOUD_PREFIX):
        key = _key(reference.removeprefix(CLOUD_PREFIX))
        request(
            "DELETE",
            "/object/" + quote(settings.SUPABASE_STORAGE_BUCKET, safe=""),
            json={"prefixes": [key]},
        )
    else:
        (Path(settings.STORAGE_DIR) / _key(reference)).unlink(missing_ok=True)


def file_response(reference: str, mime: str, filename: str, *, download_url: bool) -> Response:
    if reference.startswith(CLOUD_PREFIX):
        key = reference.removeprefix(CLOUD_PREFIX)
        response = request("POST", "/object/sign/" + _object(key), json={"expiresIn": 60})
        url = _signed_url(response.json()["signedURL"])
        headers = {"Cache-Control": "private, no-store", "Referrer-Policy": "no-referrer"}
        if download_url:
            return JSONResponse({"download_url": url}, headers=headers)
        return RedirectResponse(url, status_code=302, headers=headers)
    path = Path(settings.STORAGE_DIR) / _key(reference)
    if not path.is_file():
        raise StorageMissing()
    return FileResponse(
        path, media_type=mime, filename=filename, headers={"Cache-Control": "private, no-store"}
    )
