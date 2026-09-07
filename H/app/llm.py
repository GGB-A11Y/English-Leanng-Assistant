"""LLM 访问层(LangChain,OpenAI 兼容协议,默认 DeepSeek)。

- build_llm:对话用(温度较高,支持流式 astream)
- generate_structured:结构化输出(函数调用 + 嵌套修复 + 校验重试)
- generate_text:普通文本生成(范文)
- LLMError:统一映射为 502 {"detail": "生成失败,请重试"}(契约 6 建议)
"""
import json
import logging
import time

from langchain_openai import ChatOpenAI

from .config import settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """LLM 生成失败(网络/超时/解析),由 main.py 统一转为 502。"""


def build_llm(temperature: float | None = None) -> ChatOpenAI:
    if not settings.llm_api_key:
        # 未配置密钥时不发起请求,直接给出可操作的错误信息
        raise LLMError("未配置 LLM 密钥,请设置环境变量 DEEPSEEK_API_KEY 后重启后端")
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=settings.chat_temperature if temperature is None else temperature,
        timeout=settings.llm_timeout,
        max_retries=settings.llm_max_retries,
        stream_usage=True,  # 流式时回带 token 用量(done 帧 usage,契约第 2 节)
    )


def _repair_nested_json_strings(data):
    """修复 DeepSeek 函数调用的已知 bug:嵌套对象/数组偶发被返回成 JSON 字符串。

    递归遍历工具调用参数,凡是以 { 或 [ 开头且以 } 或 ] 结尾的字符串,
    尝试 json.loads 还原为真正的对象/数组。
    """
    if isinstance(data, dict):
        return {k: _repair_nested_json_strings(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_repair_nested_json_strings(v) for v in data]
    if isinstance(data, str):
        s = data.strip()
        if len(s) >= 2 and s[0] in "[{" and s[-1] in "]}":
            try:
                return _repair_nested_json_strings(json.loads(s))
            except (json.JSONDecodeError, TypeError, ValueError):
                return data
    return data


def _structured_llm(schema, temperature: float):
    """函数调用方式的结构化输出:bind_tools 强制调用,拿原始参数以便修复。"""
    tool = {
        "type": "function",
        "function": {
            "name": "output",
            "description": "输出符合给定 JSON schema 的结构化数据",
            "parameters": schema.model_json_schema(),
        },
    }
    return build_llm(temperature).bind_tools(
        [tool], tool_choice={"type": "function", "function": {"name": "output"}}
    )


def _extract_args(resp) -> dict:
    """从模型响应中取结构化数据。优先工具调用参数;DeepSeek 偶发无视
    tool_choice 直接把 JSON 写在正文里(可能带 markdown 代码围栏),回退解析。"""
    if resp.tool_calls:
        return resp.tool_calls[0]["args"]
    text = resp.content if isinstance(resp.content, str) else str(resp.content)
    text = text.strip()
    if text.startswith("```"):  # 剥掉 ```json ... ``` 围栏
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return json.loads(text)


def generate_structured(schema, system: str, user: str, temperature: float | None = None, attempts: int = 3, budget: float = 100.0):
    """结构化输出:函数调用 + 嵌套字符串修复 + 全量校验,失败重试。

    不用 with_structured_output:DeepSeek 函数调用偶发把嵌套对象返回成
    JSON 字符串(如含中文/emoji 的文本),直接解析必失败且重试复现;
    这里拿到原始参数先修复再校验,只有真失败才重试(重试时温度逐次
    +0.15 以打破确定性)。契约建议生成类接口温度 0.3~0.5。

    budget: 整体时间预算(秒),超限后不再发起新的 LLM 请求
    (前端超时 120s,单次请求 30s × 3 次尝试最坏 90s)。
    """
    base_temp = settings.gen_temperature if temperature is None else temperature
    deadline = time.monotonic() + budget
    last_exc = None
    for attempt in range(1, attempts + 1):
        if time.monotonic() > deadline:
            logger.warning("LLM 结构化输出超出时间预算(%.0fs),放弃剩余尝试", budget)
            break
        temp = min(0.9, base_temp + (attempt - 1) * 0.15)
        try:
            resp = _structured_llm(schema, temp).invoke([("system", system), ("human", user)])
            args = _extract_args(resp)
            # 先修复嵌套 JSON 字符串,再解包 "params" 包装
            # (params 的值也可能被 DeepSeek 返回成 JSON 字符串,修复后才能解包)
            data = _repair_nested_json_strings(args)
            if isinstance(data, dict) and isinstance(data.get("params"), dict):
                merged = dict(data["params"])
                merged.update({k: v for k, v in data.items() if k != "params"})
                data = merged
            return schema.model_validate(data)
        except LLMError:
            raise  # 密钥缺失等可操作错误,不重试
        except Exception as exc:  # noqa: BLE001 网络/超时/解析失败统一重试
            last_exc = exc
            logger.warning("LLM 结构化输出失败(第 %d/%d 次): %s", attempt, attempts, exc)
    raise LLMError("生成失败,请重试") from last_exc


def generate_text(system: str, user: str, temperature: float | None = None) -> str:
    """普通文本生成(范文),带一次业务重试,与 generate_structured 行为一致。"""
    last_exc = None
    for attempt in range(1, 3):
        try:
            resp = build_llm(temperature).invoke([("system", system), ("human", user)])
            return resp.content if isinstance(resp.content, str) else str(resp.content)
        except LLMError:
            raise
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning("LLM 文本生成失败(第 %d/2 次): %s", attempt, exc)
    raise LLMError("生成失败,请重试") from last_exc
