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
    Raises:
        ValueError: 当缺少 API 密钥时
    """
    # 确保代理已禁用（config.disable_proxy 会设置 NO_PROXY='*'）
    config.disable_proxy()

    api_key = config.BAILIAN_API_KEY

    # 调试打印：运行时传入 ChatOpenAI 的 key、base_url、model
    print(f"[LLM Client] BAILIAN_API_KEY 存在: {bool(api_key)}, 长度: {len(api_key)}")
    if api_key:
        print(f"[LLM Client] KEY 前12位: {api_key[:12]}...")
    print(f"[LLM Client] BASE_URL: {config.BAILIAN_BASE_URL}")
    print(f"[LLM Client] MODEL: {model or config.MODEL_NAME}")

    if not api_key:
        raise ValueError(
            "缺少 API 密钥！请在 .env 文件中设置 BAILIAN_API_KEY 环境变量。"
        )

    return ChatOpenAI(
        api_key=SecretStr(api_key),
        base_url=config.BAILIAN_BASE_URL,
        model=model or config.MODEL_NAME,
        temperature=temperature if temperature is not None else config.TEMPERATURE,
        max_retries=2,
    )
