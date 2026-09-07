"""后端配置:面向 DeepSeek(OpenAI 兼容协议)。

配置读取优先级(由 pydantic-settings 保证):
    1. 系统环境变量(如 LLM_API_KEY 用 setx 注入,密钥推荐放这里,不落项目文件夹)
    2. .env 文件(非敏感配置,如 base_url/model/温度)
    3. 代码默认值

切换到其他兼容服务(通义千问/智谱/OpenAI 等)只需改 LLM_BASE_URL / LLM_MODEL,
代码零改动。契约见前端 Q/app/docs/API.md。
"""
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ---- LLM(OpenAI 兼容协议,默认 DeepSeek)----
    # 密钥环境变量名:LLM_API_KEY 或 DEEPSEEK_API_KEY,两者任设其一即可(优先 LLM_API_KEY)
    llm_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("LLM_API_KEY", "DEEPSEEK_API_KEY"),
    )
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"
    chat_temperature: float = 0.8   # 对话:活泼一些(契约建议 0.7~0.9)
    gen_temperature: float = 0.4    # 词条/翻译/批改/文章:追求稳定(契约建议 0.3~0.5)
    llm_timeout: float = 30.0       # 单次 LLM 请求超时(秒);业务层 3 次尝试最坏约 90s < 前端 120s
    llm_max_retries: int = 0        # 传输层不重试(重试统一由 generate_structured 业务层控制,避免超时叠加)

    # ---- 数据库 ----
    database_url: str = "sqlite:///./english_learning.db"

    # ---- CORS ----
    # 逗号分隔的允许来源;本地单机开发默认全开,前端独立部署时建议收紧(如 http://localhost:5173)
    cors_origins: str = "*"

    # ---- 对话 ----
    chat_history_turns: int = 8     # 送入 LLM 的最近对话轮数


settings = Settings()
