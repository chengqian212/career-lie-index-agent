"""Streamlit 前端：多 Agent 相亲对话小助手 v3.0

该模块实现了 v3 版本的 Web 交互界面，主要特性包括：
- 美观的聊天界面，大字体显示用户回答和AI提问
- AI提问流式输出效果
- 实时显示分析过程和结果
- 支持中文输出
"""

import json
import os
import sys
import time
from datetime import datetime

import streamlit as st

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from v3.config import (
    disable_proxy,
    MAX_ROUNDS,
)
from v3.graph import build_graph


# ============== 页面配置 ==============
st.set_page_config(
    page_title="多 Agent 相亲对话小助手 v3.0",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============== 自定义CSS样式 ==============
st.markdown("""
<style>
/* 全局字体设置 */
body {
    font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif;
}

/* 用户消息样式 - 大字体 */
.user-message {
    font-size: 1.3rem !important;
    line-height: 1.8 !important;
    color: #1a1a2e !important;
    padding: 12px 16px !important;
    border-radius: 12px !important;
    background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%) !important;
    border-left: 4px solid #2196f3 !important;
    margin: 8px 0 !important;
}

/* AI消息样式 - 大字体 */
.ai-message {
    font-size: 1.3rem !important;
    line-height: 1.8 !important;
    color: #1a1a2e !important;
    padding: 12px 16px !important;
    border-radius: 12px !important;
    background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%) !important;
    border-left: 4px solid #9c27b0 !important;
    margin: 8px 0 !important;
}

/* 流式输出光标效果 */
.streaming-cursor {
    display: inline-block;
    width: 2px;
    height: 1.2em;
    background-color: #9c27b0;
    animation: blink 0.8s infinite;
    vertical-align: text-bottom;
    margin-left: 2px;
}

@keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0; }
}

/* 消息容器 */
.chat-message {
    margin-bottom: 16px;
}

/* 角色标签 */
.role-label {
    font-size: 0.85rem;
    font-weight: 600;
    color: #666;
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 6px;
}

/* 侧边栏样式 */
.sidebar-title {
    font-size: 1.1rem;
    font-weight: bold;
    color: #333;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 2px solid #e0e0e0;
}

/* 统计卡片 */
.stat-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 16px;
    border-radius: 12px;
    margin-bottom: 12px;
    text-align: center;
}

.stat-value {
    font-size: 2rem;
    font-weight: bold;
}

.stat-label {
    font-size: 0.85rem;
    opacity: 0.9;
}

/* 风险等级指示器 */
.risk-indicator {
    padding: 8px 16px;
    border-radius: 8px;
    font-weight: bold;
    text-align: center;
    margin: 8px 0;
}

.risk-low {
    background-color: #e8f5e9;
    color: #2e7d32;
}

.risk-medium {
    background-color: #fff3e0;
    color: #ef6c00;
}

.risk-high {
    background-color: #ffebee;
    color: #c62828;
}

/* 分析过程折叠面板 */
.analysis-panel {
    background-color: #fafafa;
    border-radius: 8px;
    padding: 12px;
    margin-top: 8px;
}

/* 输入框样式 */
.stTextInput > div > div > input {
    font-size: 1.1rem !important;
    padding: 12px 16px !important;
}

/* 按钮样式 */
.stButton > button {
    font-size: 1rem !important;
    padding: 8px 24px !important;
    border-radius: 8px !important;
}

/* 隐藏默认的streamlit元素 */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* 欢迎区域 */
.welcome-area {
    text-align: center;
    padding: 40px 20px;
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    border-radius: 16px;
    margin-bottom: 24px;
}

.welcome-title {
    font-size: 2rem;
    font-weight: bold;
    color: #333;
    margin-bottom: 12px;
}

.welcome-subtitle {
    font-size: 1.1rem;
    color: #666;
}

/* 报告区域 */
.report-area {
    background: linear-gradient(135deg, #fff8e1 0%, #ffecb3 100%);
    border-radius: 12px;
    padding: 20px;
    margin-top: 16px;
    border-left: 4px solid #ffc107;
}

/* 专家标签 */
.specialist-tag {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    margin-right: 4px;
    margin-bottom: 4px;
}

.specialist-semantic { background-color: #e3f2fd; color: #1565c0; }
.specialist-logical { background-color: #e8f5e9; color: #2e7d32; }
.specialist-domain { background-color: #fff3e0; color: #ef6c00; }
.specialist-psycho { background-color: #f3e5f5; color: #7b1fa2; }
</style>
""", unsafe_allow_html=True)


# ============== 初始化函数 ==============
def create_initial_state(max_rounds: int = MAX_ROUNDS) -> dict:
    """创建初始状态"""
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
        "debate_needed": False,
        "debate_result": None,
        "lie_index": 0.0,
        "risk_explanation": [],
        "next_action": "",
        "final_report": None,
        "quick_fact_summary": "",
        "quick_signal_summary": "",
        "surface_risk_score": 0.0,
        "has_new_fact": False,
        "routing_decision": {},
        "selected_specialists": [],
        "need_specialist": False,
        "priority_issue": "",
        "followup_strategy": "",
        "called_specialists": [],
        # v3.3 新增字段
        "stop_reason": "",
        "target_anomaly_id": "",
    }


