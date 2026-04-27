"""LLM 调用成本核算。

定价表单位：USD per 1M tokens（与 OpenAI / Anthropic 官方 catalog 一致）。
- prompt: 输入价
- completion: 输出价

支持通过 settings.LLM_PRICING_OVERRIDES 注入自定义模型，例如：
    '{"my-private-model": {"prompt": 0.5, "completion": 1.5}}'

调用：
    calc_cost_usd(model="gpt-4o-mini", prompt_tokens=1000, completion_tokens=500)
    -> {"prompt_cost": 0.00015, "completion_cost": 0.00030, "total_cost": 0.00045, ...}
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from app.core.config import settings


# Catalog 时间：2026-04，仅作为默认参考；如有变化请通过 LLM_PRICING_OVERRIDES 覆盖。
DEFAULT_PRICING: dict[str, dict[str, float]] = {
    # OpenAI GPT-4o 家族
    "gpt-4o":              {"prompt": 2.50,  "completion": 10.00},
    "gpt-4o-mini":         {"prompt": 0.15,  "completion": 0.60},
    "gpt-4-turbo":         {"prompt": 10.00, "completion": 30.00},
    "gpt-4":               {"prompt": 30.00, "completion": 60.00},
    "gpt-3.5-turbo":       {"prompt": 0.50,  "completion": 1.50},
    # OpenAI o-series（reasoning）
    "o1":                  {"prompt": 15.00, "completion": 60.00},
    "o1-mini":             {"prompt": 3.00,  "completion": 12.00},
    "o3":                  {"prompt": 10.00, "completion": 40.00},
    "o3-mini":             {"prompt": 1.10,  "completion": 4.40},
    # GPT-5 系列（参考价）
    "gpt-5":               {"prompt": 5.00,  "completion": 20.00},
    "gpt-5.4":             {"prompt": 5.00,  "completion": 20.00},
    "gpt-5.5":             {"prompt": 5.00,  "completion": 20.00},
    # Anthropic Claude
    "claude-3-5-sonnet":   {"prompt": 3.00,  "completion": 15.00},
    "claude-3-opus":       {"prompt": 15.00, "completion": 75.00},
    "claude-3-haiku":      {"prompt": 0.25,  "completion": 1.25},
    # DeepSeek（OpenAI 兼容）
    "deepseek-chat":       {"prompt": 0.27,  "completion": 1.10},
    "deepseek-coder":      {"prompt": 0.27,  "completion": 1.10},
    # 其它常见
    "qwen-max":            {"prompt": 2.40,  "completion": 9.60},
    "moonshot-v1-32k":     {"prompt": 3.30,  "completion": 3.30},
}


def _load_overrides() -> dict[str, dict[str, float]]:
    raw = (getattr(settings, "LLM_PRICING_OVERRIDES", "") or "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return {str(k): v for k, v in data.items() if isinstance(v, dict)}
    except Exception as e:  # noqa
        logger.warning("[pricing] LLM_PRICING_OVERRIDES 解析失败: {}", e)
    return {}


def lookup_unit_price(model: str) -> dict[str, float]:
    """模糊匹配定价。优先精确，再按前缀。"""
    if not model:
        return {"prompt": 0.0, "completion": 0.0}
    overrides = _load_overrides()
    if model in overrides:
        return overrides[model]
    if model in DEFAULT_PRICING:
        return DEFAULT_PRICING[model]
    # 前缀模糊匹配（覆盖 gpt-4o-2024-xx-xx 这类）
    name = model.lower()
    candidates = sorted(
        {**DEFAULT_PRICING, **overrides}.items(),
        key=lambda kv: -len(kv[0]),  # 长前缀优先
    )
    for key, price in candidates:
        if name.startswith(key.lower()):
            return price
    return {"prompt": 0.0, "completion": 0.0}


def calc_cost_usd(*, model: str, prompt_tokens: int, completion_tokens: int) -> dict[str, Any]:
    price = lookup_unit_price(model)
    p_cost = (prompt_tokens or 0) / 1_000_000.0 * price.get("prompt", 0.0)
    c_cost = (completion_tokens or 0) / 1_000_000.0 * price.get("completion", 0.0)
    return {
        "model": model,
        "unit_price": price,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "prompt_cost": round(p_cost, 6),
        "completion_cost": round(c_cost, 6),
        "total_cost": round(p_cost + c_cost, 6),
    }


def list_pricing() -> dict[str, Any]:
    return {
        "default": DEFAULT_PRICING,
        "overrides": _load_overrides(),
        "currency": "USD",
        "unit": "per_1M_tokens",
    }
