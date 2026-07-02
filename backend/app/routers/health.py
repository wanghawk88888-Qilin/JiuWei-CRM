from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
async def health_check():
    return {
        "success": True,
        "data": {
            "service": "jiuwei-crm-backend",
            "status": "ok",
        },
        "message": "ok",
    }
