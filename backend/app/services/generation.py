from typing import Optional, Dict, Any
from fastapi import UploadFile, HTTPException
from loguru import logger
from app.services.parser import parse_uploaded_file
from app.ai.ai import analyze_requirements, design_test_strategy, generate_test_cases
from app.services.exporter import convert_cases_to_mindmap, export_cases_to_excel

async def process_generation_request(source_type: str, doc_url: Optional[str], file: Optional[UploadFile]) -> Dict[str, Any]:
    logger.info(f"Processing generation request with source_type: {source_type}")
    
    # 1. Provide Context
    text_content = ""
    
    if source_type not in ["feishu", "dingtalk", "local"]:
        logger.error(f"Invalid source type received: {source_type}")
        raise HTTPException(status_code=400, detail="来源类型无效")
        
    if source_type in ["feishu", "dingtalk"]:
        if not doc_url:
            logger.error("Doc URL is missing for remote source type.")
            raise HTTPException(status_code=400, detail="此来源类型必须填写文档链接")
        logger.debug(f"Parsing document from URL: {doc_url}")
        text_content = f"Mock downloaded content from {doc_url}"
        
    if source_type == "local":
        if not file:
            logger.error("File is missing for local source type.")
            raise HTTPException(status_code=400, detail="本地上传必须提供文件")
        # Extract text from file
        text_content = await parse_uploaded_file(file)
        
    if not text_content:
        raise HTTPException(status_code=400, detail="无法从文档中提取到文本内容")
        
    # Phase 1: Requirement Analysis
    analysis = await analyze_requirements(text_content)
    
    # Phase 2: Test Design
    design = await design_test_strategy(analysis)
    
    # Phase 3: Write Test Cases
    cases = await generate_test_cases(design)
    
    # Phase 4: Generate Mindmap
    mindmap = convert_cases_to_mindmap(cases)
    
    logger.info("Generation pipeline completed successfully.")
    
    return {
        "analysis": analysis,
        "design": design,
        "cases": cases,
        "mindmap": mindmap
    }
