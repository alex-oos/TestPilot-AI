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
from app.core.config import settings
from app.modules.persistence import config_center_store
from app.modules.dingtalk import read_dingtalk_doc
from app.modules.feishu import read_feishu_doc, write_feishu_doc
from app.rag.knowledge_base import (
    build_generation_history_context,
    find_similar_requirement_history,
    ingest_requirement_document,
)
from app.services.notification import notify_task_event
from app.services.exporter import convert_cases_to_mindmap
from app.services import task_manager
from app.services import file_service
from app.services.file_storage import read_uploaded_bytes

ANALYSIS_SUB_STEP_META = [
    ("parse_clean", "解析与清洗"),
    ("chunking", "需求拆分 Chunking"),
    ("metadata_build", "元数据构建"),
    ("embedding_store", "Embedding 向量化入库"),
    ("vector_retrieval", "向量检索 TopK"),
    ("rerank_filter", "重排与过滤"),
    ("prompt_assembly", "组装分析上下文"),
    ("llm_analysis", "LLM 需求分析"),
    ("strategy_design", "测试策略生成"),
]
QUALITY_BLOCKED_STATUS = "quality_blocked"


def _evaluate_expected_result_quality(cases: list[dict], threshold: float) -> dict:
    total = len(cases or [])
    if total <= 0:
        return {
            "total_cases": 0,
            "blank_expected_count": 0,
            "blank_ratio": 0.0,
            "threshold": threshold,
            "passed": False,
        }
    blank_count = sum(1 for item in cases if not str((item or {}).get("expected_result") or "").strip())
    blank_ratio = blank_count / total
    return {
        "total_cases": total,
        "blank_expected_count": blank_count,
        "blank_ratio": blank_ratio,
        "threshold": threshold,
        "passed": blank_ratio <= threshold,
    }


def _truncate_for_llm(text: str, max_chars: int) -> tuple[str, bool]:
    value = str(text or "")
    if max_chars <= 0 or len(value) <= max_chars:
        return value, False
    head = int(max_chars * 0.8)
    tail = max_chars - head
    truncated = (
        value[:head]
        + "\n\n[内容过长，已截断中间段以提升生成速度]\n\n"
        + value[-tail:]
    )
    return truncated, True


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


