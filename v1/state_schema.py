"""
全局状态定义：定义 DialogueState TypedDict，标注各字段的 reducer（Overwrite 覆盖 / Append 追加）。
调用关系：被 graph.py 和所有 6 个节点文件引用。
输入：无
输出：DialogueState 类型
"""
from typing import TypedDict, List, Dict, Any, Optional, Annotated
import operator


def _overwrite(old, new):
    """标量字段：直接覆盖"""
    return new


# 标量字段 reducer：直接覆盖
Overwrite = Annotated[Any, _overwrite]

# 列表字段 reducer：追加
Append = Annotated[list, operator.add]


class DialogueState(TypedDict):
    """多轮对话全局状态"""
    # 轮次控制
    round_id: Overwrite
    max_rounds: Overwrite

    # 当前用户输入
    current_user_text: Overwrite

    # 对话历史：每项为 {"role": "user"/"assistant", "content": "..."}
    dialogue_history: Append

    # 当前轮抽取的事实
    current_facts: Overwrite

    # 历史事实表
    facts_table: Overwrite

    # 当前轮识别的异常表达
    current_anomalies: Overwrite

    # 异常表达历史记录
    indicator_history: Append

    # 事实一致性判断结果
    consistency_results: Overwrite

    # 异常表
    anomalies_table: Overwrite

    # 上一轮追问问题
    last_followup_question: Overwrite

    # 追问历史
    followup_history: Append

    # 路由控制：followup / report
    next_action: Overwrite

    # 谎言指数
    lie_index: Overwrite

    # 风险等级
    risk_level: Overwrite

    # 最终测评报告
    final_report: Overwrite
