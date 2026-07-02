"""KB rerank 与多阶段检索单测。"""

from app.rag.knowledge_base import build_generation_history_context, rerank_kb_hits, retrieve_kb_context


def test_rerank_prefers_task_summary():
    hits = [
        {"id": "1", "similarity": 0.7, "text": "case a", "metadata": {"entry_type": "adopted_test_case"}},
        {"id": "2", "similarity": 0.68, "text": "summary", "metadata": {"entry_type": "task_summary"}},
    ]
    out = rerank_kb_hits(hits, "登录模块测试", top_k=2)
    assert out[0]["metadata"]["entry_type"] == "task_summary"


def test_build_generation_history_context_structured():
    matches = [{
        "similarity": 0.8,
        "text": "模块: 登录\n标题: 验证登录",
        "metadata": {"case_module": "登录", "case_type": "功能-正向", "entry_type": "adopted_test_case"},
    }]
    ctx = build_generation_history_context(matches)
    assert "历史模块分布" in ctx
    assert "case_type" in ctx or "功能-正向" in ctx


def test_retrieve_kb_context_empty_query():
    ctx, meta = retrieve_kb_context("analysis", "", current_task_id="task-1")
    assert ctx == ""
    assert meta.get("phase") == "analysis"
