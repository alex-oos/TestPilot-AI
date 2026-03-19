"""
Background task runner - executes the 4-phase AI pipeline and updates task state.
Each phase reports progress to the task manager so SSE can stream it to frontend.
"""
from typing import Optional
from loguru import logger
from app.ai.ai import analyze_requirements, design_test_strategy, generate_test_cases, review_test_cases
from app.services.exporter import convert_cases_to_mindmap
from app.services import task_manager


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
        design = await design_test_strategy(analysis)
        
        task_manager.update_phase(task_id, "analysis", "completed", {
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
        task_manager.set_task_status(task_id, "running", status_text="用例评审中")
        task_manager.update_phase(task_id, "review", "running")
        logger.info(f"Task {task_id} | Phase 3: AI Review")
        
        review = await review_test_cases(cases, analysis)
        
        task_manager.update_phase(task_id, "review", "completed", {
            "review": review,
        })
        
        # ── All done ──────────────────────────────────────────────────────
        task_manager.set_task_status(task_id, "completed", status_text="任务已完成")
        logger.success(f"Task {task_id} completed successfully.")
        
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        task_manager.set_task_status(task_id, "failed", error=str(e), status_text="任务执行失败")
        # Mark current running phase as failed
        task = task_manager.get_task(task_id)
        if task:
            for phase_key, phase in task["phases"].items():
                if phase["status"] == "running":
                    task_manager.update_phase(task_id, phase_key, "failed")
