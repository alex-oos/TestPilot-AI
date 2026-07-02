from pydantic import BaseModel, Field
from typing import List, Optional


class RoleConfigs(BaseModel):
    analysis: str = Field(default="")
    generation: str = Field(default="")
    review: str = Field(default="")


class RoleConfigItem(BaseModel):
    id: str
    name: str
    role_type: str
    mapped_model_name: str
    enabled: bool = True
    created_at: str = ""
    updated_at: str = ""
    creator: str = "admin"
    modifier: str = "admin"


class AIModelItem(BaseModel):
    id: str
    name: str
    model_type: str
    api_key: str
    api_base_url: str
    model_name: str
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    enabled: bool = True
    created_at: str = ""
    updated_at: str = ""
    creator: str = "admin"
    modifier: str = "admin"


class PromptsConfig(BaseModel):
    analysis: str = Field(default="")
    generation: str = Field(default="")
    review: str = Field(default="")


class PromptConfigItem(BaseModel):
    id: str
    name: str
    role: str = ""
    prompt_type: str = ""
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
    custom_keyword: str = ""


class NotificationsConfig(BaseModel):
    feishu: ChannelConfig = Field(default_factory=ChannelConfig)
    dingtalk: ChannelConfig = Field(default_factory=ChannelConfig)
    wecom: ChannelConfig = Field(default_factory=ChannelConfig)


class ConfigCenterResponse(BaseModel):
    role_configs: RoleConfigs
    role_config_items: List[RoleConfigItem] = Field(default_factory=list)
    ai_model_configs: List[AIModelItem] = Field(default_factory=list)
    prompts: PromptsConfig
    prompt_configs: List[PromptConfigItem] = Field(default_factory=list)
    generation_behavior_configs: List[GenerationBehaviorConfigItem] = Field(default_factory=list)
    notifications: NotificationsConfig


class ConfigCenterUpdateRequest(BaseModel):
    role_configs: Optional[RoleConfigs] = None
    ai_models: Optional[RoleConfigs] = None
    role_config_items: Optional[List[RoleConfigItem]] = None
    ai_model_configs: Optional[List[AIModelItem]] = None
    prompts: Optional[PromptsConfig] = None
    prompt_configs: Optional[List[PromptConfigItem]] = None
    generation_behavior_configs: Optional[List[GenerationBehaviorConfigItem]] = None
    notifications: Optional[NotificationsConfig] = None


class AIModelConfigsUpdateRequest(BaseModel):
    ai_model_configs: List[AIModelItem]


class RoleConfigsUpdateRequest(BaseModel):
    role_configs: Optional[RoleConfigs] = None
    ai_models: Optional[RoleConfigs] = None
    role_config_items: Optional[List[RoleConfigItem]] = None


class PromptConfigsUpdateRequest(BaseModel):
    prompts: Optional[PromptsConfig] = None
    prompt_configs: Optional[List[PromptConfigItem]] = None


class GenerationBehaviorConfigsUpdateRequest(BaseModel):
    generation_behavior_configs: List[GenerationBehaviorConfigItem]


class NotificationsUpdateRequest(BaseModel):
    notifications: NotificationsConfig


class TestModelRequest(BaseModel):
    api_key: str = ""
    api_base_url: str
    model_name: str
