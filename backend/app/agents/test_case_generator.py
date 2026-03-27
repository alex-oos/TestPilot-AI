"""
测试用例生成智能体
负责基于需求分析结果生成详细的测试用例
"""

import json
import sys
import os
from typing import List, Dict, Any, AsyncGenerator

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import ModelClientStreamingChunkEvent

from utils.llms import model_client, deepseek_model_client, QWEN_MODEL_NAME, DEEPSEEK_MODEL_NAME
from utils.logger import logger


class TestCaseGenerator:
    """测试用例生成智能体 - 负责生成详细的测试用例"""

    def __init__(self):
        self.name = "TestCaseGenerator"

    def _get_model_client_for_file_type(self, file_path: str):
        """根据文件类型选择合适的模型客户端"""
        file_extension = file_path.lower().split('.')[-1] if '.' in file_path else ''

        # 图像文件使用支持视觉的模型
        if file_extension in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']:
            return model_client
        else:
            return deepseek_model_client

    async def generate_test_cases_stream(
        self,
        file_path: str,
        context: str,
        user_requirements: str,
        analysis_result: str
    ) -> AsyncGenerator[str, None]:
        """
        基于需求分析结果生成测试用例

        参数:
            file_path: 文件路径
            context: 用户上下文
            user_requirements: 用户需求
            analysis_result: 需求分析结果

        产出:
            测试用例（Markdown格式）
        """
        # 根据文件类型选择合适的模型客户端
        selected_model_client = self._get_model_client_for_file_type(file_path)
        file_extension = file_path.lower().split('.')[-1] if '.' in file_path else ''

        logger.info(f"测试用例生成 - 文件类型: {file_extension}, 模型: {DEEPSEEK_MODEL_NAME if selected_model_client == deepseek_model_client else QWEN_MODEL_NAME}")

        # 构建测试用例生成提示词
        prompt = f"""基于需求分析结果，直接生成详细的测试用例。

            ## 需求分析结果
            {analysis_result}
            
            ## 用户原始需求
            {user_requirements}
            
            ## 上下文信息
            {context}
            
            **重要格式要求**：
            请直接生成测试用例，不要添加任何概述、介绍或总结性内容。从第一个测试用例开始。
            
            每个测试用例必须严格按照以下格式：
            
            ## TC-001: 测试标题
            
            **优先级:** 高/中/低
            
            **描述:** 测试用例的详细描述
            
            **前置条件:** 执行测试前的条件（如果有）
            
            ### 测试步骤
            
            | # | 步骤描述 | 预期结果 |
            | --- | --- | --- |
            | 1 | 具体的操作步骤 | 期望看到的结果 |
            | 2 | 下一个操作步骤 | 对应的期望结果 |
            
            **关键要求**：
            1. 直接开始生成测试用例，不要添加文档概述或测试范围说明
            2. 每个测试用例必须以 ## TC-XXX: 标题 格式开始
            3. 必须包含 **优先级:**、**描述:**、**前置条件:** 等加粗字段
            4. 测试步骤必须使用标准的Markdown表格格式
            5. 表格必须有三列：#、步骤描述、预期结果
            6. 确保测试用例覆盖需求分析中的所有功能点
            7. 包含正向、负向和边界测试场景
            
            请直接生成测试用例，从TC-001开始。不要添加任何介绍性内容。"""

                    system_message = """你是一个专业的测试用例生成器，擅长基于需求分析生成全面的测试用例。
            
            **关键要求**：
            1. 直接开始生成测试用例，不要添加任何概述、介绍、文档说明或总结
            2. 第一个输出必须是测试用例，格式：## TC-001: 标题
            3. 每个测试用例必须以 ## TC-XXX: 标题 格式开始
            4. 必须包含 **优先级:**、**描述:**、**前置条件:** 等加粗字段
            5. 测试步骤必须使用标准的Markdown表格格式，包含表头和分隔行
            6. 表格必须有三列：#、步骤描述、预期结果
            7. 确保测试用例覆盖需求分析中的所有功能点
            8. 包含正向、负向和边界测试场景
            
            **禁止输出**：
            - 不要输出"基于以下需求..."等介绍性文字
            - 不要输出"测试用例集"等标题
            - 不要输出测试范围或覆盖说明
            - 直接从第一个测试用例 ## TC-001 开始
            
            请严格遵循格式要求，直接生成测试用例。"""

        # 创建AI代理
        agent = AssistantAgent(
            name="test_case_generator",
            model_client=selected_model_client,
            system_message=system_message,
            model_client_stream=True,
        )

        # 输出测试用例生成阶段标题
        yield "# 测试用例生成阶段\n\n"
        yield f"**文件类型**: {file_extension.upper()}\n"
        yield f"**使用模型**: {DEEPSEEK_MODEL_NAME if selected_model_client == deepseek_model_client else QWEN_MODEL_NAME}\n\n"
        yield "---\n\n"

        # 流式输出生成的测试用例
        test_cases_content = ""
        async for event in agent.run_stream(task=prompt):
            if isinstance(event, ModelClientStreamingChunkEvent):
                chunk = event.content
                test_cases_content += chunk
                yield chunk
            elif isinstance(event, TaskResult):
                break

        logger.info(f"测试用例生成完成，内容长度: {len(test_cases_content)}")


# 创建全局实例
test_case_generator = TestCaseGenerator()
