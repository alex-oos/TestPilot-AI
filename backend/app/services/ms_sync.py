import httpx
from loguru import logger
from typing import List, Dict, Any
from app.core.config import settings


async def sync_cases_to_ms(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    同步测试用例到 MS 测试管理平台（如 Azure DevOps Test Plans）。
    
    配置方式：在 .env 中设置 MS_API_URL 和 MS_API_KEY。
    若未配置，则以模拟模式运行（返回成功响应）。
    """
    ms_api_url = getattr(settings, 'MS_API_URL', None)
    ms_api_key = getattr(settings, 'MS_API_KEY', None)
    
    logger.info(f"MS Sync: Starting sync for {len(cases)} test cases")
    
    # === 模拟模式（未配置真实MS平台时） ===
    if not ms_api_url or ms_api_url == "https://your-ms-platform/api":
        logger.info("MS Sync: Running in MOCK mode (MS_API_URL not configured)")
        
        synced_ids = []
        for i, case in enumerate(cases):
            mock_id = f"MS-TC-{10000 + i + 1}"
            synced_ids.append({
                "case_title": case.get("title", f"用例{i+1}"),
                "ms_id": mock_id,
                "status": "created"
            })
        
        return {
            "success": True,
            "mode": "mock",
            "total": len(cases),
            "synced": len(cases),
            "failed": 0,
            "synced_items": synced_ids,
            "message": f"✅ 模拟同步成功！共 {len(cases)} 条用例已同步（模拟模式）。配置 MS_API_URL 和 MS_API_KEY 后可接入真实平台。"
        }
    
    # === 真实 MS 平台对接模式 ===
    logger.info(f"MS Sync: Sending cases to {ms_api_url}")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ms_api_key}" if ms_api_key else ""
    }
    
    synced_items = []
    failed_items = []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for case in cases:
            payload = {
                "title": case.get("title", ""),
                "module": case.get("module", ""),
                "precondition": case.get("precondition", ""),
                "steps": case.get("steps", ""),
                "expected_result": case.get("expected_result", ""),
                "priority": case.get("priority", "中")
            }
            
            try:
                resp = await client.post(
                    f"{ms_api_url}/testcase/create",
                    json=payload,
                    headers=headers
                )
                resp.raise_for_status()
                result = resp.json()
                synced_items.append({
                    "case_title": case.get("title"),
                    "ms_id": result.get("id", "unknown"),
                    "status": "created"
                })
                logger.debug(f"MS Sync: Case '{case.get('title')}' synced successfully")
            except Exception as e:
                logger.error(f"MS Sync: Failed to sync case '{case.get('title')}': {e}")
                failed_items.append({
                    "case_title": case.get("title"),
                    "error": str(e)
                })
    
    total = len(cases)
    synced = len(synced_items)
    failed = len(failed_items)
    
    logger.success(f"MS Sync completed: {synced}/{total} cases synced, {failed} failed")
    
    return {
        "success": failed == 0,
        "mode": "real",
        "total": total,
        "synced": synced,
        "failed": failed,
        "synced_items": synced_items,
        "failed_items": failed_items,
        "message": f"同步完成：{synced}/{total} 条成功，{failed} 条失败"
    }
