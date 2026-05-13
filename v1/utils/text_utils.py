"""
文本处理工具：提供文本截断等辅助函数。
调用关系：当前未被其他文件直接调用，预留供后续使用。
输入：字符串
输出：truncate_text() 函数
"""


def truncate_text(text: str, max_length: int = 500) -> str:
    """截断过长文本"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."
