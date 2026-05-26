from typing import Dict, Any

from app.ai.llm import llm_client
from app.ai.prompts import DEFAULT_ANALYSIS_PROMPT, DEFAULT_GENERATION_PROMPT, DEFAULT_REVIEW_PROMPT
from app.ai.skills.role_skill_config import (
    normalize_role,
    pick_configured_skill_id,
    pick_qa_skills_enabled,
    pick_role_skill_enabled,
    resolve_effective_skill_id,
)
from app.core.config import settings
from app.modules.persistence import config_center_store


def _normalize_role(role: str) -> str:
    """兼容旧调用方：委托 normalize_role。"""
    return normalize_role(role)


def _is_llm_error_text(text: str) -> bool:
    if not isinstance(text, str):
        return True
    return text.strip().lower().startswith("error:")


def _raise_if_llm_error(text: str, stage: str) -> None:
    if _is_llm_error_text(text):
        detail = (text or "").strip()
        raise RuntimeError(f"{stage}模型调用失败：{detail}")


def _pick_role_model_options(cfg: Dict[str, Any], role: str) -> Dict[str, Any]:
    normalized_role = _normalize_role(role)
    role_target_model = str((cfg.get("role_configs") or cfg.get("ai_models") or {}).get(normalized_role) or "").strip()
    fallback: Dict[str, Any] = {}
    for item in cfg.get("ai_model_configs", []):
        if not isinstance(item, dict):
            continue
        if not item.get("enabled", True):
            continue
        if not fallback:
            fallback = {
                "model": item.get("model_name") or llm_client.model,
                "api_key": item.get("api_key") or None,
                "base_url": item.get("api_base_url") or None,
                "temperature": item.get("temperature"),
                "max_tokens": item.get("max_tokens"),
                "top_p": item.get("top_p"),
            }
        if role_target_model and str(item.get("model_name") or "").strip() == role_target_model:
            return {
                "model": item.get("model_name") or llm_client.model,
                "api_key": item.get("api_key") or None,
                "base_url": item.get("api_base_url") or None,
                "temperature": item.get("temperature"),
                "max_tokens": item.get("max_tokens"),
                "top_p": item.get("top_p"),
            }
    return fallback


def _pick_role_prompt(cfg: Dict[str, Any], role: str, fallback: str) -> str:
    normalized_role = _normalize_role(role)
    for item in cfg.get("prompt_configs", []):
        if not isinstance(item, dict):
            continue
        if not item.get("enabled", True):
            continue
        prompt_role = _normalize_role(str(item.get("role") or item.get("prompt_type") or ""))
        if prompt_role == normalized_role:
            content = str(item.get("content") or "").strip()
            if content:
                return content
    prompts = cfg.get("prompts", {})
    prompt = str((prompts or {}).get(normalized_role) or "").strip()
    return prompt or fallback


def _pick_role_skill_id(cfg: Dict[str, Any], role: str) -> str:
    """读取角色生效 skill_id（enabled 时走配置链，disabled 时回退 env/catalog）。"""
    effective, _source = resolve_effective_skill_id(cfg, role)
    return effective


def _pick_role_extra_prompt(cfg: Dict[str, Any], role: str) -> str:
    """读取「业务自定义补充 prompt」（专门用于 skill 模式下叠加的业务规则）。

    与 _pick_role_prompt 区别：
    - prompt_configs 用于「替换」整个 prompt（旧行为，向后兼容）
    - extra_prompt_configs 用于在 skill 之上「追加」业务约束
    """
    normalized_role = _normalize_role(role)
    for item in cfg.get("extra_prompt_configs", []) or []:
        if not isinstance(item, dict) or not item.get("enabled", True):
            continue
        prole = _normalize_role(str(item.get("role") or ""))
        if prole == normalized_role:
            content = str(item.get("content") or "").strip()
            if content:
                return content
    return ""


async def _load_role_config() -> Dict[str, Dict[str, Any]]:
    cfg = await config_center_store.get_config_center()
    role_configs = cfg.get("role_configs", {}) or cfg.get("ai_models", {})
    qa_skills_enabled = pick_qa_skills_enabled(cfg)
    analysis_options = _pick_role_model_options(cfg, "analysis")
    generation_options = _pick_role_model_options(cfg, "generation")
    review_options = _pick_role_model_options(cfg, "review")

    def _build(role: str, options: dict, default_prompt: str) -> dict:
        configured_skill = pick_configured_skill_id(cfg, role)
        effective_skill, skill_source = resolve_effective_skill_id(cfg, role)
        skill_enabled = pick_role_skill_enabled(cfg, role)
        return {
            **options,
            "model": options.get("model") or role_configs.get(role) or llm_client.model,
            "prompt": _pick_role_prompt(cfg, role, default_prompt),
            "skill_id": effective_skill,
            "configured_skill_id": configured_skill or effective_skill,
            "skill_source": skill_source,
            "skill_enabled": skill_enabled,
            "qa_skills_enabled": qa_skills_enabled,
            "extra_prompt": _pick_role_extra_prompt(cfg, role),
        }

    return {
        "analysis": _build("analysis", analysis_options, DEFAULT_ANALYSIS_PROMPT),
        "generation": _build("generation", generation_options, DEFAULT_GENERATION_PROMPT),
        "review": _build("review", review_options, DEFAULT_REVIEW_PROMPT),
    }
