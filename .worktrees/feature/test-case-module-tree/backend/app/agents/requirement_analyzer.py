import json
from typing import Dict, Any, AsyncGenerator, List
import sys
import os

# 添加父目录到路径，以便正确导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import ModelClientStreamingChunkEvent, MultiModalMessage as AGMultiModalMessage
from autogen_core import Image as AGImage
from PIL import Image as PILImage

from utils.llms import model_client, deepseek_model_client, QWEN_MODEL_NAME, DEEPSEEK_MODEL_NAME
from utils.logger import logger
from services.pdf_service import pdf_service
from services.openapi_service import openapi_service


class RequirementAnalyzer:
    """需求分析智能体 - 负责分析上传文件并提取结构化需求"""

    def __init__(self):
        self.name = "RequirementAnalyzer"

    def _get_model_client_for_file_type(self, file_path: str):
        """根据文件类型选择合适的模型客户端"""
        file_extension = file_path.lower().split('.')[-1] if '.' in file_path else ''

        # 图像文件使用支持视觉的模型客户端
        if file_extension in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']:
            return model_client  # 支持视觉的模型
        else:
            return deepseek_model_client

    async def analyze_requirements_stream(
            self,
            file_path: str,
            context: str,
            user_requirements: str
    ) -> AsyncGenerator[str, None]:
        """
        分析文件并提取需求（流式输出）

        参数:
            file_path: 文件路径
            context: 用户提供的上下文
            user_requirements: 用户提供的需求

        产出:
            需求分析结果（Markdown格式）
        """
        logger.info(f"开始需求分析 - 文件: {file_path}")

        # 根据文件类型选择合适的模型客户端
        selected_model_client = self._get_model_client_for_file_type(file_path)
        file_extension = file_path.lower().split('.')[-1] if '.' in file_path else ''

        logger.info(
            f"文件类型: {file_extension}, 使用模型: {DEEPSEEK_MODEL_NAME if selected_model_client == deepseek_model_client else QWEN_MODEL_NAME}")

        # 根据文件类型准备分析内容
        if file_extension in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']:
            # 处理图像文件
            pil_image = PILImage.open(file_path)
            img = AGImage(pil_image)

            # 构建需求分析提示词
            prompt = f"""请深入分析上传的图像，提取关键需求和功能点。

                上下文信息: {context}
                
                用户需求: {user_requirements}
                
                **分析要求**：
                请按照以下结构进行分析，提取结构化的需求信息：
                
                ## 1. 功能概述
                - 简要描述图像展示的主要功能或场景
                - 识别核心业务流程
                
                ## 2. 功能需求
                - 列出具体的功能点（编号列表）
                - 每个功能点包含：功能名称、描述、触发条件
                
                ## 3. 用户交互需求
                - 用户界面元素（按钮、输入框、选项等）
                - 用户操作流程
                - 交互反馈机制
                
                ## 4. 非功能性需求
                - 性能要求（如有）
                - 安全性要求（如有）
                - 兼容性要求（如有）
                
                ## 5. 数据需求
                - 输入数据要求
                - 输出数据要求
                - 数据验证规则
                
                ## 6. 异常场景
                - 可能的错误场景
                - 异常处理方式
                
                ## 7. 测试重点建议
                - 建议重点测试的功能
                - 需要特别关注的场景
                
                请详细分析图像内容，提取所有可见和隐含的需求信息。"""

            # 创建多模态消息
            multi_modal_message = AGMultiModalMessage(content=[prompt, img], source="user")
            system_message = """你是一个专业的需求分析师，擅长从图像中提取结构化的需求信息。
                
                **关键要求**：
                1. 仔细观察图像中的所有细节
                2. 识别UI元素、文本内容和交互逻辑
                3. 提取明确和隐含的需求
                4. 按照指定格式组织分析结果
                5. 提供具体的测试建议
                
                请确保分析全面、准确、结构清晰。"""
            task_message = multi_modal_message

        elif file_extension == 'pdf':
            # 处理PDF文件
            try:
                logger.info(f"处理PDF文件: {file_path}")
                pdf_content = pdf_service.extract_text_from_pdf(file_path)

                prompt = f"""请深入分析PDF文档内容，提取关键需求和功能点。

                    文档信息:
                    - 标题: {pdf_content['metadata'].get('title', '未知')}
                    - 页数: {pdf_content['metadata'].get('pages', '未知')}
                    
                    文档内容:
                    {pdf_content['text'][:10000]}{'...(内容过长，已截断)' if len(pdf_content['text']) > 10000 else ''}
                    
                    上下文信息: {context}
                    
                    用户需求: {user_requirements}
                    
                    **分析要求**：
                    请按照以下结构进行分析，提取结构化的需求信息：
                    
                    ## 1. 文档概述
                    - 文档目的和范围
                    - 目标用户群体
                    
                    ## 2. 功能需求
                    - 核心功能列表（编号）
                    - 每个功能的详细描述
                    - 功能优先级
                    
                    ## 3. 业务规则
                    - 业务逻辑和规则
                    - 数据验证规则
                    - 约束条件
                    
                    ## 4. 数据需求
                    - 数据结构要求
                    - 数据关系
                    - 数据存储要求
                    
                    ## 5. 非功能性需求
                    - 性能需求
                    - 安全性需求
                    - 可用性需求
                    
                    ## 6. 接口需求
                    - 外部接口依赖
                    - API要求
                    - 集成需求
                    
                    ## 7. 测试重点建议
                    - 关键测试场景
                    - 风险点识别
                    - 测试优先级建议
                    
                    请基于文档内容进行深入分析，提取所有相关需求信息。"""

                task_message = prompt
                system_message = """你是一个专业的需求分析师，擅长从文档中提取结构化的需求信息。

                请仔细分析文档内容，按照指定格式组织需求信息，确保分析全面、准确。"""

            except Exception as e:
                logger.error(f"PDF处理失败: {str(e)}", exc_info=True)
                yield f"\n\n**错误**: PDF处理失败 - {str(e)}\n"
                return

        elif file_extension in ['json', 'yaml', 'yml']:
            # 处理OpenAPI文件
            try:
                logger.info(f"处理OpenAPI文件: {file_path}")
                api_data = openapi_service.parse_openapi_file(file_path)
                api_info = api_data['api_info']

                prompt = f"""请分析OpenAPI/Swagger文档，提取API测试需求。

                    API文档信息:
                    - 标题: {api_info['info'].get('title', '未知')}
                    - 版本: {api_info['info'].get('version', '未知')}
                    - 描述: {api_info['info'].get('description', '无描述')}
                    - API路径数量: {len(api_info['paths'])}
                    
                    API端点概览:
                    {self._format_api_endpoints_for_analysis(api_info)}
                    
                    上下文信息: {context}
                    
                    用户需求: {user_requirements}
                    
                    **分析要求**：
                    请按照以下结构进行分析：
                    
                    ## 1. API概述
                    - API的整体功能和用途
                    - 主要业务场景
                    
                    ## 2. API端点分析
                    针对每个主要端点，分析：
                    - 功能描述
                    - 请求参数要求
                    - 响应数据结构
                    - 认证授权要求
                    
                    ## 3. 测试需求分析
                    - 正向测试场景（正常流程）
                    - 负向测试场景（错误处理）
                    - 边界值测试场景
                    - 安全性测试需求
                    
                    ## 4. 数据验证需求
                    - 参数验证规则
                    - 数据格式要求
                    - 必填字段识别
                    
                    ## 5. 性能测试需求
                    - 响应时间要求
                    - 并发处理要求
                    
                    ## 6. 测试重点建议
                    - 关键API端点
                    - 复杂业务逻辑
                    - 高风险场景
                    
                    请基于OpenAPI文档进行详细分析。"""

                task_message = prompt
                system_message = """你是一个专业的API测试需求分析师，擅长从OpenAPI文档中提取测试需求。
    
                请仔细分析API定义，提取所有测试相关的需求信息。"""

            except Exception as e:
                logger.error(f"OpenAPI文档处理失败: {str(e)}", exc_info=True)
                yield f"\n\n**错误**: OpenAPI文档处理失败 - {str(e)}\n"
                return

        else:
            # 处理其他文本文件
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
            except UnicodeDecodeError:
                try:
                    with open(file_path, 'r', encoding='gbk') as f:
                        file_content = f.read()
                except Exception as e:
                    logger.error(f"无法读取文件: {str(e)}")
                    yield f"\n\n**错误**: 无法读取文件内容，不支持的编码格式\n"
                    return

            prompt = f"""请分析文档内容，提取需求信息。

                    文档内容:
                    {file_content[:8000]}{'...(内容过长，已截断)' if len(file_content) > 8000 else ''}
                    
                    上下文信息: {context}
                    
                    用户需求: {user_requirements}
                    
                    **分析要求**：
                    请提取并组织以下需求信息：
                    
                    ## 1. 功能概述
                    ## 2. 功能需求列表
                    ## 3. 业务规则
                    ## 4. 数据需求
                    ## 5. 测试重点建议
                    
                    请详细分析文档内容。"""

            task_message = prompt
            system_message = "你是一个专业的需求分析师，擅长从文档中提取结构化的需求信息。"

        # 创建需求分析智能体
        agent = AssistantAgent(
            name="requirement_analyzer",
            model_client=selected_model_client,
            system_message=system_message,
            model_client_stream=True,
        )

        # 输出分析阶段标题
        yield "# 需求分析阶段\n\n"
        yield f"**分析文件**: {file_path}\n"
        yield f"**文件类型**: {file_extension.upper()}\n"
        yield f"**使用模型**: {DEEPSEEK_MODEL_NAME if selected_model_client == deepseek_model_client else QWEN_MODEL_NAME}\n\n"
        yield "---\n\n"

        # 流式输出分析结果
        full_analysis = ""
        async for event in agent.run_stream(task=task_message):
            if isinstance(event, ModelClientStreamingChunkEvent):
                chunk = event.content
                full_analysis += chunk
                yield chunk
            elif isinstance(event, TaskResult):
                break

        logger.info(f"需求分析完成，分析结果长度: {len(full_analysis)}")
        yield "\n\n---\n\n"
        yield "**需求分析完成，正在启动测试用例生成...**\n\n"

    def _format_api_endpoints_for_analysis(self, api_info: Dict[str, Any]) -> str:
        """格式化API端点信息用于分析"""
        formatted = ""

        for path_info in api_info['paths'][:15]:  # 显示更多端点
            formatted += f"### {path_info['path']}\n"
            for op in path_info['operations']:
                formatted += f"- **{op['method']}**: {op['summary'] or op['description']}\n"
                if op['parameters']:
                    formatted += f"  - 参数: {len(op['parameters'])} 个\n"
                if op['responses']:
                    formatted += f"  - 响应状态码: {', '.join(op['responses'].keys())}\n"
            formatted += "\n"

        return formatted


# 创建全局实例
requirement_analyzer = RequirementAnalyzer()
