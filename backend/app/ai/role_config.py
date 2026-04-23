from typing import Dict, Any

from app.ai.llm import llm_client
from app.ai.prompts import DEFAULT_ANALYSIS_PROMPT, DEFAULT_GENERATION_PROMPT, DEFAULT_REVIEW_PROMPT
from app.core.config import settings
from app.modules.persistence import config_center_store


def _normalize_role(role: str) -> str:
    value = (role or "").strip().lower()
    if value in {"analysis", "需求分析", "需求分析角色"}:
        return "analysis"
    if value in {"generation", "用例编写", "用例编写角色", "测试用例编写"}:
        return "generation"
    if value in {"review", "用例评审", "用例评审角色"}:
        return "review"
    return value


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
    """读取角色对应的 skill_id 覆盖。

    优先级：配置中心 skill_configs[role] > 配置中心 skills[role] > .env 全局覆盖 > 空（用 catalog 默认）。
    """
    normalized_role = _normalize_role(role)
    skill_configs = cfg.get("skill_configs", []) or []
    if isinstance(skill_configs, list):
        for item in skill_configs:
            if not isinstance(item, dict) or not item.get("enabled", True):
                continue
            sk_role = _normalize_role(str(item.get("role") or ""))
            if sk_role == normalized_role:
                sid = str(item.get("skill_id") or "").strip()
                if sid:
                    return sid
    skills_map = cfg.get("skills", {}) or {}
    sid = str(skills_map.get(normalized_role) or "").strip()
    if sid:
        return sid

    env_map = {
        "analysis": getattr(settings, "QA_SKILL_ANALYSIS", ""),
        "generation": getattr(settings, "QA_SKILL_GENERATION", ""),
        "review": getattr(settings, "QA_SKILL_REVIEW", ""),
        "supplement": getattr(settings, "QA_SKILL_SUPPLEMENT", ""),
    }
    return str(env_map.get(normalized_role, "") or "").strip()


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
    analysis_options = _pick_role_model_options(cfg, "analysis")
    generation_options = _pick_role_model_options(cfg, "generation")
    review_options = _pick_role_model_options(cfg, "review")
    return {
        "analysis": {
            **analysis_options,
            "model": analysis_options.get("model") or role_configs.get("analysis") or llm_client.model,
            "prompt": _pick_role_prompt(cfg, "analysis", DEFAULT_ANALYSIS_PROMPT),
            "skill_id": _pick_role_skill_id(cfg, "analysis"),
            "extra_prompt": _pick_role_extra_prompt(cfg, "analysis"),
        },
        "generation": {
            **generation_options,
            "model": generation_options.get("model") or role_configs.get("generation") or llm_client.model,
            "prompt": _pick_role_prompt(cfg, "generation", DEFAULT_GENERATION_PROMPT),
            "skill_id": _pick_role_skill_id(cfg, "generation"),
            "extra_prompt": _pick_role_extra_prompt(cfg, "generation"),
        },
        "review": {
            **review_options,
            "model": review_options.get("model") or role_configs.get("review") or llm_client.model,
            "prompt": _pick_role_prompt(cfg, "review", DEFAULT_REVIEW_PROMPT),
            "skill_id": _pick_role_skill_id(cfg, "review"),
            "extra_prompt": _pick_role_extra_prompt(cfg, "review"),
        },
    }
