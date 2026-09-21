"""Delete abandoned staging files only after their two-hour upload URLs have expired.

uv run --env-file .env.supabase.local python -m scripts.cleanup_staging
Add --yes to delete. Read Storage metadata via SQL; delete objects only via Storage API.
"""

import sys

from sqlalchemy import text

from app.core.config import settings
from app.core.db import SessionLocal
from app.services import storage


def main() -> None:
    with SessionLocal() as db:
        keys = list(
            db.scalars(
                text("""
            SELECT name FROM storage.objects
            WHERE bucket_id = :bucket AND name LIKE 'staging/%'
              AND created_at < now() - interval '3 hours'
        """),
                {"bucket": settings.SUPABASE_STORAGE_BUCKET},
            )
        )
    print(f"Expired staging objects: {len(keys)}")
    if "--yes" not in sys.argv:
        print("Preview only. Add --yes to delete these staging objects.")
        return
    for key in keys:
        storage.delete(storage.CLOUD_PREFIX + key)
    print(f"Deleted: {len(keys)}")


if __name__ == "__main__":
    main()
