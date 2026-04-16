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
    EMBEDDING_MODEL: str = ""

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
