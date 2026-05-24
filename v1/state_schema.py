"""
全局状态定义：定义 DialogueState TypedDict，标注各字段的 reducer（Overwrite 覆盖 / Append 追加）。
调用关系：被 graph.py 和所有 Agent 节点、普通节点文件引用。
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
    """多轮对话全局状态（三 Agent 版）"""
    # 轮次控制
    round_id: Overwrite
    max_rounds: Overwrite

    # 当前用户输入
    current_user_text: Overwrite

    # 对话历史：每项为 {"round_id": int, "role": "user"/"assistant", "content": "..."}
    dialogue_history: Append

    # Agent 2 输出：当前事实、当前异常、事实比对结果
    current_facts: Overwrite
    current_anomalies: Overwrite
    consistency_results: Overwrite

    # 状态表
    facts_table: Overwrite
    anomalies_table: Overwrite
    indicator_history: Append

    # Agent 3 输出：策略反馈
    priority_issue: Overwrite
    followup_strategy: Overwrite
    strategy_reason: Overwrite
    next_action: Overwrite

    # Agent 1 输出：追问
    last_followup_question: Overwrite
    followup_history: Append

    # 谎言指数
    lie_index: Overwrite
    risk_level: Overwrite

    # 最终报告
    final_report: Overwrite
