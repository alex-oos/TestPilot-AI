from pydantic import BaseModel
from typing import Optional

class GenerateRequest(BaseModel):
    source_type: str  # "feishu", "dingtalk", "local"
    doc_url: Optional[str] = None

class UseCase(BaseModel):
    id: int
    module: str
    title: str
    precondition: str
    steps: str
    expected_result: str
    priority: str
