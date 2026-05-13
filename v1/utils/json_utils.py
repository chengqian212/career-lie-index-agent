"""
JSON 解析工具：从 LLM 响应中提取 JSON，兼容直接 JSON、代码块包裹、裸花括号三种情况。
调用关系：被 4 个 LLM 节点（fact_extraction, anomaly_detection, consistency_judge, report_generation）引用。
输入：LLM 返回的原始文本
输出：parse_json_response() 函数 → 返回 dict
"""
import json
import re


def parse_json_response(text: str) -> dict:
    """
    从 LLM 响应中解析 JSON。
    尝试直接解析，失败则提取 ```json ... ``` 代码块再解析。
    """
    text = text.strip()

    # 直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 提取 ```json ... ``` 代码块
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 提取第一个 { 到最后一个 }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    return {}
