"""
LLM 调用封装：通过 langchain-openai 连接阿里云百炼 DeepSeek-V4-Pro，提供纯文本和 JSON 两种调用方式。
调用关系：调用 config.py 读取配置；被 6 个节点文件（fact_extraction, anomaly_detection, consistency_judge, followup_generation, report_generation）引用。
输入：config.py (API_KEY, BASE_URL, MODEL_NAME)
输出：call_llm(), call_llm_json()
"""
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from config import API_KEY, BASE_URL, MODEL_NAME


def get_chat_model(temperature: float = 0.3) -> ChatOpenAI:
    """返回一个 ChatOpenAI 实例，连接阿里云百炼 DeepSeek-V4-Pro"""
    return ChatOpenAI(
        model=MODEL_NAME,
        api_key=API_KEY,  # type: ignore[arg-type]
        base_url=BASE_URL,
        temperature=temperature,
    )


def _extract_content(response: HumanMessage) -> str:
    """从响应中提取文本内容"""
    content = response.content
    if isinstance(content, str):
        return content
    # content 为 list 时，拼接文本部分
    parts = []
    for item in content:  # type: ignore[union-attr]
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict) and "text" in item:
            parts.append(item["text"])
    return "".join(parts)


def call_llm(prompt: str, temperature: float = 0.3) -> str:
    """调用大模型，返回纯文本响应"""
    model = get_chat_model(temperature)
    response = model.invoke([HumanMessage(content=prompt)])
    return _extract_content(response)  # type: ignore[arg-type]


def call_llm_json(prompt: str, temperature: float = 0.1) -> str:
    """
    调用大模型，要求返回 JSON 格式响应。
    temperature 默认更低以保证输出稳定。
    """
    model = get_chat_model(temperature)
    model = model.bind(response_format={"type": "json_object"})
    response = model.invoke([HumanMessage(content=prompt)])
    return _extract_content(response)  # type: ignore[arg-type]
