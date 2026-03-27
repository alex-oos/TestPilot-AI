"""
测试用例评审智能体
负责评审测试用例的质量，检查完整性、一致性、可执行性，并输出改进后的测试用例
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

from utils.llms import deepseek_model_client, DEEPSEEK_MODEL_NAME
from utils.logger import logger


class TestCaseReviewer:
    """测试用例评审智能体 - 负责评审和改进测试用例"""

    def __init__(self):
        self.name = "TestCaseReviewer"

    async def review_test_cases_stream(
        self,
        test_cases_content: str,
        analysis_result: str,
        user_requirements: str
    ) -> AsyncGenerator[str, None]:
        """
        评审测试用例并输出改进后的版本

        参数:
            test_cases_content: 生成的测试用例内容（Markdown格式）
            analysis_result: 需求分析结果
            user_requirements: 用户原始需求

        产出:
            评审报告和改进后的测试用例（Markdown格式）
        """
        logger.info("开始测试用例评审")

        # 构建评审提示词
        prompt = f"""作为专业的测试用例评审专家，请对测试用例进行全面评审并输出改进后的版本。

            ## 需求分析结果
            {analysis_result}
            
            ## 用户原始需求
            {user_requirements}
            
            ## 原始测试用例
            {test_cases_content}
            
            **输出要求**：
            
            请按照以下两部分输出：
            
            ### 第一部分：评审报告
            输出完整的评审分析，包含：
            
            **优点**：
            - 列出测试用例的优点（格式规范、覆盖全面等）
            
            **问题识别**：
            - 完整性问题：是否覆盖所有功能点？
            - 一致性问题：格式是否统一？命名是否一致？
            - 可执行性：步骤是否清晰？预期结果是否明确？
            - 遗漏场景：是否缺少重要的测试场景？
            - 优先级合理性：优先级分配是否合理？
            
            **覆盖度分析**：
            - 功能覆盖度评分（0-100%）
            - 场景覆盖度评分（0-100%）
            - 边界值覆盖度评分（0-100%）
            
            **改进建议**：
            - 具体的改进建议
            
            ### 第二部分：最终测试用例
            使用以下标记开始：
            **===最终测试用例===**
            
            然后直接输出改进后的完整测试用例：
            
            ## TC-001: 测试标题
            
            **优先级:** 高/中/低
            
            **描述:** 测试用例的详细描述
            
            **前置条件:** 执行测试前的条件（如果有）
            
            ### 测试步骤
            
            | # | 步骤描述 | 预期结果 |
            | --- | --- | --- |
            | 1 | 具体的操作步骤 | 期望看到的结果 |
            
            ---
            
            **关键要求**：
            1. 评审报告要全面、具体
            2. 使用 **===最终测试用例===** 标记分隔两部分
            3. 最终测试用例要包含所有改进后的用例
            4. 确保覆盖所有功能点和场景
            5. 格式规范统一"""

        system_message = """你是一个经验丰富的测试用例评审专家，拥有10年以上的软件测试经验。

            **你的专长**：
            - 测试用例质量评审
            - 测试覆盖度分析
            - 测试场景设计
            - 最佳实践指导
            
            **评审原则**：
            1. 严格但建设性：指出问题的同时提供改进建议
            2. 全面性：检查完整性、一致性、可执行性
            3. 实用性：改进建议要具体可行
            4. 专业性：遵循测试最佳实践
            
            **输出要求**：
            1. 评审报告要客观全面、具体明确
            2. 使用 **===最终测试用例===** 标记分隔评审报告和最终用例
            3. 最终测试用例要完整、格式规范
            
            请以专业的态度进行评审，帮助提升测试用例质量。"""

        # 创建AI代理
        agent = AssistantAgent(
            name="test_case_reviewer",
            model_client=deepseek_model_client,  # 使用文本模型
            system_message=system_message,
            model_client_stream=True,
        )

        # 输出评审阶段标题
        yield "# 测试用例评审阶段\n\n"
        yield f"**使用模型**: {DEEPSEEK_MODEL_NAME}\n"
        yield "**评审内容**: 完整性、一致性、可执行性、覆盖度\n\n"
        yield "---\n\n"

        # 流式输出评审结果
        review_content = ""
        async for event in agent.run_stream(task=prompt):
            if isinstance(event, ModelClientStreamingChunkEvent):
                chunk = event.content
                review_content += chunk
                yield chunk
            elif isinstance(event, TaskResult):
                break

        logger.info(f"测试用例评审完成，内容长度: {len(review_content)}")


# 创建全局实例
test_case_reviewer = TestCaseReviewer()
