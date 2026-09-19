"""M1 — สมัครสมาชิก / เข้าสู่ระบบ / ยืนยันตัวตนด้วย OTP

เจ้าของงานส่วนนี้: <ใส่ชื่อสมาชิก>
"""

from fastapi import APIRouter, HTTPException, Request, status

from app.api.deps import CurrentUser, DbSession
from app.core.security import create_access_token
from app.schemas.auth import LoginRequest, TokenResponse, UserOut
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


@router.get("/me", response_model=UserOut, summary="ข้อมูลผู้ใช้ที่เข้าสู่ระบบอยู่")
def me(current: CurrentUser) -> UserOut:
    return UserOut.model_validate(current)


# TODO M1: POST /register        สมัครด้วยเบอร์โทรหรืออีเมล
# TODO M1: POST /verify-otp      ยืนยันตัวตน (โหมดสาธิตใช้ OTP คงที่ 6 หลัก)
