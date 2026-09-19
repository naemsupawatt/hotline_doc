"""FastAPI dependencies ที่ใช้ร่วมกัน — auth, role guard, scope ของท้องถิ่น"""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_access_token
from app.models.enums import UserRole
from app.models.user import User

bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)] = None,
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="กรุณาเข้าสู่ระบบก่อนใช้งานส่วนนี้",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if creds is None:
        raise unauthorized

    try:
        payload = decode_access_token(creds.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="เซสชันหมดอายุแล้ว กรุณาเข้าสู่ระบบใหม่อีกครั้ง",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.PyJWTError:
        raise unauthorized from None

    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*allowed: UserRole):
    """guard ตามบทบาท (NFR: Role-based Authorization)

    คืน dependency ที่ปล่อยผ่านเฉพาะบทบาทที่ระบุ
    ใช้แบบ: `user: Annotated[User, Depends(require_role(UserRole.OPERATOR))]`

    ข้อความ 403 ต้องบอกผู้ใช้ว่า "ทำไม่ได้เพราะบทบาทไม่ตรง" ด้วยภาษาคน
    ไม่ใช่ปล่อยข้อความดิบของเฟรมเวิร์กออกไป (NFR Usability)
    """

    def guard(current: CurrentUser) -> User:
        if current.role not in {r.value for r in allowed}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="บัญชีของคุณไม่มีสิทธิ์ใช้งานส่วนนี้",
            )
        return current

    return guard


CurrentOperator = Annotated[User, Depends(require_role(UserRole.OPERATOR))]

# TODO: require_same_authority(application)  -> guard T-09 + เขียน AuditLog เมื่อถูกปฏิเสธ
