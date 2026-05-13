"""CLI 入口：命令行交互式多 Agent 谎言指数测评系统"""

import json
import os
import sys
from datetime import datetime

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from career_lie_index_agent.config import (
    disable_proxy,
    MAX_ROUNDS,
)
from career_lie_index_agent.graph import build_graph
from career_lie_index_agent.state_schema import DialogueState


def create_initial_state(max_rounds: int = MAX_ROUNDS) -> dict:
    """创建初始状态

    Args:
        max_rounds: 最大轮次
    Returns:
        初始状态字典
    """
    return {
        "round_id": 0,
        "max_rounds": max_rounds,
        "current_user_text": "",
        "dialogue_history": [],
        "current_facts": [],
        "facts_table": [],
        "current_anomalies": [],
        "indicator_history": [],
        "consistency_results": [],
        "anomalies_table": [],
        "last_followup_question": "",
        "followup_history": [],
        "specialist_results": [],
        "dimension_scores": {},
        "agent_votes": {},
        "debate_needed": False,
        "debate_result": None,
        "lie_index": 0.0,
        "risk_level": "低",
        "risk_explanation": [],
        "next_action": "",
        "final_report": None,
    }


def print_round_summary(state: dict) -> None:
    """打印每轮分析摘要

    Args:
        state: 当前状态
    """
    lie_index = state.get("lie_index", 0)
    risk_level = state.get("risk_level", "低")
    dimension_scores = state.get("dimension_scores", {})
    debate_needed = state.get("debate_needed", False)
    risk_explanation = state.get("risk_explanation", [])
    followup = state.get("last_followup_question", "")

    print("\n" + "=" * 60)
    print(f"📊 当前谎言指数：{lie_index} / 100（风险等级：{risk_level}）")
    print("-" * 60)

    if dimension_scores:
        print("📈 各维度分数：")
        score_names = {
            "semantic": "语义一致性",
            "logical": "逻辑时间线",
            "domain": "职业常识",
            "psycho_linguistic": "心理语言",
        }
        for key, name in score_names.items():
            score = dimension_scores.get(key, 0)
            print(f"   {name}：{score}")

    print("-" * 60)
    print(f"💬 是否触发 Debate：{'是' if debate_needed else '否'}")

    if risk_explanation:
        print("⚠️  主要风险理由：")
        for exp in risk_explanation:
            print(f"   - {exp}")

    print("-" * 60)
    if followup:
        print(f"🔍 追问：{followup}")
    print("=" * 60)


def print_final_report(state: dict) -> None:
    """打印最终报告

    Args:
        state: 当前状态
    """
    final_report = state.get("final_report")
    if not final_report:
        print("\n❌ 未生成最终报告")
        return

    print("\n" + "=" * 60)
    print("📋 最终测评报告")
    print("=" * 60)
    print(final_report.get("report_text", ""))
    print("=" * 60)

    # 保存报告到文件
    save_report(final_report)


def save_report(report: dict) -> None:
    """保存报告到文件

    Args:
        report: 报告字典
    """
    reports_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "outputs",
        "reports",
    )
    os.makedirs(reports_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"report_{timestamp}.json"
    filepath = os.path.join(reports_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n💾 报告已保存至：{filepath}")


def run_cli():
    """主 CLI 交互循环"""
    # 关闭代理
    disable_proxy()

    print("🤖 多 Agent 谎言指数测评系统 v2.0")
    print(f"   最大对话轮次：{MAX_ROUNDS}")
    print("   输入 'quit' 退出，输入 'skip' 跳过当前轮次")
    print()

    # 构建图
    graph = build_graph()

    # 初始化状态
    state = create_initial_state()

    # 第一轮系统开场白
    opening_question = "你平时是做什么方向的工作呀？"
    print(f"系统：{opening_question}")
    state["last_followup_question"] = opening_question
    state["dialogue_history"].append({
        "role": "assistant",
        "content": opening_question,
    })

    # 主循环
    for round_num in range(1, MAX_ROUNDS + 1):
        state["round_id"] = round_num
        state["specialist_results"] = []  # 每轮清空，由 reducer 重新填充

        # 获取用户输入
        user_input = input("\n用户：").strip()

        if user_input.lower() == "quit":
            print("退出系统。")
            break

        if user_input.lower() == "skip" or not user_input:
            print("（跳过本轮）")
            continue

        # 更新状态
        state["current_user_text"] = user_input
        state["dialogue_history"].append({
            "role": "user",
            "content": user_input,
        })

        # 运行图
        try:
            result = graph.invoke(state)

            # 更新状态（保留完整结果）
            state.update(result)

            # 打印本轮摘要
            print_round_summary(state)

            # 将追问加入对话历史
            followup = state.get("last_followup_question", "")
            if followup and state.get("next_action") != "final_report":
                state["dialogue_history"].append({
                    "role": "assistant",
                    "content": followup,
                })

            # 检查是否已生成最终报告（图内已路由到 report_generation）
            if state.get("next_action") == "final_report":
                print_final_report(state)
                break

        except Exception as e:
            print(f"\n❌ 运行出错：{e}")
            import traceback
            traceback.print_exc()
            continue

    else:
        # 达到最大轮次但最后一轮走的是 followup，需额外生成报告
        print("\n🔄 已达到最大轮次，正在生成最终报告...")
        state["round_id"] = MAX_ROUNDS
        state["specialist_results"] = []
        state["next_action"] = "final_report"
        try:
            result = graph.invoke(state)
            state.update(result)
            print_final_report(state)
        except Exception as e:
            print(f"\n❌ 生成报告出错：{e}")
            import traceback
            traceback.print_exc()

    print("\n👋 感谢使用！")


if __name__ == "__main__":
    run_cli()
