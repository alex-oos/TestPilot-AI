import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # LLM Settings
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.openai.com/v1"  # Default to OpenAI URL format
    LLM_MODEL: str = "gpt-3.5-turbo" # Default model
    SQLITE_DB_PATH: str = "./data/app.db"
    JWT_SECRET_KEY: str = "please-change-this-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 15
    APP_BASE_URL: str = "http://127.0.0.1:8001"
    MCP_REQUEST_TIMEOUT_SECONDS: int = 20

    FEISHU_MCP_BASE_URL: str = ""
    FEISHU_MCP_INVOKE_PATH: str = "/invoke"
    FEISHU_MCP_TOOL_NAME: str = "read_feishu_doc"
    FEISHU_MCP_API_KEY: str = ""

    DINGTALK_MCP_BASE_URL: str = ""
    DINGTALK_MCP_INVOKE_PATH: str = "/invoke"
    DINGTALK_MCP_TOOL_NAME: str = "read_dingtalk_doc"
    DINGTALK_MCP_API_KEY: str = ""

    FEISHU_USE_CLI: bool = True
    FEISHU_CLI_BIN: str = "lark-cli"
    FEISHU_CLI_PROFILE: str = ""
    FEISHU_CLI_AS: str = "user"
    FEISHU_CLI_TIMEOUT_SECONDS: int = 20
    FEISHU_AUTO_UPLOAD_XMIND: bool = True
    FEISHU_AUTO_WRITE_MINDMAP: bool = True
    FEISHU_WIKI_CHILD_OBJ_TYPE: str = "docx"
    FEISHU_DRIVE_FOLDER_TOKEN: str = ""
    FEISHU_DRIVE_DOMAIN: str = "my.feishu.cn"
    QUALITY_GATE_ENABLE: bool = True
    EXPECTED_RESULT_EMPTY_RATIO_THRESHOLD: float = 0.35
    LLM_STEP_TIMEOUT_SECONDS: int = 240
    LLM_STEP_RETRIES: int = 0
    LLM_MAX_SOURCE_CHARS: int = 32000
    LLM_MAX_ANALYSIS_CHARS_FOR_STRATEGY: int = 12000

    # === Embedding 设置 ===
    # 真实 embedding 模型（OpenAI 兼容 API）。留空则降级为 hash embedding（仅供原型）。
    # 推荐: text-embedding-3-small（1536 维，便宜快速）
    EMBEDDING_MODEL: str = ""
    # 如果 embedding 服务和 LLM 不在同一个 base_url（例如 LLM 走代理但 embedding 走 OpenAI 官方），
    # 可单独配置。留空则复用 LLM_BASE_URL / LLM_API_KEY。
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_BASE_URL: str = ""
    EMBEDDING_DIM: int = 1536  # text-embedding-3-small=1536; text-embedding-3-large=3072
    EMBEDDING_BATCH_SIZE: int = 32

    # === 向量数据库后端 ===
    # 可选: "qdrant" (推荐) | "chroma" (兼容旧数据)
    VECTOR_DB_BACKEND: str = "qdrant"
    # Qdrant 嵌入式模式的本地路径（相对 backend/ 目录）。生产环境可改为远程 URL。
    QDRANT_PATH: str = "./data/qdrant_db"
    QDRANT_URL: str = ""  # 例如 "http://qdrant:6333"; 设置后优先使用 server 模式
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION: str = "test_case_kb_v3"

    # 跨任务召回相似度门槛（真实 embedding 用 0.55；hash embedding 用 0.65+）
    KB_SIMILARITY_THRESHOLD: float = 0.55
    KB_TOP_K: int = 5

    # === QA Skills（基于 awesome-qa-skills 的 SKILL 化 prompt 体系） ===
    # 开关：True = 使用 skill 拼装 prompt；False = 回退到旧的硬编码 prompts.py
    USE_QA_SKILLS: bool = True
    # skill 库根目录（相对 backend/ 目录）。默认指向 app/ai/skills/library
    QA_SKILLS_DIR: str = ""
    # 角色 → skill_id 覆盖（留空使用 catalog 中的默认值）
    QA_SKILL_ANALYSIS: str = ""
    QA_SKILL_GENERATION: str = ""
    QA_SKILL_REVIEW: str = ""
    QA_SKILL_SUPPLEMENT: str = ""
    QA_SKILL_DISCOVER: str = ""  # 智能路由 skill，留空使用 discover-testing

    # 项目级 overlay（多个用逗号分隔）。需在 library/_overlays/<name>/ 创建。
    QA_SKILL_OVERLAY: str = ""

    # Few-shot 与 token 控制
    QA_SKILL_FEWSHOT_ENABLED: bool = True
    QA_SKILL_FEWSHOT_MAX_CHARS: int = 1200
    QA_SKILL_PROMPT_TOKEN_BUDGET: int = 8000   # 0 = 不限制
    QA_SKILL_EXTRA_PROMPT_MAX_CHARS: int = 4000

    # 智能路由：根据需求文档自动选择 generation skill
    QA_SKILL_DISCOVER_ENABLED: bool = False

    # 三层降级链：skill -> contract-only -> legacy(prompts.py)；False=两层
    QA_SKILL_LEGACY_FALLBACK_ENABLED: bool = True

    # A/B 实验：同任务并行用两个 skill_id 跑 generation，仅记录指标对比
    QA_SKILL_AB_ENABLED: bool = False
    QA_SKILL_AB_VARIANT_GENERATION: str = ""

    # 启动健康检查严格模式：True = 任何 skill 失败/映射缺失都直接抛错（推荐生产）
    QA_SKILL_HEALTH_STRICT: bool = False
    # 是否把审计落库到独立 SQLite 表 skill_audits
    QA_SKILL_AUDIT_PERSIST: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()

if settings.JWT_SECRET_KEY == "please-change-this-secret":
    import warnings
    warnings.warn(
        "JWT_SECRET_KEY 使用默认值，请在 .env 中设置安全的密钥！",
        stacklevel=1,
    )
