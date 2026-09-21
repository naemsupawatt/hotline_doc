from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.services.storage import StorageError

app = FastAPI(
    title="HoTLinE Doc API",
    description=(
        "ระบบยื่นขอใบอนุญาตประกอบธุรกิจโรงแรมและที่พักแรมแบบออนไลน์ "
        "— ข้อมูลทั้งหมดเป็นข้อมูลจำลองสำหรับการสาธิตเท่านั้น"
    ),
    version="0.1.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# ต้องตั้งก่อนเสมอ ไม่งั้น frontend ที่ localhost:3000 จะยิง API ไม่ได้
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(StorageError)
async def storage_error_handler(request, exc: StorageError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "hotline-doc-api"}
