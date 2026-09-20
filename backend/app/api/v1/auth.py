"""M1 — สมัครสมาชิก / เข้าสู่ระบบ

เจ้าของงานส่วนนี้: <ใส่ชื่อสมาชิก>
"""

from fastapi import APIRouter, HTTPException, Request, status

from app.api import presenters
from app.api.deps import CurrentUser, DbSession
from app.core.security import create_access_token
from app.schemas.auth import (
    LoginRequest,
    PasswordChangeRequest,
    ProfileOut,
    ProfileUpdateRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.services import auth as auth_service

router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="เข้าสู่ระบบด้วยอีเมลหรือเบอร์โทร",
    responses={401: {"description": "อีเมล เบอร์โทรศัพท์ หรือรหัสผ่านไม่ถูกต้อง"}},
)
def login(payload: LoginRequest, db: DbSession, request: Request) -> TokenResponse:
    ip = request.client.host if request.client else None
    user, error = auth_service.authenticate(db, payload.identifier, payload.password, ip)

    # commit ทุกกรณี เพราะ AuditLog ของความพยายามที่ล้มเหลวก็ต้องถูกบันทึก
    db.commit()

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error)

    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role),
        user=UserOut.model_validate(user),
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="สมัครสมาชิกสำหรับผู้ประกอบการ",
    responses={409: {"description": "อีเมล เบอร์โทรศัพท์ หรือเลขประจำตัวประชาชนถูกใช้สมัครไว้แล้ว"}},
)
def register(payload: RegisterRequest, db: DbSession, request: Request) -> TokenResponse:
    ip = request.client.host if request.client else None
    user, error = auth_service.register(
        db,
        first_name=payload.first_name,
        last_name=payload.last_name,
        national_id=payload.national_id,
        phone=payload.phone,
        email=payload.email,
        password=payload.password,
        ip=ip,
    )

    if user is None:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)

    db.commit()
    # สมัครเสร็จเข้าใช้งานได้ทันที ไม่มีขั้นยืนยันตัวตนคั่น
    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role),
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=ProfileOut, summary="ข้อมูลบัญชีของผู้ใช้ที่เข้าสู่ระบบอยู่")
def me(db: DbSession, current: CurrentUser) -> ProfileOut:
    return presenters.to_profile_out(db, current)


@router.patch(
    "/me",
    response_model=ProfileOut,
    summary="แก้ข้อมูลบัญชีของตัวเอง (ชื่อ อีเมล เบอร์โทรศัพท์)",
    responses={409: {"description": "อีเมลหรือเบอร์โทรศัพท์ถูกใช้กับบัญชีอื่นแล้ว"}},
)
def update_me(
    payload: ProfileUpdateRequest, db: DbSession, current: CurrentUser, request: Request
) -> ProfileOut:
    """แก้ได้เฉพาะบัญชีของตัวเอง ไม่มีพารามิเตอร์ระบุว่าจะแก้ของใคร

    ผู้ใช้มาจากโทเคนเสมอ จึงไม่มีทางส่ง id ของคนอื่นเข้ามาแก้ได้
    เลขประจำตัวประชาชนและบทบาทแก้ไม่ได้ที่นี่ (เหตุผลอยู่ใน services/auth.py)
    """
    user, error = auth_service.update_profile(
        db,
        user=current,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        phone=payload.phone,
        ip=request.client.host if request.client else None,
    )

    if user is None:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)

    db.commit()
    db.refresh(user)
    return presenters.to_profile_out(db, user)


@router.post(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="เปลี่ยนรหัสผ่านของตัวเอง",
    responses={400: {"description": "รหัสผ่านเดิมไม่ถูกต้อง หรือรหัสใหม่ซ้ำกับรหัสเดิม"}},
)
def change_my_password(
    payload: PasswordChangeRequest, db: DbSession, current: CurrentUser, request: Request
) -> None:
    """โทเคนเดิมยังใช้ได้ต่อหลังเปลี่ยนรหัส

    ระบบจริงควรถอนโทเคนที่ออกไปก่อนหน้าทั้งหมด แต่ต้นแบบนี้ยังไม่มีที่เก็บ
    รายการโทเคน (ดูหมายเหตุความปลอดภัยใน frontend/src/lib/auth.ts)
    จึงบันทึกการเปลี่ยนรหัสลง AuditLog ไว้ให้ตามรอยได้แทน
    """
    error = auth_service.change_password(
        db,
        user=current,
        current_password=payload.current_password,
        new_password=payload.new_password,
        ip=request.client.host if request.client else None,
    )

    # ต้อง commit ทั้งสองทาง เพราะกรณีผิดก็มี AuditLog ที่ต้องเก็บไว้
    db.commit()
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
