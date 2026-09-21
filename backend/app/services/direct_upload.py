"""Bind staging uploads to an owner, application, document and immutable file version."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from fastapi import HTTPException

from app.core.config import settings
from app.schemas.upload import PrepareUpload
from app.services import storage

AUDIENCE = "hotline-document-upload"


def prepare(application_no: str, code: str, user_id: int, payload: PrepareUpload) -> dict:
    nonce = uuid4().hex
    staging = f"staging/{application_no}/{nonce}"
    url = storage.upload_url(staging)
    now = datetime.now(UTC)
    ticket = jwt.encode(
        {
            **payload.model_dump(),
            "application_no": application_no,
            "code": code,
            "user_id": user_id,
            "nonce": nonce,
            "aud": AUDIENCE,
            "iat": now,
            "exp": now + timedelta(minutes=30),
        },
        settings.SUPABASE_SECRET_KEY,
        algorithm="HS256",
    )
    return {"mode": "supabase", "upload_url": url, "ticket": ticket}


def decode(ticket: str, application_no: str, code: str, user_id: int) -> dict:
    try:
        claims = jwt.decode(
            ticket,
            settings.SUPABASE_SECRET_KEY,
            algorithms=["HS256"],
            audience=AUDIENCE,
            leeway=30,
            options={
                "require": [
                    "exp",
                    "iat",
                    "aud",
                    "nonce",
                    "user_id",
                    "application_no",
                    "code",
                    "size_bytes",
                    "content_type",
                    "original_name",
                ]
            },
        )
        if (claims["application_no"], claims["code"], claims["user_id"]) != (
            application_no,
            code,
            user_id,
        ):
            raise ValueError()
        return claims
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(422, "ข้อมูลอัปโหลดหมดอายุหรือไม่ถูกต้อง กรุณาเลือกไฟล์แล้วอัปโหลดใหม่") from None
