import pandas as pd
import io
from loguru import logger
from typing import List, Dict

def export_cases_to_excel(cases: List[dict]) -> bytes:
    """Convert list of cases to Excel bytes."""
    logger.info(f"Exporting {len(cases)} cases to Excel format")
    df = pd.DataFrame(cases)
    
    # Rename columns to Chinese
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
    """
    Phase 4: 将 excel 表格用例转化成 mind 格式
    Here we generate a Markdown-based Mindmap (which can be rendered by markmap, mermaid, or saved as .md).
    """
    logger.info(f"Converting {len(cases)} cases to Mind Map format")
    
    # Group by module
    modules = {}
    for case in cases:
        mod = case.get("module", "基础模块")
        if mod not in modules:
            modules[mod] = []
        modules[mod].append(case)
        
    # Generate Markmap Markdown
    # Root
    md_lines = ["# AI 自动生成测试用例"]
    
    for mod, mod_cases in modules.items():
        md_lines.append(f"## {mod}")
        for c in mod_cases:
            priority_tag = f"[{c.get('priority', '中')}]"
            md_lines.append(f"### {priority_tag} {c.get('title')}")
            # we could add steps and expected results, but mindmaps shouldn't be too dense
            # md_lines.append(f"#### 步骤: {c.get('steps').replace(chr(10), ' ')}")
            # md_lines.append(f"#### 预期: {c.get('expected_result')}")
            
    markdown_mindmap = "\n".join(md_lines)
    logger.success("Mind Map conversion completed.")
    return markdown_mindmap
