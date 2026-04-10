from app.ai.llm import llm_client


async def extract_text_from_image_bytes(*, image_bytes: bytes, file_name: str) -> str:
    result = await llm_client.extract_text_from_image(
        image_bytes=image_bytes,
        file_name=file_name,
        prompt="请识别并输出图片中的全部文本内容，保持条目和段落结构。",
    )
    return str(result or "").strip()
