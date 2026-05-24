"""JSON 工具模块：处理 LLM 输出中的 JSON 解析"""

import json
import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


def extract_json_from_text(text: str) -> Optional[Any]:
    """从 LLM 输出文本中提取 JSON

    支持以下格式：
    1. 纯 JSON 字符串
    2. ```json ... ``` 代码块包裹
    3. 混合文字中嵌入 JSON

    Args:
        text: LLM 输出文本
    Returns:
        解析后的 Python 对象，解析失败返回 None
    """
    if not text or not text.strip():
        return None

    # 尝试 1：直接解析整个文本
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # 尝试 2：提取 ```json ... ``` 代码块
    pattern = r"```json\s*(.*?)\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 尝试 3：提取 { ... } 或 [ ... ] 结构
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start_idx = text.find(start_char)
        if start_idx != -1:
            # 从后往前找匹配的结束符
            end_idx = text.rfind(end_char)
            if end_idx > start_idx:
                try:
                    return json.loads(text[start_idx : end_idx + 1])
                except json.JSONDecodeError:
                    pass

    return None


def safe_json_parse_with_retry(text: str, default: Any = None, node_name: str = "未知节点") -> Any:
    """安全的 JSON 解析，支持两次解析和日志记录

    第一次解析失败后，会尝试使用更激进的清理策略重新解析。
    两次均失败时返回默认值并记录日志。

    Args:
        text: LLM 输出文本
        default: 解析失败时的默认返回值
        node_name: 节点名称（用于日志）

    Returns:
        解析后的 Python 对象或 default
    """
    from .text_utils import clean_llm_output
    
    # 第一次解析尝试
    result = extract_json_from_text(text)
    
    if result is not None:
        logger.info(f"[{node_name}] JSON 解析成功")
        return result
    
    # 第一次解析失败
    logger.warning(
        f"[{node_name}] 第一次 JSON 解析失败，尝试重新解析。"
        f"原始输出长度: {len(text)} 字符，"
        f"原始输出预览: {text[:200]}..."
    )
    
    # 重新清理并解析（使用更激进的清理策略）
    cleaned_again = clean_llm_output(text, aggressive=True)
    result = extract_json_from_text(cleaned_again)
    
    if result is not None:
        logger.info(f"[{node_name}] 第二次解析成功")
        return result
    
    # 两次都失败
    logger.error(
        f"[{node_name}] JSON 解析彻底失败。"
        f"已尝试两次解析，均无法提取有效 JSON。"
        f"原始输出: {text}"
    )
    
    return default


def safe_json_parse(text: str, default: Any = None) -> Any:
    """安全的 JSON 解析，失败时返回默认值

    Args:
        text: LLM 输出文本
        default: 解析失败时的默认返回值
    Returns:
        解析后的 Python 对象或 default
    """
    result = extract_json_from_text(text)
    return result if result is not None else default