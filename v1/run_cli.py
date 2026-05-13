"""
命令行多轮对话 Demo：启动时关闭代理，循环接收用户输入并调用 LangGraph 工作流，输出追问和最终报告。
调用关系：调用 utils/env_utils.py 关闭代理；调用 config.py 读取轮数；调用 graph.py 构建工作流。
输入：用户键盘输入
输出：终端打印（追问、事实、异常、谎言指数、最终报告）
"""
import json
from typing import Any
from utils.env_utils import disable_proxy
from config import MAX_ROUNDS
from graph import build_graph
from state_schema import DialogueState


def create_initial_state() -> dict[str, Any]:
    """创建初始状态"""
    return {
        "round_id": 0,
        "max_rounds": MAX_ROUNDS,
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
        "next_action": "",
        "lie_index": 0,
        "risk_level": "低",
        "final_report": None,
    }


def main():
    # 关闭代理
    disable_proxy()

    print("=" * 60)
    print("  职业身份谎言指数测评系统")
    print("=" * 60)
    print()

    # 构建工作流
    app = build_graph()
    state: dict[str, Any] = create_initial_state()

    # 开场问题
    opening_question = "你平时是做什么工作的呀？"
    print(f"系统：{opening_question}")
    state["last_followup_question"] = opening_question

    # 多轮对话
    while state["round_id"] < state["max_rounds"]:
        user_input = input("\n你：").strip()
        if not user_input:
            print("（输入为空，请重新输入）")
            continue
        if user_input.lower() in ("exit", "quit", "退出"):
            print("\n已退出对话。")
            break

        # 更新轮次和当前输入
        state["round_id"] += 1
        state["current_user_text"] = user_input
        state["current_facts"] = []
        state["current_anomalies"] = []
        state["consistency_results"] = []

        print(f"\n--- 第 {state['round_id']} 轮 ---")

        # 运行工作流
        result = app.invoke(state)  # type: ignore[arg-type]

        # 更新状态
        state.update(result)

        # 显示本轮信息
        print(f"\n[抽取事实] {json.dumps(state.get('current_facts', []), ensure_ascii=False)}")
        print(f"[异常表达] {json.dumps(state.get('current_anomalies', []), ensure_ascii=False)}")
        print(f"[一致性判断] {json.dumps(state.get('consistency_results', []), ensure_ascii=False)}")
        print(f"[谎言指数] {state.get('lie_index', 0)}  [风险等级] {state.get('risk_level', '低')}")

        # 判断是否结束
        if state["round_id"] >= state["max_rounds"]:
            break

        # 显示追问
        question = state.get("last_followup_question", "")
        if question:
            print(f"\n系统：{question}")

    # 输出最终报告
    print("\n" + "=" * 60)
    print("  最终测评报告")
    print("=" * 60)
    report = state.get("final_report")
    if report:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("未生成报告。")

    print(f"\n最终谎言指数：{state.get('lie_index', 0)}")
    print(f"最终风险等级：{state.get('risk_level', '低')}")


if __name__ == "__main__":
    main()
