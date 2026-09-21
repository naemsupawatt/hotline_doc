"""Create/check the private bucket.

uv run --env-file .env.supabase.local python -m scripts.setup_storage
"""

from urllib.parse import quote

from app.core.config import settings
from app.services import storage


def main() -> None:
    bucket = settings.SUPABASE_STORAGE_BUCKET
    try:
        info = storage.request("GET", "/bucket/" + quote(bucket, safe="")).json()
    except storage.StorageMissing:
        storage.request(
            "POST",
            "/bucket",
            json={
                "id": bucket,
                "name": bucket,
                "public": False,
                "file_size_limit": settings.MAX_UPLOAD_MB * 1024 * 1024,
            },
        )
    else:
        if info.get("public"):
            raise SystemExit("Bucket นี้เป็น public กรุณาเปลี่ยนเป็น private ก่อนใช้งาน")
        storage.request(
            "PUT",
            "/bucket/" + quote(bucket, safe=""),
            json={
                "public": False,
                "file_size_limit": settings.MAX_UPLOAD_MB * 1024 * 1024,
            },
        )
    print(f"Private bucket ready: {bucket} ({settings.MAX_UPLOAD_MB} MB/file)")


if __name__ == "__main__":
    try:
        main()
    except storage.StorageError as exc:
        raise SystemExit(exc.detail) from None
