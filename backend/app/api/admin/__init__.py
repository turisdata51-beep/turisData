"""API del panel de administración: agrupa las rutas de cada sección bajo /api/admin."""
from fastapi import APIRouter

from . import cargas, catalogos, establecimientos, resumen, usuarios

router = APIRouter(prefix="/api/admin", tags=["admin"])
for modulo in (resumen, cargas, establecimientos, usuarios, catalogos):
    router.include_router(modulo.router)
