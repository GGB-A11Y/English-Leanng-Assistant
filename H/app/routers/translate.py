"""英语翻译:翻译 + 深度解析(契约 3.4)。同步接口,历史由前端本地保存。"""
from fastapi import APIRouter, Depends, HTTPException

from ..auth import get_current_user
from ..llm import generate_structured
from ..models import User
from ..prompts import TRANSLATE_SYSTEM
from ..schemas import TranslateIn, TranslationLlm

router = APIRouter(tags=["translate"])


@router.post("/translate", response_model=TranslationLlm)
def translate(payload: TranslateIn, user: User = Depends(get_current_user)):
    if payload.source_lang == payload.target_lang:
        raise HTTPException(422, "源语言与目标语言不能相同")
    if not payload.text.strip():
        raise HTTPException(422, "待翻译文本不能为空")
    if len(payload.text) > 2000:
        raise HTTPException(422, "待翻译文本过长(最多 2000 字符)")

    direction = "中文 → 英文" if payload.source_lang == "zh" else "英文 → 中文"
    user = f"翻译方向:{direction}\n待翻译文本:\n{payload.text}"
    return generate_structured(TranslationLlm, TRANSLATE_SYSTEM, user)
