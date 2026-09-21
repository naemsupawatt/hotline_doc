"""Exercise authorization, versioning and completion against the real API/local test DB."""

import jwt
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.application import Application
from app.models.document import DocumentFile
from app.services import storage
from tests import test_document_upload as upload_fixtures

client = upload_fixtures.client
token = upload_fixtures.token
application_no = upload_fixtures.application_no
PDF = upload_fixtures.PDF
auth = upload_fixtures.auth


@pytest.fixture
def cloud(monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "supabase")
    monkeypatch.setattr(settings, "SUPABASE_SECRET_KEY", "sb_secret_" + "test" * 10)
    files = {}
    monkeypatch.setattr(storage, "upload_url", lambda key: "https://example.supabase.co/" + key)

    def read(key, limit):
        if key not in files:
            raise storage.StorageMissing()
        data, mime = files[key]
        if len(data) > limit:
            raise storage.StorageTooLarge()
        return data, mime

    def write(key, data, mime):
        assert key not in files, "A stored version must never be overwritten"
        files[key] = (data, mime)
        return storage.CLOUD_PREFIX + key

    monkeypatch.setattr(storage, "cloud_read", read)
    monkeypatch.setattr(storage, "write", write)
    monkeypatch.setattr(
        storage, "delete", lambda ref: files.pop(ref.removeprefix(storage.CLOUD_PREFIX), None)
    )
    return files


def prepare(client, token, no, data=PDF, code="A02"):
    response = client.post(
        f"/api/v1/applications/{no}/documents/{code}/prepare",
        headers=auth(token),
        json={
            "original_name": "file.pdf",
            "size_bytes": len(data),
            "content_type": "application/pdf",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def stage(cloud, prepared, data=PDF, mime="application/pdf"):
    claims = jwt.decode(
        prepared["ticket"],
        settings.SUPABASE_SECRET_KEY,
        algorithms=["HS256"],
        audience="hotline-document-upload",
    )
    key = f"staging/{claims['application_no']}/{claims['nonce']}"
    cloud[key] = (data, mime)
    return key


def complete(client, token, no, prepared, code="A02"):
    return client.post(
        f"/api/v1/applications/{no}/documents/{code}/complete",
        headers=auth(token),
        json={"ticket": prepared["ticket"]},
    )


def test_direct_upload_above_vercel_limit_keeps_old_versions_and_is_idempotent(
    client,
    token,
    application_no,
    cloud,
):
    first = prepare(client, token, application_no)
    staging = stage(cloud, first)
    one = complete(client, token, application_no, first)
    assert one.status_code == 200, one.text
    assert staging not in cloud
    repeat = complete(client, token, application_no, first)
    assert repeat.json()["id"] == one.json()["id"]
    # A still-valid signed URL can recreate staging, never replace the permanent file.
    cloud[staging] = (b"malicious replacement", "application/pdf")
    assert complete(client, token, application_no, first).json()["id"] == one.json()["id"]
    large = PDF + b" " * (5 * 1024 * 1024)
    second = prepare(client, token, application_no, data=large)
    stage(cloud, second, data=large)
    two = complete(client, token, application_no, second)
    assert two.status_code == 200, two.text
    assert two.json()["version_no"] == 2
    with SessionLocal() as db:
        old = db.get(DocumentFile, one.json()["id"])
        new = db.get(DocumentFile, two.json()["id"])
        assert not old.is_current and new.is_current
        assert cloud[old.stored_path.removeprefix(storage.CLOUD_PREFIX)][0] == PDF
        assert cloud[new.stored_path.removeprefix(storage.CLOUD_PREFIX)][0] == large


@pytest.mark.parametrize("data,mime", [(b"wrong size", "application/pdf"), (PDF, "image/png")])
def test_finalize_checks_actual_storage_metadata(client, token, application_no, cloud, data, mime):
    prepared = prepare(client, token, application_no)
    stage(cloud, prepared, data=data, mime=mime)
    assert complete(client, token, application_no, prepared).status_code == 422
    with SessionLocal() as db:
        app_id = db.scalar(
            select(Application.id).where(Application.application_no == application_no)
        )
        assert (
            db.scalar(select(DocumentFile.id).where(DocumentFile.application_id == app_id)) is None
        )


def test_finalize_rechecks_application_state(client, token, application_no, cloud):
    prepared = prepare(client, token, application_no)
    stage(cloud, prepared)
    with SessionLocal() as db:
        application = db.scalar(
            select(Application).where(Application.application_no == application_no)
        )
        application.status = "submitted"
        db.commit()
    assert complete(client, token, application_no, prepared).status_code == 409


def test_ticket_is_not_an_access_token(client, token, application_no, cloud):
    prepared = prepare(client, token, application_no)
    response = client.get("/api/v1/auth/me", headers=auth(prepared["ticket"]))
    assert response.status_code == 401


def test_prepare_rejects_invalid_type_and_excess_size(client, token, application_no, cloud):
    for mime, size in [("application/pdf", 11 * 1024 * 1024), ("text/html", 100)]:
        response = client.post(
            f"/api/v1/applications/{application_no}/documents/A02/prepare",
            headers=auth(token),
            json={"original_name": "file", "content_type": mime, "size_bytes": size},
        )
        assert response.status_code == 422
    assert cloud == {}


def test_storage_failure_does_not_replace_current_version(
    client, token, application_no, cloud, monkeypatch
):
    first = prepare(client, token, application_no)
    stage(cloud, first)
    one = complete(client, token, application_no, first).json()
    second = prepare(client, token, application_no)
    stage(cloud, second)

    def fail(*args):
        raise storage.StorageError()

    monkeypatch.setattr(storage, "write", fail)
    response = complete(client, token, application_no, second)
    assert response.status_code == 503
    with SessionLocal() as db:
        assert db.get(DocumentFile, one["id"]).is_current
