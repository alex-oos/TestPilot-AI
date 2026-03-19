"""
Background task runner - executes the 4-phase AI pipeline and updates task state.
Each phase reports progress to the task manager so SSE can stream it to frontend.
"""
import asyncio
from typing import Optional
from loguru import logger
from app.ai.ai import analyze_requirements, design_test_strategy, generate_test_cases, review_test_cases
from app.core import database
from app.services.notification import notify_task_event
from app.services.exporter import convert_cases_to_mindmap
from app.services import task_manager


def _is_llm_error(text: str) -> bool:
    if not isinstance(text, str):
        return True
    return text.strip().lower().startswith("error:")


def _validate_local_runtime_config() -> dict:
    cfg = database.get_config_center()

    enabled_models = [x for x in cfg.get("ai_model_configs", []) if isinstance(x, dict) and x.get("enabled", True)]
    enabled_prompts = [x for x in cfg.get("prompt_configs", []) if isinstance(x, dict) and x.get("enabled", True)]
    enabled_behaviors = [
        x for x in cfg.get("generation_behavior_configs", []) if isinstance(x, dict) and x.get("enabled", True)
    ]

    for role in ("analysis", "generation", "review"):
        if not any(str(x.get("role") or "") == role for x in enabled_models):
            raise RuntimeError(f"本地配置缺失：请在 AI 配置中启用“{role}”角色模型")
        if not any(str(x.get("prompt_type") or "") == role and str(x.get("content") or "").strip() for x in enabled_prompts):
            raise RuntimeError(f"本地配置缺失：请在提示词配置中启用“{role}”类型提示词")

    if not enabled_behaviors:
        raise RuntimeError("本地配置缺失：请在生成行为配置中启用至少一条配置")
    return enabled_behaviors[0]


async def run_generation_pipeline(
    task_id: str,
    source_type: str,
    doc_url: Optional[str],
    file_content: Optional[bytes],
    file_name: Optional[str]
):
    """
    The complete 3-node AI generation pipeline.
    Runs as a background task, updating the task_manager at each phase.
    
    Nodes:
      1. analysis  → 需求分析
      2. generation → 用例编写 (includes test strategy)
      3. review    → 用例评审
    """
    try:
        biz_type = "api" if source_type in ("feishu", "dingtalk") else "ui_auto"
        behavior_cfg = _validate_local_runtime_config()

        # ── Step 0: Parse document ──────────────────────────────────────────
        task_manager.set_task_status(task_id, "running", status_text="本地文件分析中")
        text_content = ""
        
        if source_type in ["feishu", "dingtalk"]:
            text_content = (
                f"[在线文档] 来源: {doc_url}\n"
                "飞书/钉钉文档需配置相应Token才能真实获取。此为演示内容，请改用本地上传体验完整流程。"
            )
        elif source_type == "local" and file_content:
            import io
            import os
            import docx
            from pypdf import PdfReader
            
            ext = os.path.splitext(file_name or "")[1].lower()
            if ext in (".md", ".txt"):
                text_content = file_content.decode("utf-8", errors="ignore")
            elif ext == ".docx":
                doc = docx.Document(io.BytesIO(file_content))
                text_content = "\n".join([p.text for p in doc.paragraphs])
            elif ext == ".pdf":
                pdf = PdfReader(io.BytesIO(file_content))
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        text_content += t + "\n"
            else:
                text_content = file_content.decode("utf-8", errors="ignore")
        
        if not text_content.strip():
            raise ValueError("无法从文档中提取到文本内容")
        
        # ── Phase 1: 需求分析 ─────────────────────────────────────────────
        task_manager.set_task_status(task_id, "running", status_text="需求分析中")
        task_manager.update_phase(task_id, "analysis", "running")
        logger.info(f"Task {task_id} | Phase 1: Requirement Analysis")
        
        analysis = await analyze_requirements(text_content)
        if _is_llm_error(analysis):
            raise RuntimeError(f"需求分析失败: {analysis}")

        design = await design_test_strategy(analysis)
        if _is_llm_error(design):
            raise RuntimeError(f"测试策略生成失败: {design}")
        
        task_manager.update_phase(task_id, "analysis", "completed", {
            "source_text": text_content,
            "analysis": analysis,
            "design": design,
        })
        
        # ── Phase 2: 用例编写 ─────────────────────────────────────────────
        task_manager.set_task_status(task_id, "running", status_text="用例编写中")
        task_manager.update_phase(task_id, "generation", "running")
        logger.info(f"Task {task_id} | Phase 2: Test Case Generation")
        
        cases = await generate_test_cases(design)
        mindmap = convert_cases_to_mindmap(cases)
        
        task_manager.update_phase(task_id, "generation", "completed", {
            "cases": cases,
        })
        task_manager.set_task_mindmap(task_id, mindmap)
        
        # ── Phase 3: 用例评审 ─────────────────────────────────────────────
        if behavior_cfg.get("enable_ai_review", True):
            task_manager.set_task_status(task_id, "running", status_text="用例评审中")
            task_manager.update_phase(task_id, "review", "running")
            logger.info(f"Task {task_id} | Phase 3: AI Review")

            timeout_seconds = int(behavior_cfg.get("review_timeout_seconds") or 1500)
            review = await asyncio.wait_for(review_test_cases(cases, analysis), timeout=timeout_seconds)

            task_manager.update_phase(task_id, "review", "completed", {
                "review": review,
            })
        else:
            task_manager.update_phase(task_id, "review", "completed", {
                "review": {
                    "summary": "已在生成行为配置中关闭 AI 评审",
                    "issues": [],
                    "suggestions": [],
                    "missing_scenarios": [],
                    "quality_score": 0,
                },
            })
        
        # ── All done ──────────────────────────────────────────────────────
        task_manager.set_task_status(task_id, "completed", status_text="任务已完成")
        await notify_task_event(
            task_id=task_id,
            task_status="已完成",
            status_text="任务已完成",
            biz_type=biz_type,
        )
        logger.success(f"Task {task_id} completed successfully.")
        
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        task = task_manager.get_task(task_id)
        failed_phase = None
        if task:
            for phase_key, phase in task["phases"].items():
                if phase["status"] == "running":
                    failed_phase = phase_key
                    task_manager.update_phase(task_id, phase_key, "failed")
                    break

        status_text = "任务执行失败"
        if failed_phase == "analysis":
            status_text = "需求分析异常"
        elif failed_phase == "generation":
            status_text = "用例编写异常"
        elif failed_phase == "review":
            status_text = "用例评审异常"

        task_manager.set_task_status(task_id, "failed", error=str(e), status_text=status_text)
        await notify_task_event(
            task_id=task_id,
            task_status="执行异常",
            status_text=status_text,
            error=str(e),
            biz_type="api" if source_type in ("feishu", "dingtalk") else "ui_auto",
        )