def _derive_requirement_name(text_content: str, fallback: str) -> str:
    for raw in (text_content or "").splitlines():
        line = (raw or "").strip()
        if not line:
            continue
        line = line.lstrip("#").strip()
        if line:
            return line[:40]
    value = (fallback or "").strip()
    if value:
        return value[:40]
    return "需求"


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
        analysis_sub_steps_state = {key: "pending" for key, _ in ANALYSIS_SUB_STEP_META}
        analysis_phase_data: dict = {}

        async def run_ai_step(coro_factory, step_name: str, retries: int | None = None):
            last_exc: Exception | None = None
            attempts = retries if isinstance(retries, int) and retries >= 0 else int(settings.LLM_STEP_RETRIES or 0)
            timeout_seconds = min(int(ai_timeout_seconds or 1500), int(settings.LLM_STEP_TIMEOUT_SECONDS or 240))
            for attempt in range(attempts + 1):
                try:
                    return await asyncio.wait_for(coro_factory(), timeout=timeout_seconds)
                except asyncio.TimeoutError as exc:
                    last_exc = RuntimeError(
                        f"{step_name}超时（>{timeout_seconds}秒），请简化输入或检查模型服务状态"
                    )
                    logger.warning(f"Task {task_id} | {step_name} timeout, attempt={attempt + 1}/{attempts + 1}")
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    logger.warning(f"Task {task_id} | {step_name} failed, attempt={attempt + 1}/{attempts + 1}: {exc}")
                if attempt < attempts:
                    await asyncio.sleep(0.6)
            raise last_exc or RuntimeError(f"{step_name}执行失败")

        def _build_analysis_sub_steps():
            return [
                {"key": key, "label": label, "status": analysis_sub_steps_state.get(key, "pending")}
                for key, label in ANALYSIS_SUB_STEP_META
            ]

        async def _push_analysis_phase(status: str = "running", patch: Optional[dict] = None):
            if patch:
                analysis_phase_data.update(patch)
            analysis_phase_data["sub_steps"] = _build_analysis_sub_steps()
            await task_manager.update_phase(task_id, "analysis", status, dict(analysis_phase_data))

        async def _set_analysis_sub_step(step_key: str, status: str):
            if step_key in analysis_sub_steps_state:
                analysis_sub_steps_state[step_key] = status
            await _push_analysis_phase("running")

        # ── Step 0: Parse document ──────────────────────────────────────────
        parse_status_text = "需求描述分析中" if source_type == "manual" else "本地文件分析中"
        await task_manager.set_task_status(task_id, "running", status_text=parse_status_text)
        text_content = ""
        await _set_analysis_sub_step("parse_clean", "running")

        if source_type in ("local", "manual") and file_content is None and file_path:
            file_content = read_uploaded_bytes(file_path)
        
        if source_type in ["feishu", "dingtalk"]:
            if source_type == "feishu":
                text_content = await run_ai_step(lambda: read_feishu_doc(doc_url or ""), "飞书文档解析")
            else:
                text_content = await run_ai_step(lambda: read_dingtalk_doc(doc_url or ""), "钉钉文档解析")
        elif source_type == "local" and file_content:
            text_content = await file_service.parse_text_from_uploaded_file(
                file_name=file_name or "upload.bin",
                file_content=file_content,
            )
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
        await _set_analysis_sub_step("parse_clean", "completed")
        llm_source_text, source_truncated = _truncate_for_llm(
            text_content,
            int(settings.LLM_MAX_SOURCE_CHARS or 32000),
        )
        if source_type in {"feishu", "dingtalk"}:
            current_task_name = str((task_snapshot or {}).get("task_name") or "").strip()
            if current_task_name in {"", file_service.ONLINE_TASK_NAME_PLACEHOLDER}:
                derived_task_name = _derive_requirement_name(text_content, fallback="在线文档需求")
                if derived_task_name:
                    await task_manager.set_task_name(task_id, derived_task_name)
                    task_snapshot = await task_manager.get_task(task_id)

        # ── Step 0.5: Requirement KB ingest + retrieval ───────────────────
        await _set_analysis_sub_step("chunking", "running")
        kb_ingest = await asyncio.to_thread(
            ingest_requirement_document,
            task_id=task_id,
            text=text_content,
            source_type=source_type,
            file_name=file_name,
            submitter=submitter,
        )
        await _set_analysis_sub_step("chunking", "completed")
        await _set_analysis_sub_step("metadata_build", "completed")
        await _set_analysis_sub_step("embedding_store", "completed")

        await _set_analysis_sub_step("vector_retrieval", "running")
        similar_history = await asyncio.to_thread(
            find_similar_requirement_history,
            query_text=text_content,
            current_task_id=task_id,
            top_k=5,
        )
        await _set_analysis_sub_step("vector_retrieval", "completed")
        await _set_analysis_sub_step("rerank_filter", "completed")

        await _set_analysis_sub_step("prompt_assembly", "running")
        history_context = build_generation_history_context(similar_history) if similar_history else ""
        await _set_analysis_sub_step("prompt_assembly", "completed")
        
        # ── Phase 1: 需求分析 ─────────────────────────────────────────────
        await task_manager.set_task_status(task_id, "running", status_text="需求分析中")
        await _push_analysis_phase("running", {
            "source_text": text_content,
            "knowledge_base": {
                "ingested_chunks": kb_ingest.get("chunk_count", 0),
                "similar_history_count": len(similar_history),
                "retrieval_mode": "history_enhanced" if similar_history else "cold_start",
            },
        })
        logger.info(f"Task {task_id} | Phase 1: Requirement Analysis")
        analysis_output_mode = await _read_output_mode()
        
        await _set_analysis_sub_step("llm_analysis", "running")
        analysis = await run_ai_step(lambda: analyze_requirements(llm_source_text), "需求分析")
        await _set_analysis_sub_step("llm_analysis", "completed")
        if _is_llm_error(analysis):
            raise RuntimeError(f"需求分析失败: {analysis}")
        # 实时模式下，需求分析结果先落库，保证页面可立即展示
        if analysis_output_mode == "stream":
            await _push_analysis_phase("running", {
                "source_text": text_content,
                "analysis": analysis,
                "output_mode": analysis_output_mode,
                "knowledge_base": {
                    "ingested_chunks": kb_ingest.get("chunk_count", 0),
                    "similar_history_count": len(similar_history),
                    "retrieval_mode": "history_enhanced" if similar_history else "cold_start",
                    "history_preview": similar_history[:3],
                },
            })

        await task_manager.set_task_status(task_id, "running", status_text="测试策略生成中")
        await _set_analysis_sub_step("strategy_design", "running")
        strategy_input, strategy_truncated = _truncate_for_llm(
            analysis,
            int(settings.LLM_MAX_ANALYSIS_CHARS_FOR_STRATEGY or 12000),
        )
        design = await run_ai_step(lambda: design_test_strategy(strategy_input), "测试策略生成")
        await _set_analysis_sub_step("strategy_design", "completed")
        if _is_llm_error(design):
            raise RuntimeError(f"测试策略生成失败: {design}")
        
        analysis_payload = {
            "source_text": text_content,
            "analysis": analysis,
            "design": design,
            "output_mode": analysis_output_mode,
                "knowledge_base": {
                    "ingested_chunks": kb_ingest.get("chunk_count", 0),
                    "similar_history_count": len(similar_history),
                    "retrieval_mode": "history_enhanced" if similar_history else "cold_start",
                    "history_preview": similar_history,
                },
                "llm_guardrails": {
                    "source_truncated": source_truncated,
                    "strategy_input_truncated": strategy_truncated,
                    "step_timeout_seconds": min(
                        int(ai_timeout_seconds or 1500),
                        int(settings.LLM_STEP_TIMEOUT_SECONDS or 240),
                    ),
                    "step_retries": int(settings.LLM_STEP_RETRIES or 0),
                },
            }
        analysis_json_file = _save_phase_json(task_id, "analysis", analysis_payload)
        analysis_payload["analysis_json_file"] = analysis_json_file
        analysis_phase_data.update(analysis_payload)
        await _push_analysis_phase("completed")
        
        # ── Phase 2: 用例编写 ─────────────────────────────────────────────
        await task_manager.set_task_status(task_id, "running", status_text="用例编写中")
        generation_output_mode = await _read_output_mode()
        await task_manager.update_phase(task_id, "generation", "running", {
            "output_mode": generation_output_mode,
        })
        logger.info(f"Task {task_id} | Phase 2: Test Case Generation")
        cases = await run_ai_step(lambda: generate_test_cases(design, history_context), "测试用例生成")
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

        quality_gate = _evaluate_expected_result_quality(
            cases=cases,
            threshold=float(settings.EXPECTED_RESULT_EMPTY_RATIO_THRESHOLD or 0.35),
        )
        if settings.QUALITY_GATE_ENABLE and not quality_gate["passed"]:
            fail_msg = (
                "模型输出质量不足：expected_result 为空比例超阈值，已终止任务。"
                f" 空白占比={quality_gate['blank_ratio']:.2%}，阈值={quality_gate['threshold']:.2%}"
            )
            await task_manager.update_phase(
                task_id,
                "generation",
                "failed",
                {
                    "cases": cases,
                    "output_mode": generation_output_mode,
                    "cases_json_file": generation_payload.get("cases_json_file"),
                    "quality_gate": quality_gate,
                },
                error=fail_msg,
            )
            await task_manager.set_task_status(
                task_id,
                QUALITY_BLOCKED_STATUS,
                error=fail_msg,
                status_text="模型输出质量不足",
            )
            await notify_task_event(
                task_id=task_id,
                task_status="模型输出质量不足",
                status_text="模型输出质量不足：expected_result 缺失过多，任务已终止",
                error=fail_msg,
            )
            return

        # 飞书源任务：在需求文档下创建“需求名+测试用例”子文档并写入思维导图内容
        try:
            feishu_mindmap_url = ""
            if source_type == "feishu" and str(doc_url or "").strip():
                requirement_name = _derive_requirement_name(
                    text_content=text_content,
                    fallback=(task_snapshot or {}).get("task_name") or "",
                )
                feishu_mindmap_url = await write_feishu_doc(
                    doc_url=doc_url or "",
                    cases=cases,
                    title=f"{requirement_name}测试用例",
                )
            if feishu_mindmap_url:
                await task_manager.set_task_feishu_mindmap_url(task_id, feishu_mindmap_url)
                await task_manager.update_phase(
                    task_id,
                    "generation",
                    "completed",
                    {
                        "cases": cases,
                        "output_mode": generation_output_mode,
                        "cases_json_file": generation_payload.get("cases_json_file"),
                        "feishu_mindmap_url": feishu_mindmap_url,
                    },
                )
        except Exception as write_error:  # noqa: BLE001
            logger.warning("Task {} write cases back to Feishu doc skipped: {}", task_id, write_error)
            await task_manager.update_phase(
                task_id,
                "generation",
                "completed",
                {
                    "cases": cases,
                    "output_mode": generation_output_mode,
                    "cases_json_file": generation_payload.get("cases_json_file"),
                    "feishu_mindmap_error": str(write_error),
                },
            )
        
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
