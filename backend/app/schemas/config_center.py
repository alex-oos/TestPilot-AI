from pydantic import BaseModel, Field
from typing import List, Optional


class AIModelsConfig(BaseModel):
    analysis: str = Field(default="")
    generation: str = Field(default="")
    review: str = Field(default="")


class AIModelItem(BaseModel):
    id: str
    name: str
    model_type: str
    role: str
    api_key: str
    api_base_url: str
    model_name: str
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    enabled: bool = True
    created_at: str = ""


class PromptsConfig(BaseModel):
    analysis: str = Field(default="")
    generation: str = Field(default="")
    review: str = Field(default="")


class PromptConfigItem(BaseModel):
    id: str
    name: str
    prompt_type: str
    content: str
    enabled: bool = True
    created_at: str = ""
    updated_at: str = ""
    creator: str = "admin"


class GenerationBehaviorConfigItem(BaseModel):
    id: str
    name: str
    output_mode: str = "stream"
    enable_ai_review: bool = True
    review_timeout_seconds: int = 1500
    enabled: bool = True
    created_at: str = ""
    updated_at: str = ""


class ChannelConfig(BaseModel):
    name: str = ""
    enabled: bool = False
    webhook: str = ""
    secret: str = ""
    business_types: List[str] = Field(default_factory=list)


class NotificationsConfig(BaseModel):
    feishu: ChannelConfig = Field(default_factory=ChannelConfig)
    dingtalk: ChannelConfig = Field(default_factory=ChannelConfig)
    wecom: ChannelConfig = Field(default_factory=ChannelConfig)


class ConfigCenterResponse(BaseModel):
    ai_models: AIModelsConfig
    ai_model_configs: List[AIModelItem] = Field(default_factory=list)
    prompts: PromptsConfig
    prompt_configs: List[PromptConfigItem] = Field(default_factory=list)
    generation_behavior_configs: List[GenerationBehaviorConfigItem] = Field(default_factory=list)
    notifications: NotificationsConfig


class ConfigCenterUpdateRequest(BaseModel):
    ai_models: Optional[AIModelsConfig] = None
    ai_model_configs: Optional[List[AIModelItem]] = None
    prompts: Optional[PromptsConfig] = None
    prompt_configs: Optional[List[PromptConfigItem]] = None
    generation_behavior_configs: Optional[List[GenerationBehaviorConfigItem]] = None
    notifications: Optional[NotificationsConfig] = None


class TestModelRequest(BaseModel):
    api_key: str = ""
    api_base_url: str
    model_name: str