def get_risk_level(lie_index: float) -> tuple[str, str]:
    """根据谎言指数返回风险等级和样式类"""
    if lie_index >= 70:
        return "高风险", "risk-high"
    elif lie_index >= 30:
        return "中风险", "risk-medium"
    else:
        return "低风险", "risk-low"


def get_specialist_name(specialist: str) -> str:
    """获取专家中文名称"""
    mapping = {
        "semantic": "语义分析",
        "logical": "逻辑分析",
        "domain": "职业常识",
        "psycho_linguistic": "心理语言",
    }
    return mapping.get(specialist, specialist)


def get_specialist_class(specialist: str) -> str:
    """获取专家标签样式类"""
    mapping = {
        "semantic": "specialist-semantic",
        "logical": "specialist-logical",
        "domain": "specialist-domain",
        "psycho_linguistic": "specialist-psycho",
    }
    return mapping.get(specialist, "specialist-semantic")


def render_message(msg: dict, is_streaming: bool = False):
    """渲染单条消息

    Args:
        msg: 消息字典，包含 role 和 content
        is_streaming: 是否正在流式输出（显示光标）
    """
    role = msg["role"]
    content = msg["content"]
    cursor_html = '<span class="streaming-cursor"></span>' if is_streaming else ""

    if role == "user":
        st.markdown(f"""
        <div class="chat-message">
            <div class="role-label">👤 用户</div>
            <div class="user-message">{content}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="chat-message">
            <div class="role-label">🤖 AI</div>
            <div class="ai-message">{content}{cursor_html}</div>
        </div>
        """, unsafe_allow_html=True)


