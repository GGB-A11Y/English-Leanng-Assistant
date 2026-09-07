from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    """前端每 15s 轮询,用于「后端在线/离线」状态显示(契约 3.1)。"""
    return {"status": "ok", "version": "0.1.0"}
