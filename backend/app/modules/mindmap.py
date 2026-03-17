import pandas as pd
import io
from loguru import logger
from typing import List, Dict

def export_cases_to_excel(cases: List[dict]) -> bytes:
    """导出用例到 Excel"""
    logger.info(f"Mindmap/Export Module: Exporting {len(cases)} cases to Excel format")
    df = pd.DataFrame(cases)
    
    df.rename(columns={
        "id": "编号",
        "module": "模块",
        "title": "标题",
        "precondition": "前置条件",
        "steps": "操作步骤",
        "expected_result": "预期结果",
        "priority": "优先级"
    }, inplace=True)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='测试用例')
    return output.getvalue()


def convert_cases_to_mindmap(cases: List[dict]) -> str:
    """脑图模块 - 获取 Markdown 脑图语法"""
    logger.info(f"Mindmap Module: Converting {len(cases)} cases to Mind Map form")
    
    modules = {}
    for case in cases:
        mod = case.get("module", "基础模块")
        if mod not in modules:
            modules[mod] = []
        modules[mod].append(case)
        
    md_lines = ["# AI 自动生成测试用例"]
    for mod, mod_cases in modules.items():
        md_lines.append(f"## {mod}")
        for c in mod_cases:
            priority_tag = f"[{c.get('priority', '中')}]"
            md_lines.append(f"### {priority_tag} {c.get('title')}")
            
    return "\n".join(md_lines)
