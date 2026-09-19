from fastapi import APIRouter

from app.api.v1 import admin, applications, auth, documents, officer, reports, wizard

api_router = APIRouter()
api_router.include_router(auth.router,         prefix="/auth",         tags=["auth"])
api_router.include_router(wizard.router,       prefix="/wizard",       tags=["wizard"])
api_router.include_router(applications.router, prefix="/applications", tags=["applications"])
api_router.include_router(documents.router,    prefix="/documents",    tags=["documents"])
api_router.include_router(officer.router,      prefix="/officer",      tags=["officer"])
api_router.include_router(reports.router,      prefix="/reports",      tags=["reports"])
api_router.include_router(admin.router,        prefix="/admin",        tags=["admin"])
