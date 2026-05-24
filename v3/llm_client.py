"""LLM 客户端模块：提供统一的 ChatOpenAI 实例"""

from pydantic import SecretStr
from langchain_openai import ChatOpenAI
from . import config


def get_llm(temperature: float | None = None, model: str | None = None) -> ChatOpenAI:
    """获取 LLM 实例

    每次调用都确保代理已禁用，防止系统代理干扰 API 连接。

    Args:
        temperature: 可选覆盖温度
        model: 可选覆盖模型名
    Returns:
        ChatOpenAI 实例
    """
    # 确保代理已禁用（config.disable_proxy 会设置 NO_PROXY='*'）
    config.disable_proxy()

    return ChatOpenAI(
        api_key=SecretStr(config.DEEPSEEK_API_KEY),
        base_url=config.BAILIAN_BASE_URL,
        model=model or config.MODEL_NAME,
        temperature=temperature if temperature is not None else config.TEMPERATURE,
        max_retries=2,
    )
