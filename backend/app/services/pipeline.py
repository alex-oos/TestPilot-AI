"""
Background task runner - executes upload->analysis->generation->review->manual_review pipeline.
Each phase reports progress to the task manager so SSE can stream it to frontend.
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger
from app.ai.ai import analyze_requirements, design_test_strategy, generate_test_cases, review_test_cases
from app.modules.persistence import config_center_store
from app.services.notification import notify_task_event
from app.services.exporter import convert_cases_to_mindmap
from app.services import task_manager
from app.services.file_storage import read_uploaded_bytes


def _is_llm_error(text: str) -> bool:
    if not isinstance(text, str):
        return True
    return text.strip().lower().startswith("error:")


def _save_phase_json(task_id: str, phase: str, payload: dict) -> str:
    base_dir = Path(__file__).resolve().parents[2] / "data" / "generated" / task_id
    base_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    file_path = base_dir / f"{phase}_{ts}.json"
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(file_path)


def _normalize_role(value: str) -> str:
    role = (value or "").strip().lower()
    if role in {"analysis", "需求分析", "需求分析角色"}:
        return "analysis"
    if role in {"generation", "用例编写", "测试用例编写", "测试用例编写角色"}:
        return "generation"
    if role in {"review", "用例评审", "测试用例评审", "测试用例评审角色"}:
        return "review"
    return role


def _role_display_name(role: str) -> str:
    mapping = {
        "analysis": "需求分析",
        "generation": "用例编写",
        "review": "用例评审",
    }
    return mapping.get(role, role)


async def _validate_local_runtime_config(required_roles: Optional[list[str]] = None) -> dict:
    cfg = await config_center_store.get_config_center()

    enabled_models = [x for x in cfg.get("ai_model_configs", []) if isinstance(x, dict) and x.get("enabled", True)]
    enabled_prompts = [x for x in cfg.get("prompt_configs", []) if isinstance(x, dict) and x.get("enabled", True)]
    has_any_enabled_model = bool(enabled_models)
    enabled_model_names = {str(x.get("model_name") or "").strip() for x in enabled_models if str(x.get("model_name") or "").strip()}
    role_configs_map = cfg.get("role_configs", {}) or cfg.get("ai_models", {}) or {}
    enabled_prompt_roles = {
        _normalize_role(str(x.get("role") or x.get("prompt_type") or ""))
        for x in enabled_prompts
        if str(x.get("content") or "").strip()
    }

    roles = required_roles or []
    for role in roles:
        normalized_role = _normalize_role(role)
        role_name = _role_display_name(normalized_role)
        if not has_any_enabled_model:
            raise RuntimeError("本地配置缺失：请在 AI 配置中启用至少一个模型")
        mapped_model_name = str(role_configs_map.get(normalized_role) or "").strip()
        if not mapped_model_name:
            raise RuntimeError(f"本地配置缺失：请在角色配置页面为“{role_name}”选择模型")
        if mapped_model_name not in enabled_model_names:
            active = "、".join(sorted(enabled_model_names)) or "无"
            raise RuntimeError(
                f"本地配置缺失：角色“{role_name}”映射模型“{mapped_model_name}”未启用（当前已启用：{active}）"
            )
        if normalized_role not in enabled_prompt_roles:
            active = "、".join(sorted([_role_display_name(x) for x in enabled_prompt_roles if x])) or "无"
            raise RuntimeError(
                f"本地配置缺失：请在提示词配置中启用“{role_name}”类型提示词（当前已启用：{active}）"
            )

    enabled_behaviors = [
        x for x in cfg.get("generation_behavior_configs", []) if isinstance(x, dict) and x.get("enabled", True)
    ]
    if enabled_behaviors:
        return enabled_behaviors[0]
    # 生成行为配置缺失时走默认值，不阻断任务执行前置校验。
    return {
        "enable_ai_review": True,
        "review_timeout_seconds": 1500,
        "output_mode": "stream",
    }


async def _read_output_mode() -> str:
    cfg = await config_center_store.get_config_center()
    enabled_behaviors = [
        x for x in cfg.get("generation_behavior_configs", []) if isinstance(x, dict) and x.get("enabled", True)
    ]
    if not enabled_behaviors:
        return "stream"
    mode = str(enabled_behaviors[0].get("output_mode") or "stream").strip().lower()
    return "full" if mode == "full" else "stream"


async def run_generation_pipeline(
    task_id: str,
    source_type: str,
    doc_url: Optional[str],
    file_content: Optional[bytes],
    file_name: Optional[str],
    file_path: Optional[str] = None,
    submitter: Optional[str] = None,
):
    """
    The complete AI generation pipeline.
    Runs as a background task, updating the task_manager at each phase.
    
    Nodes:
      1. analysis      → 需求分析
      2. generation    → 用例编写
      3. review        → 用例评审（自动修正用例）
      4. manual_review → 人工审核（批量采纳后完成）
    """
    try:
        behavior_cfg = await _validate_local_runtime_config(["analysis", "generation", "review"])
        ai_timeout_seconds = int(behavior_cfg.get("review_timeout_seconds") or 1500)

        async def run_ai_step(coro_factory, step_name: str, retries: int = 1):
            last_exc: Exception | None = None
            for attempt in range(retries + 1):
                try:
                    return await asyncio.wait_for(coro_factory(), timeout=ai_timeout_seconds)
                except asyncio.TimeoutError as exc:
                    last_exc = RuntimeError(
                        f"{step_name}超时（>{ai_timeout_seconds}秒），请在生成行为配置中调整超时设置"
                    )
                    logger.warning(f"Task {task_id} | {step_name} timeout, attempt={attempt + 1}/{retries + 1}")
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    logger.warning(f"Task {task_id} | {step_name} failed, attempt={attempt + 1}/{retries + 1}: {exc}")
                if attempt < retries:
                    await asyncio.sleep(0.6)
            raise last_exc or RuntimeError(f"{step_name}执行失败")

        # ── Step 0: Parse document ──────────────────────────────────────────
        parse_status_text = "需求描述分析中" if source_type == "manual" else "本地文件分析中"
        await task_manager.set_task_status(task_id, "running", status_text=parse_status_text)
        text_content = ""

        if source_type in ("local", "manual") and file_content is None and file_path:
            file_content = read_uploaded_bytes(file_path)
        
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
        elif source_type == "manual" and file_content:
            text_content = file_content.decode("utf-8", errors="ignore")

        # 兼容上传阶段附加输入：context / requirements
        task_snapshot = await task_manager.get_task(task_id)
        upload_phase = ((task_snapshot or {}).get("phases") or {}).get("upload") or {}
        upload_data = upload_phase.get("data") if isinstance(upload_phase, dict) else {}
        if isinstance(upload_data, dict):
            context_text = str(upload_data.get("context") or "").strip()
            requirements_text = str(upload_data.get("requirements") or "").strip()
            if context_text:
                text_content += f"\n\n补充上下文：\n{context_text}"
            if requirements_text:
                text_content += f"\n\n额外要求：\n{requirements_text}"
        
        if not text_content.strip():
            raise ValueError("无法从文档中提取到文本内容")
        
        # ── Phase 1: 需求分析 ─────────────────────────────────────────────
        await task_manager.set_task_status(task_id, "running", status_text="需求分析中")
        await task_manager.update_phase(task_id, "analysis", "running", {
            "source_text": text_content,
        })
        logger.info(f"Task {task_id} | Phase 1: Requirement Analysis")
        analysis_output_mode = await _read_output_mode()
        
        analysis = await run_ai_step(lambda: analyze_requirements(text_content), "需求分析")
        if _is_llm_error(analysis):
            raise RuntimeError(f"需求分析失败: {analysis}")
        # 实时模式下，需求分析结果先落库，保证页面可立即展示
        if analysis_output_mode == "stream":
            await task_manager.update_phase(task_id, "analysis", "running", {
                "source_text": text_content,
                "analysis": analysis,
                "output_mode": analysis_output_mode,
            })

        design = await run_ai_step(lambda: design_test_strategy(analysis), "测试策略生成")
        if _is_llm_error(design):
            raise RuntimeError(f"测试策略生成失败: {design}")
        
        analysis_payload = {
            "source_text": text_content,
            "analysis": analysis,
            "design": design,
            "output_mode": analysis_output_mode,
        }
        analysis_json_file = _save_phase_json(task_id, "analysis", analysis_payload)
        analysis_payload["analysis_json_file"] = analysis_json_file
        await task_manager.update_phase(task_id, "analysis", "completed", analysis_payload)
        
        # ── Phase 2: 用例编写 ─────────────────────────────────────────────
        await task_manager.set_task_status(task_id, "running", status_text="用例编写中")
        generation_output_mode = await _read_output_mode()
        await task_manager.update_phase(task_id, "generation", "running", {
            "output_mode": generation_output_mode,
        })
        logger.info(f"Task {task_id} | Phase 2: Test Case Generation")
        cases = await run_ai_step(lambda: generate_test_cases(design), "测试用例生成")
        # 实时模式下，用例生成结果先落库，保证页面可立即展示
        if generation_output_mode == "stream":
            await task_manager.update_phase(task_id, "generation", "running", {
                "cases": cases,
                "output_mode": generation_output_mode,
            })
        mindmap = convert_cases_to_mindmap(cases)
        
        generation_payload = {
            "cases": cases,
            "output_mode": generation_output_mode,
        }
        generation_json_file = _save_phase_json(task_id, "generation", {"cases": cases})
        generation_payload["cases_json_file"] = generation_json_file
        await task_manager.update_phase(task_id, "generation", "completed", generation_payload)
        await task_manager.set_task_mindmap(task_id, mindmap)
        
        # ── Phase 3: 用例评审 ─────────────────────────────────────────────
        review = {}
        review_output_mode = await _read_output_mode()
        if behavior_cfg.get("enable_ai_review", True):
            await task_manager.set_task_status(task_id, "running", status_text="用例评审中")
            await task_manager.update_phase(task_id, "review", "running", {
                "output_mode": review_output_mode,
            })
            logger.info(f"Task {task_id} | Phase 3: AI Review")
            review = await run_ai_step(lambda: review_test_cases(cases, analysis), "测试用例评审")
            reviewed_cases = review.get("reviewed_cases") if isinstance(review, dict) else None
            if isinstance(reviewed_cases, list) and reviewed_cases:
                cases = reviewed_cases
                await task_manager.update_phase(
                    task_id,
                    "generation",
                    "completed",
                    {
                        "cases": cases,
                        "output_mode": generation_output_mode,
                        "cases_json_file": _save_phase_json(task_id, "generation_reviewed", {"cases": cases}),
                    },
                )
                await task_manager.set_task_mindmap(task_id, convert_cases_to_mindmap(cases))
            if review_output_mode == "stream":
                await task_manager.update_phase(task_id, "review", "running", {
                    "review": review,
                    "output_mode": review_output_mode,
                })

            await task_manager.update_phase(task_id, "review", "completed", {
                "review": review,
                "output_mode": review_output_mode,
            })
        else:
            review = {
                "summary": "已在生成行为配置中关闭 AI 评审",
                "issues": [],
                "suggestions": [],
                "missing_scenarios": [],
                "quality_score": 0,
            }
            await task_manager.update_phase(task_id, "review", "completed", {
                "review": review,
                "output_mode": review_output_mode,
            })
        
        # ── Phase 4: 人工审核 ────────────────────────────────────────────
        await task_manager.update_phase(
            task_id,
            "manual_review",
            "running",
            {
                "review_summary": str(review.get("summary") or "") if isinstance(review, dict) else "",
                "pending_adoption_count": len(cases),
                "status": "人工审核中",
            },
        )
        await task_manager.set_task_status(task_id, "manual_reviewing", status_text="人工审核中")
        await notify_task_event(
            task_id=task_id,
            task_status="人工审核中",
            status_text="测试用例评审已完成，请人工批量采纳后完成任务",
        )
        logger.success(f"Task {task_id} entered manual review stage.")
        
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        task = await task_manager.get_task(task_id)
        failed_phase = None
        if task:
            for phase_key, phase in task["phases"].items():
                if phase["status"] == "running":
                    failed_phase = phase_key
                    await task_manager.update_phase(task_id, phase_key, "failed")
                    break

        fail_status = "failed"
        status_text = "执行异常"
        if failed_phase == "analysis":
            fail_status = "analysis_failed"
            status_text = "需求分析异常"
        elif failed_phase == "generation":
            fail_status = "generation_failed"
            status_text = "用例编写异常"
        elif failed_phase == "review":
            fail_status = "review_failed"
            status_text = "用例评审异常"
        elif failed_phase == "manual_review":
            status_text = "人工审核异常"

        await task_manager.set_task_status(task_id, fail_status, error=str(e), status_text=status_text)
        await notify_task_event(
            task_id=task_id,
            task_status=status_text if fail_status != "failed" else "执行异常",
            status_text=status_text,
            error=str(e),
        )
