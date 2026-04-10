import time
import asyncio
from typing import Optional, Dict, Any
from fastapi import UploadFile, HTTPException
from loguru import logger
from app.services.parser import parse_uploaded_file
from app.ai.ai import analyze_requirements, design_test_strategy, generate_test_cases, review_test_cases
from app.modules.dingtalk import read_dingtalk_doc
from app.modules.feishu import read_feishu_doc
from app.rag.knowledge_base import (
    build_generation_history_context,
    find_similar_requirement_history,
    ingest_requirement_document,
)
from app.services.exporter import convert_cases_to_mindmap, export_cases_to_excel


async def process_generation_request(source_type: str, doc_url: Optional[str], file: Optional[UploadFile]) -> Dict[str, Any]:
    logger.info(f"Processing generation request with source_type: {source_type}")
    
    # 1. 文档解析 - 提取需求文本
    text_content = ""
    
    if source_type not in ["feishu", "dingtalk", "local", "manual"]:
        logger.error(f"Invalid source type received: {source_type}")
        raise HTTPException(status_code=400, detail="来源类型无效")
        
    if source_type in ["feishu", "dingtalk"]:
        if not doc_url:
            logger.error("Doc URL is missing for remote source type.")
            raise HTTPException(status_code=400, detail="此来源类型必须填写文档链接")
        logger.debug(f"Parsing document from URL: {doc_url}")
        if source_type == "feishu":
            text_content = await read_feishu_doc(doc_url)
        else:
            text_content = await read_dingtalk_doc(doc_url)
        
    if source_type == "local":
        if not file:
            logger.error("File is missing for local source type.")
            raise HTTPException(status_code=400, detail="本地上传必须提供文件")
        # 从文件中提取文本
        text_content = await parse_uploaded_file(file)
    if source_type == "manual":
        if not doc_url:
            raise HTTPException(status_code=400, detail="手动输入模式必须提供需求内容")
        text_content = doc_url
        
    if not text_content:
        raise HTTPException(status_code=400, detail="无法从文档中提取到文本内容")

    transient_task_id = f"legacy-{source_type}-{int(time.time() * 1000)}"
    await asyncio.to_thread(
        ingest_requirement_document,
        task_id=transient_task_id,
        text=text_content,
        source_type=source_type,
        file_name=file.filename if file else "manual_input.txt",
        submitter="legacy",
    )
    similar_history = await asyncio.to_thread(
        find_similar_requirement_history,
        query_text=text_content,
        current_task_id=transient_task_id,
        top_k=5,
    )
    history_context = build_generation_history_context(similar_history) if similar_history else ""
    
    logger.info("Pipeline Phase 1: AI requirement analysis...")
    # Phase 1: 需求分析
    analysis = await analyze_requirements(text_content)
    
    logger.info("Pipeline Phase 2: AI test strategy design...")
    # Phase 2: 测试策略设计
    design = await design_test_strategy(analysis)
    
    logger.info("Pipeline Phase 3: AI test case generation...")
    # Phase 3: 生成测试用例
    cases = await generate_test_cases(design, history_context)
    
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
