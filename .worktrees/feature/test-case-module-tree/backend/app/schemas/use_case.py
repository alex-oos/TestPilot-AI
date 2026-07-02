from pydantic import BaseModel
from typing import Optional, List, Dict, Any


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


class MissingScenario(BaseModel):
    module: str
    scenario: str
    test_point: str


class ReviewResult(BaseModel):
    issues: List[str] = []
    suggestions: List[str] = []
    missing_scenarios: List[MissingScenario] = []
    quality_score: int = 0
    summary: str = ""


class GenerateResponse(BaseModel):
    analysis: str
    design: str
    cases: List[Dict[str, Any]]
    review: Dict[str, Any]
    mindmap: str


class SyncRequest(BaseModel):
    cases: List[Dict[str, Any]]


class ExportRequest(BaseModel):
    cases: List[Dict[str, Any]]
    title: Optional[str] = "AI自动生成测试用例"


class DeleteTasksRequest(BaseModel):
    task_ids: List[str]


class ReviewCaseItem(BaseModel):
    id: Optional[Any] = None
    module: Optional[str] = ""
    title: Optional[str] = ""
    precondition: Optional[str] = ""
    steps: Optional[str] = ""
    expected_result: Optional[str] = ""
    priority: Optional[str] = "中"
    adoption_status: Optional[str] = "accepted"


class UpdateReviewCasesRequest(BaseModel):
    cases: List[ReviewCaseItem]
