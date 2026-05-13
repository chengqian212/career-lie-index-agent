"""文本工具模块：处理文本的通用辅助函数"""

import re
from typing import List


def truncate_text(text: str, max_length: int = 2000) -> str:
    """截断过长文本，保留尾部

    Args:
        text: 原始文本
        max_length: 最大长度
    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + "...(已截断)"


def format_dialogue_history(history: List[dict], max_rounds: int | None = None) -> str:
    """格式化对话历史为可读文本

    Args:
        history: 对话历史列表，每项包含 role 和 content
        max_rounds: 最多格式化几轮，None 表示全部
    Returns:
        格式化后的文本
    """
    if not history:
        return "（暂无对话历史）"

    entries = history if max_rounds is None else history[-max_rounds:]
    lines = []
    for entry in entries:
        role = entry.get("role", "unknown")
        content = entry.get("content", "")
        if role == "user":
            lines.append(f"【用户】：{content}")
        elif role == "assistant":
            lines.append(f"【系统】：{content}")
        else:
            lines.append(f"【{role}】：{content}")
    return "\n".join(lines)


def format_facts_table(facts_table: List[dict]) -> str:
    """格式化事实表为可读文本

    Args:
        facts_table: 事实表
    Returns:
        格式化后的文本
    """
    if not facts_table:
        return "（暂无事实记录）"

    lines = []
    for i, fact in enumerate(facts_table, 1):
        round_id = fact.get("round_id", "?")
        content = fact.get("content", "")
        category = fact.get("category", "")
        lines.append(f"  [{i}] 第{round_id}轮 | {category} | {content}")
    return "\n".join(lines)


def format_anomalies_table(anomalies_table: List[dict]) -> str:
    """格式化异常表为可读文本

    Args:
        anomalies_table: 异常表
    Returns:
        格式化后的文本
    """
    if not anomalies_table:
        return "（暂无异常记录）"

    lines = []
    for i, anomaly in enumerate(anomalies_table, 1):
        round_id = anomaly.get("round_id", "?")
        atype = anomaly.get("type", "")
        desc = anomaly.get("description", "")
        status = anomaly.get("status", "unresolved")
        lines.append(f"  [{i}] 第{round_id}轮 | {atype} | {desc} | 状态: {status}")
    return "\n".join(lines)


def extract_content_str(content: str | list[str | dict] | None) -> str:
    """将 LLM response.content 统一转为 str

    新版 langchain-core 中 response.content 类型为 str | list[str | dict]，
    此函数将其统一提取为纯文本字符串。

    Args:
        content: LLM 返回的 content
    Returns:
        纯文本字符串
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                # 常见格式: {"type": "text", "text": "..."}
                parts.append(item.get("text", str(item)))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(content)


def clean_llm_output(text: str | list[str | dict] | None) -> str:
    """清理 LLM 输出中的常见噪音

    Args:
        text: 原始 LLM 输出（兼容 str 或 list 类型）
    Returns:
        清理后的文本
    """
    # 先统一转为 str
    text = extract_content_str(text)
    # 去除首尾空白
    text = text.strip()
    # 去除 <think/> 标签内容（部分模型输出思考过程）
    text = re.sub(r"<think.*?>.*?</think\s*>", "", text, flags=re.DOTALL)
    return text.strip()