def _save_session_to_outputs(state: dict, thinking_history: list) -> str:
    """保存完整测试会话到 outputs/reports 目录

    Args:
        state: 完整的对话状态字典
        thinking_history: 每轮耗时记录列表

    Returns:
        保存后的文件路径
    """
    reports_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "outputs",
        "reports",
    )
    os.makedirs(reports_dir, exist_ok=True)

    data = {
        "round_id": state.get("round_id"),
        "max_rounds": state.get("max_rounds"),
        "dialogue_history": state.get("dialogue_history", []),
        "followup_history": state.get("followup_history", []),
        "facts_table": state.get("facts_table", []),
        "anomalies_table": state.get("anomalies_table", []),
        "indicator_history": state.get("indicator_history", []),
        "lie_index": state.get("lie_index", 0.0),
        "dimension_scores": state.get("dimension_scores", {}),
        "risk_explanation": state.get("risk_explanation", []),
        "called_specialists": state.get("called_specialists", []),
        "routing_decision": state.get("routing_decision", {}),
        "final_report": state.get("final_report"),
        "thinking_time_history": thinking_history,
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"session_{timestamp}.json"
    filepath = os.path.join(reports_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return filepath


# ============== Streamlit 应用主体 ==============
def main():
    # 关闭代理
    disable_proxy()

    # 初始化 session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "state" not in st.session_state:
        st.session_state.state = create_initial_state()
    if "graph" not in st.session_state:
        st.session_state.graph = build_graph()
    if "round_num" not in st.session_state:
        st.session_state.round_num = 0
    if "started" not in st.session_state:
        st.session_state.started = False
    if "final_report_shown" not in st.session_state:
        st.session_state.final_report_shown = False
    if "current_lie_index" not in st.session_state:
        st.session_state.current_lie_index = 0.0
    if "dimension_scores" not in st.session_state:
        st.session_state.dimension_scores = {}
    if "called_specialists" not in st.session_state:
        st.session_state.called_specialists = []
    if "streaming_text" not in st.session_state:
        st.session_state.streaming_text = ""
    if "is_streaming" not in st.session_state:
        st.session_state.is_streaming = False
    if "thinking_time_history" not in st.session_state:
        st.session_state.thinking_time_history = []

    if "last_thinking_time" not in st.session_state:
        st.session_state.last_thinking_time = 0.0

    if "saved_filepath" not in st.session_state:
        st.session_state.saved_filepath = ""

    # ============== 侧边栏 ==============
    with st.sidebar:
        st.markdown('<div class="sidebar-title">📊 系统状态</div>', unsafe_allow_html=True)

        # 当前轮次
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{st.session_state.round_num} / {MAX_ROUNDS}</div>
            <div class="stat-label">当前轮次</div>
        </div>
        """, unsafe_allow_html=True)

        # 谎言指数
        lie_index = st.session_state.current_lie_index
        risk_level, risk_class = get_risk_level(lie_index)
        st.markdown(f"""
        <div class="stat-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
            <div class="stat-value">{lie_index:.1f}</div>
            <div class="stat-label">风险指数</div>
        </div>
        """, unsafe_allow_html=True)

        # 风险等级
        st.markdown(f'<div class="risk-indicator {risk_class}">{risk_level}</div>', unsafe_allow_html=True)

        # 维度分数
        st.markdown('<div class="sidebar-title">📈 维度分数</div>', unsafe_allow_html=True)
        dimension_scores = st.session_state.dimension_scores
        if dimension_scores:
            score_names = {
                "semantic": "语义一致性",
                "logical": "逻辑时间线",
                "domain": "职业常识",
                "psycho_linguistic": "心理语言",
                "lightweight_surface": "表层风险",
                "unresolved_anomalies": "未澄清异常",
            }
            for key, score in dimension_scores.items():
                name = score_names.get(key, key)
                st.progress(min(score / 100, 1.0), text=f"{name}: {score}")
        else:
            st.info("暂无维度分数数据")

        # 已调用专家
        st.markdown('<div class="sidebar-title">🤖 已调用专家</div>', unsafe_allow_html=True)
        called = st.session_state.called_specialists
        if called:
            for spec in called:
                st.markdown(f'<span class="specialist-tag {get_specialist_class(spec)}">{get_specialist_name(spec)}</span>', unsafe_allow_html=True)
        else:
            st.info("本轮尚未调用专家")
        # 思考耗时
        st.markdown('<div class="sidebar-title">⏱️ 思考耗时</div>', unsafe_allow_html=True)

        last_time = st.session_state.last_thinking_time
        if last_time > 0:
            st.metric("最近一轮耗时", f"{last_time:.2f} 秒")
        else:
            st.info("暂无耗时记录")

        history = st.session_state.thinking_time_history
        if history:
            with st.expander("查看每轮耗时", expanded=False):
                for item in reversed(history[-10:]):
                    st.write(
                        f"第 {item['round']} 轮：{item['elapsed']:.2f} 秒 "
                        f"（{item['time']}）"
                    )
        # 分隔线
        st.divider()

        # 操作按钮
        if st.button("🔄 重新开始", use_container_width=True):
            st.session_state.messages = []
            st.session_state.state = create_initial_state()
            st.session_state.round_num = 0
            st.session_state.started = False
            st.session_state.final_report_shown = False
            st.session_state.current_lie_index = 0.0
            st.session_state.dimension_scores = {}
            st.session_state.called_specialists = []
            st.session_state.streaming_text = ""
            st.session_state.is_streaming = False
            st.session_state.thinking_time_history = []
            st.session_state.last_thinking_time = 0.0
            st.session_state.saved_filepath = ""
            st.rerun()

    # ============== 主内容区 ==============
    st.title("🤖 多 Agent 相亲对话小助手 v3.0")

    # 欢迎区域（仅在未开始时显示）
    if not st.session_state.started:
        st.markdown(f"""
        <div class="welcome-area">
            <div class="welcome-title">👋 欢迎使用风险指数测评系统</div>
            <div class="welcome-subtitle">
                本系统通过多 Agent 协作分析，评估对话中的风险指数。<br>
                系统将自动进行语义分析、逻辑验证、领域知识检查和心理语言学分析。<br>
                最大对话轮次：{MAX_ROUNDS}轮
            </div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 开始测评", use_container_width=True, type="primary"):
                st.session_state.started = True
                # 初始化第一轮
                opening_question = "你平时是做什么方向的工作呀？"
                st.session_state.messages.append({"role": "assistant", "content": opening_question})
                st.session_state.state["last_followup_question"] = opening_question
                st.session_state.state["dialogue_history"].append({
                    "role": "assistant",
                    "content": opening_question,
                })
                st.rerun()
        return

    # ============== 聊天历史显示 ==============
    chat_container = st.container()
    with chat_container:
        for i, msg in enumerate(st.session_state.messages):
            # 最后一条AI消息且正在流式输出时显示光标
            is_last = (i == len(st.session_state.messages) - 1)
            is_streaming = is_last and st.session_state.is_streaming and msg["role"] == "assistant"
            render_message(msg, is_streaming=is_streaming)

    # ============== 最终报告显示 ==============
    if st.session_state.final_report_shown and st.session_state.state.get("final_report"):
        report = st.session_state.state["final_report"]
        st.markdown("""
        <div class="report-area">
            <h3>📋 最终测评报告</h3>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(report.get("report_text", ""))

    # ============== 输入区域 ==============
    if st.session_state.started and not st.session_state.final_report_shown:
        # 检查是否已达到最大轮次
        if st.session_state.round_num >= MAX_ROUNDS:
            st.warning("已达到最大对话轮次，正在生成最终报告...")
            _generate_final_report()
            return

        # 用户输入
        user_input = st.chat_input("请输入您的回答...")

        if user_input:
            # 添加用户消息
            st.session_state.messages.append({"role": "user", "content": user_input})
            st.session_state.state["current_user_text"] = user_input
            st.session_state.state["dialogue_history"].append({
                "role": "user",
                "content": user_input,
            })

            # 增加轮次
            st.session_state.round_num += 1
            round_num = st.session_state.round_num
            st.session_state.state["round_id"] = round_num
            st.session_state.state["specialist_results"] = []
            st.session_state.state["called_specialists"] = []

            # 显示思考中状态
            with st.status("🤔 系统思考中...", expanded=False) as status:
                # 运行工作流
                try:
                    t_start = time.time()
                    result = st.session_state.graph.invoke(st.session_state.state)
                    t_end = time.time()
                    elapsed = t_end - t_start

                    st.session_state.last_thinking_time = elapsed
                    st.session_state.thinking_time_history.append({
                        "round": round_num,
                        "elapsed": elapsed,
                        "time": datetime.now().strftime("%H:%M:%S"),
                    })
                    # 更新状态
                    st.session_state.state.update(result)

                    # 更新显示数据
                    st.session_state.current_lie_index = result.get("lie_index", 0.0)
                    st.session_state.dimension_scores = result.get("dimension_scores", {})
                    st.session_state.called_specialists = result.get("called_specialists", [])

                    status.update(label=f"✅ 分析完成（耗时 {elapsed:.2f}秒）", state="complete")

                except Exception as e:
                    status.update(label=f"❌ 分析出错: {str(e)}", state="error")
                    st.error(f"运行出错：{e}")
                    return

            # 获取追问或报告
            next_action = st.session_state.state.get("next_action", "")

            if next_action == "final_report":
                # 生成最终报告
                _generate_final_report()
            else:
                # 获取追问问题
                followup = st.session_state.state.get("last_followup_question", "")
                if followup:
                    # 使用流式输出显示AI提问
                    _stream_ai_message(followup)

            st.rerun()


def _stream_ai_message(message: str, chunk_size: int = 2, delay: float = 0.03):
    """流式输出AI消息

    使用 Streamlit 的 st.empty() 占位符和 time.sleep() 模拟流式输出效果。
    注意：由于 Streamlit 的运行机制，这里的流式输出是在单次脚本运行中完成的。

    Args:
        message: 要显示的完整消息
        chunk_size: 每次显示的字符数
        delay: 每次显示的延迟（秒）
    """
    # 先添加一个空消息到历史记录（占位）
    st.session_state.messages.append({"role": "assistant", "content": ""})
    msg_index = len(st.session_state.messages) - 1

    # 创建占位符用于流式输出
    placeholder = st.empty()
    displayed_text = ""

    # 模拟流式输出
    for i in range(0, len(message), chunk_size):
        chunk = message[i:i + chunk_size]
        displayed_text += chunk

        # 更新消息内容
        st.session_state.messages[msg_index]["content"] = displayed_text

        # 更新显示，添加光标效果
        placeholder.markdown(f"""
        <div class="chat-message">
            <div class="role-label">🤖 AI</div>
            <div class="ai-message">{displayed_text}<span class="streaming-cursor"></span></div>
        </div>
        """, unsafe_allow_html=True)

        time.sleep(delay)

    # 最终显示（去掉光标）
    st.session_state.messages[msg_index]["content"] = message
    placeholder.markdown(f"""
    <div class="chat-message">
        <div class="role-label">🤖 AI</div>
        <div class="ai-message">{message}</div>
    </div>
    """, unsafe_allow_html=True)

    # 将追问加入对话历史（用于后端状态）
    st.session_state.state["dialogue_history"].append({
        "role": "assistant",
        "content": message,
    })


def _generate_final_report():
    """生成并显示最终报告，同时保存完整测试记录"""
    # 保护：避免重复生成
    if st.session_state.final_report_shown:
        return

    st.session_state.state["round_id"] = MAX_ROUNDS
    st.session_state.state["specialist_results"] = []
    st.session_state.state["called_specialists"] = []
    st.session_state.state["next_action"] = "final_report"

    try:
        with st.spinner("📋 正在生成最终报告..."):
            result = st.session_state.graph.invoke(st.session_state.state)
            st.session_state.state.update(result)

        st.session_state.final_report_shown = True

        # 更新最终数据
        st.session_state.current_lie_index = result.get("lie_index", 0.0)
        st.session_state.dimension_scores = result.get("dimension_scores", {})

        # 保存完整 session 数据到 outputs 目录
        saved_path = _save_session_to_outputs(
            st.session_state.state,
            st.session_state.thinking_time_history,
        )
        st.session_state.saved_filepath = saved_path
        st.success(f"💾 完整测试记录已保存至：{saved_path}")

    except Exception as e:
        st.error(f"生成报告出错：{e}")


if __name__ == "__main__":
    main()
