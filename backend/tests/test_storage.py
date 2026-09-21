"""Storage REST contracts and private download behavior, without a live cloud account."""

import json

import httpx
import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.schemas.upload import PrepareUpload
from app.services import direct_upload, storage


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "supabase")
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(settings, "SUPABASE_SECRET_KEY", "sb_secret_" + "test" * 10)
    calls = []
    responses = []

    def handler(request):
        calls.append(request)
        return responses.pop(0)

    original = httpx.Client
    monkeypatch.setattr(
        storage.httpx, "Client", lambda **kw: original(transport=httpx.MockTransport(handler), **kw)
    )
    return calls, responses


def test_cloud_write_is_private_and_never_upserts(provider):
    calls, responses = provider
    responses.append(httpx.Response(200, json={"Key": "hotline-documents/app/one.pdf"}))
    ref = storage.write("app/one.pdf", b"pdf-bytes", "application/pdf")
    assert ref == "supabase:app/one.pdf"
    assert calls[0].headers["x-upsert"] == "false"
    assert calls[0].headers["apikey"] == settings.SUPABASE_SECRET_KEY
    assert "authorization" not in calls[0].headers
    assert calls[0].content == b"pdf-bytes"


def test_download_link_is_short_lived_and_not_cached(provider):
    calls, responses = provider
    responses.append(httpx.Response(200, json={"signedURL": "/object/sign/bucket/key?token=short"}))
    response = storage.file_response(
        "supabase:app/file.pdf", "application/pdf", "x.pdf", download_url=True
    )
    assert json.loads(calls[0].content) == {"expiresIn": 60}
    assert json.loads(response.body)["download_url"].startswith(
        "https://example.supabase.co/storage/v1/object/sign/"
    )
    assert "no-store" in response.headers["cache-control"]
    assert settings.SUPABASE_SECRET_KEY not in response.body.decode()


def test_provider_failure_does_not_leak_secrets(provider):
    _, responses = provider
    responses.append(httpx.Response(403, json={"message": settings.SUPABASE_SECRET_KEY}))
    with pytest.raises(storage.StorageError) as error:
        storage.write("app/file.pdf", b"file", "application/pdf")
    assert settings.SUPABASE_SECRET_KEY not in str(error.value)


def test_cloud_read_limits_actual_bytes(provider):
    _, responses = provider
    responses.append(httpx.Response(200, content=b"12345", headers={"content-type": "image/png"}))
    with pytest.raises(storage.StorageTooLarge):
        storage.cloud_read("staging/file", 4)


def test_local_files_stay_local_after_switching_provider(provider, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path))
    (tmp_path / "old.pdf").write_bytes(b"old version")
    response = storage.file_response("old.pdf", "application/pdf", "old.pdf", download_url=True)
    assert response.path == tmp_path / "old.pdf"
    assert provider[0] == []


@pytest.mark.parametrize("key", ["../secret", "/etc/passwd", "a/../../secret", "a\\secret"])
def test_path_traversal_is_rejected(key):
    with pytest.raises(storage.StorageError):
        storage.write(key, b"x", "image/png")


def test_upload_ticket_cannot_be_reused_for_another_owner_or_document(provider):
    _, responses = provider
    responses.append(httpx.Response(200, json={"url": "/object/upload/sign/bucket/key?token=t"}))
    result = direct_upload.prepare(
        "APP-1",
        "A02",
        5,
        PrepareUpload(original_name="x.pdf", content_type="application/pdf", size_bytes=10),
    )
    assert direct_upload.decode(result["ticket"], "APP-1", "A02", 5)["slot_no"] is None
    for app, code, owner in [("APP-2", "A02", 5), ("APP-1", "A03", 5), ("APP-1", "A02", 6)]:
        with pytest.raises(HTTPException) as error:
            direct_upload.decode(result["ticket"], app, code, owner)
        assert error.value.status_code == 422
    with pytest.raises(HTTPException):
        direct_upload.decode(result["ticket"] + "tampered", "APP-1", "A02", 5)
