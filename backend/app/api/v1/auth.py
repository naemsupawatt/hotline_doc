"""M1 — สมัครสมาชิก / เข้าสู่ระบบ / ยืนยันตัวตนด้วย OTP

เจ้าของงานส่วนนี้: <ใส่ชื่อสมาชิก>
"""

from fastapi import APIRouter, HTTPException, Request, status

from app.api.deps import CurrentUser, DbSession
from app.core.security import create_access_token
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserOut,
    VerifyOtpRequest,
)
from app.services import auth as auth_service

router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="เข้าสู่ระบบด้วยอีเมลหรือเบอร์โทร",
    responses={401: {"description": "ข้อมูลเข้าสู่ระบบไม่ถูกต้อง หรือยังไม่ยืนยันตัวตน"}},
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
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="สมัครสมาชิกสำหรับผู้ประกอบการ",
    responses={409: {"description": "อีเมลหรือเลขประจำตัวประชาชนถูกใช้สมัครไว้แล้ว"}},
)
def register(payload: RegisterRequest, db: DbSession, request: Request) -> RegisterResponse:
    ip = request.client.host if request.client else None
    user, error = auth_service.register(
        db,
        first_name=payload.first_name,
        last_name=payload.last_name,
        national_id=payload.national_id,
        birth_date=payload.birth_date,
        email=payload.email,
        password=payload.password,
        ip=ip,
    )

    if user is None:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)

    db.commit()
    return RegisterResponse(
        email=payload.email,
        message="สมัครสมาชิกสำเร็จ กรุณายืนยันตัวตนด้วยรหัส 6 หลักเพื่อเริ่มใช้งาน",
        # โหมดสาธิตเท่านั้น — ระบบจริงต้องส่งรหัสทางอีเมล/SMS ไม่ใช่คืนกลับมาทาง API
        demo_code=auth_service.DEMO_OTP,
    )


@router.post(
    "/verify-otp",
    response_model=TokenResponse,
    summary="ยืนยันตัวตนด้วยรหัส 6 หลัก แล้วเข้าสู่ระบบให้เลย",
    responses={400: {"description": "รหัสยืนยันไม่ถูกต้อง"}},
)
def verify_otp(payload: VerifyOtpRequest, db: DbSession, request: Request) -> TokenResponse:
    ip = request.client.host if request.client else None
    user, error = auth_service.verify_otp(db, payload.email, payload.code, ip)
    db.commit()

    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role),
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut, summary="ข้อมูลผู้ใช้ที่เข้าสู่ระบบอยู่")
def me(current: CurrentUser) -> UserOut:
    return UserOut.model_validate(current)
