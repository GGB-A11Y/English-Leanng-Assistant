"""注册图形验证码:纯 Python 生成 SVG(data URI),零外部依赖。

- 4 位字符,去除易混淆的 0/O/1/I;大小写不敏感(两端统一 upper)
- 答案只存 SHA-256 哈希(复用 app.auth.hash_token),泄露库文件拿不到答案
- 一次性:任何一次校验(无论对错)即删除该行;有效期 settings.captcha_expire_minutes
- 校验用单条原子 DELETE 实现:SQLite 只序列化写,「SELECT→比对→DELETE」的读-写
  组合存在并发竞态(两个请求同时读到同一行会双双通过),单条 DELETE 的
  rowcount 保证并发下只有一方命中
"""
import base64
import random
from datetime import datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from .auth import hash_token
from .config import settings
from .models import Captcha, gen_id

# 字符集不含 XML 特殊字符(< > & " '),渲染进 SVG 无需转义;不要扩字符集
CHARS = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
WIDTH, HEIGHT = 120, 44


def _render_svg(text: str) -> str:
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}">',
        f'<rect width="100%" height="100%" rx="8" fill="#f4f6fb"/>',
    ]
    # 深色文字 + 浅色背景:暗色主题下呈现为一块浅色卡片,可读性最好;
    # 全部显式 fill,禁用 currentColor/<style>/class,防止继承页面前景色
    dark_colors = ["#1f2937", "#0f3d6e", "#7c2d12", "#14532d", "#4a044e"]
    for i, ch in enumerate(text):
        cx = 14 + i * 26 + random.uniform(-3, 3)  # 4 字符均布 120 宽
        cy = random.uniform(27, 33)
        parts.append(
            f'<text x="{cx:.1f}" y="{cy:.1f}" font-size="{random.randint(22, 30)}" '
            f'font-family="Georgia, \'Times New Roman\', serif" font-weight="700" '
            f'fill="{random.choice(dark_colors)}" text-anchor="middle" '
            f'transform="rotate({random.uniform(-25, 25):.1f} {cx:.1f} {cy:.1f})">{ch}</text>'
        )
    for _ in range(8):  # 干扰线(浅灰,不降可读性)
        parts.append(
            f'<line x1="{random.uniform(0, WIDTH):.1f}" y1="{random.uniform(0, HEIGHT):.1f}" '
            f'x2="{random.uniform(0, WIDTH):.1f}" y2="{random.uniform(0, HEIGHT):.1f}" '
            f'stroke="{random.choice(["#cbd5e1", "#d1d5db", "#b6c2d6"])}" '
            f'stroke-width="{random.uniform(0.8, 1.5):.1f}"/>'
        )
    for _ in range(30):  # 噪点
        parts.append(
            f'<circle cx="{random.uniform(0, WIDTH):.1f}" cy="{random.uniform(0, HEIGHT):.1f}" '
            f'r="1" fill="{random.choice(["#94a3b8", "#9ca3af"])}"/>'
        )
    parts.append("</svg>")
    return "".join(parts)


def generate() -> tuple[str, str]:
    """生成 (答案, SVG 字符串)。答案大写,校验端同样 upper 后比对。"""
    answer = "".join(random.choices(CHARS, k=4))
    return answer, _render_svg(answer)


def create_captcha(db: Session) -> tuple[str, str]:
    """入库并返回 (captcha_id, data URI)。显式传 id,免 flush 后取值。"""
    answer, svg = generate()
    captcha = Captcha(id=gen_id("c"), answer_hash=hash_token(answer), created_at=datetime.now())
    db.add(captcha)
    db.commit()
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return captcha.id, f"data:image/svg+xml;base64,{b64}"


def verify_captcha(db: Session, captcha_id: str, code: str) -> bool:
    """校验并消费验证码(一次性,原子实现)。

    命中单条原子 DELETE(rowcount==1)即通过;否则(错误答案/过期/不存在)
    按一次性语义清掉该行并返回 False,两类失败共用同一文案不泄露原因。
    """
    cutoff = datetime.now() - timedelta(minutes=settings.captcha_expire_minutes)
    result = db.execute(
        delete(Captcha).where(
            Captcha.id == captcha_id,
            Captcha.answer_hash == hash_token(code.strip().upper()),
            Captcha.created_at >= cutoff,
        )
    )
    if result.rowcount == 1:
        db.commit()
        return True
    db.execute(delete(Captcha).where(Captcha.id == captcha_id))
    db.commit()
    return False
