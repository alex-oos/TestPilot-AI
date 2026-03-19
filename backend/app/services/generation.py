from typing import Optional, Dict, Any
from fastapi import UploadFile, HTTPException
from loguru import logger
from app.services.parser import parse_uploaded_file
from app.ai.ai import analyze_requirements, design_test_strategy, generate_test_cases, review_test_cases
from app.services.exporter import convert_cases_to_mindmap, export_cases_to_excel


async def process_generation_request(source_type: str, doc_url: Optional[str], file: Optional[UploadFile]) -> Dict[str, Any]:
    logger.info(f"Processing generation request with source_type: {source_type}")
    
    # 1. 文档解析 - 提取需求文本
    text_content = ""
    
    if source_type not in ["feishu", "dingtalk", "local"]:
        logger.error(f"Invalid source type received: {source_type}")
        raise HTTPException(status_code=400, detail="来源类型无效")
        
    if source_type in ["feishu", "dingtalk"]:
        if not doc_url:
            logger.error("Doc URL is missing for remote source type.")
            raise HTTPException(status_code=400, detail="此来源类型必须填写文档链接")
        logger.debug(f"Parsing document from URL: {doc_url}")
        text_content = f"[在线文档内容] 来源: {doc_url}\n注意：飞书/钉钉文档需要配置相应Token才能真实获取内容。当前为演示模式，请使用本地上传功能体验完整AI生成流程。"
        
    if source_type == "local":
        if not file:
            logger.error("File is missing for local source type.")
            raise HTTPException(status_code=400, detail="本地上传必须提供文件")
        # 从文件中提取文本
        text_content = await parse_uploaded_file(file)
        
    if not text_content:
        raise HTTPException(status_code=400, detail="无法从文档中提取到文本内容")
    
    logger.info("Pipeline Phase 1: AI requirement analysis...")
    # Phase 1: 需求分析
    analysis = await analyze_requirements(text_content)
    
    logger.info("Pipeline Phase 2: AI test strategy design...")
    # Phase 2: 测试策略设计
    design = await design_test_strategy(analysis)
    
    logger.info("Pipeline Phase 3: AI test case generation...")
    # Phase 3: 生成测试用例
    cases = await generate_test_cases(design)
    
    logger.info("Pipeline Phase 4: AI test case review...")
    # Phase 4: AI评审优化（新增）
    review = await review_test_cases(cases, analysis)
    
    # Phase 5: 生成思维导图
    mindmap = convert_cases_to_mindmap(cases)
    
    logger.info("Generation pipeline completed successfully.")
    
    return {
        "analysis": analysis,
        "design": design,
        "cases": cases,
        "review": review,
        "mindmap": mindmap
    }
