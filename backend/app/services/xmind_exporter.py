import io
import json
import zipfile
from typing import List
from loguru import logger


def generate_xmind_file(cases: List[dict], title: str = "AI自动生成测试用例") -> bytes:
    """
    生成合法的 .xmind 文件（ZIP格式）。
    .xmind 文件本质是一个 ZIP 压缩包，包含 content.json 等文件。
    """
    logger.info(f"XMind Exporter: Generating .xmind file for {len(cases)} cases")
    
    # 按模块分组
    modules: dict = {}
    for case in cases:
        mod = case.get("module", "通用模块")
        if mod not in modules:
            modules[mod] = []
        modules[mod].append(case)
    
    # 构建根节点子节点（模块层）
    module_children = []
    for mod_name, mod_cases in modules.items():
        case_children = []
        for case in mod_cases:
            priority = case.get("priority", "中")
            title_node = f"[{priority}] {case.get('title', '未命名用例')}"
            
            # 用例子节点：步骤 + 预期结果
            case_detail_children = []
            steps_text = case.get("steps", "")
            if steps_text:
                case_detail_children.append({
                    "id": f"steps_{case.get('id', 0)}",
                    "title": f"步骤: {steps_text[:80]}{'...' if len(steps_text) > 80 else ''}",
                    "children": {"attached": []}
                })
            
            expected = case.get("expected_result", "")
            if expected:
                case_detail_children.append({
                    "id": f"expected_{case.get('id', 0)}",
                    "title": f"预期: {expected[:80]}{'...' if len(expected) > 80 else ''}",
                    "children": {"attached": []}
                })
            
            case_children.append({
                "id": f"case_{case.get('id', 0)}",
                "title": title_node,
                "children": {"attached": case_detail_children}
            })
        
        module_children.append({
            "id": f"module_{mod_name[:20]}",
            "title": mod_name,
            "children": {"attached": case_children}
        })
    
    # XMind content.json 格式
    content_json = [
        {
            "id": "root_sheet",
            "title": "Sheet 1",
            "rootTopic": {
                "id": "root_topic",
                "title": title,
                "children": {
                    "attached": module_children
                }
            },
            "theme": {
                "id": "businessBlue",
                "name": "Business Blue"
            }
        }
    ]
    
    # 创建 ZIP 文件（.xmind 格式）
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 必须文件：content.json
        zf.writestr("content.json", json.dumps(content_json, ensure_ascii=False, indent=2))
        
        # metadata.json（可选但推荐）
        metadata = {
            "creator": {
                "name": "AI Test Platform",
                "version": "1.0.0"
            }
        }
        zf.writestr("metadata.json", json.dumps(metadata, ensure_ascii=False))
        
        # manifest.json（部分XMind版本需要）
        manifest = {
            "file-entries": {
                "content.json": {},
                "metadata.json": {}
            }
        }
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
    
    logger.success(f"XMind file generated successfully ({len(zip_buffer.getvalue())} bytes)")
    return zip_buffer.getvalue()
