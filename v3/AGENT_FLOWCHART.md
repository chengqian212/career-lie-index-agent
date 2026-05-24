# v3 多 Agent 谎言指数测评系统 - 流程图

## 系统概述

本系统基于 LangGraph 构建，采用多 Agent 协作架构，用于分析对话内容、识别风险信号、并生成相应的追问或最终报告。工作流包含快速预分析、轻量路由、按需专家分析、辩论机制、风险聚合和输出生成等阶段。

**v3.1 改进**：绕过 `strategy_supervisor` 节点，聚合器后直接根据 `round_id` 条件路由到追问或报告，减少一次 LLM 调用。

**v3.2 改进**：合并 `quick_fact_extraction` 和 `quick_signal_detection` 为 `quick_preanalysis`，一次 LLM 调用同时完成事实抽取和表层异常检测，再减少一次 LLM 调用。

---

## 节点类型说明

| 类型 | 标识 | 说明 |
|------|------|------|
| **Agent 节点** | 🤖 | 调用 LLM 进行分析、推理或生成 |
| **规则节点** | ⚙️ | 纯 Python 代码逻辑，基于条件判断、数学计算或数据操作 |
| **混合节点** | ⚙️+🤖 | 先执行规则判断，必要时再调用 LLM |

---

## 核心状态 `DialogueState`

系统维护一个全局状态对象 `DialogueState`，在节点间传递，主要包含：

- **基础对话状态**：轮次信息、对话历史、当前用户输入
- **事实与异常**：`facts_table`、`current_facts`、`anomalies_table`、`current_anomalies`
- **轻量预分析结果**：`has_new_fact`、`surface_risk_score`、`quick_fact_summary`、`quick_signal_summary`
- **专家分析结果**：`specialist_results`、`dimension_scores`、`called_specialists`
- **辩论与聚合结果**：`debate_needed`、`debate_result`、`lie_index`、`risk_explanation`
- **路由与输出控制**：`routing_decision`、`selected_specialists`、`need_specialist`、`next_action`、`final_report`

---

## 流程图

```mermaid
graph TD
    START([开始]) --> QPA[🤖 quick_preanalysis<br/>快速预分析]

    QPA --> LRS[⚙️+🤖 lightweight_routing_supervisor<br/>轻量级路由监督器]

    LRS --> LRS_DECISION{需要专家分析？}

    LRS_DECISION -->|否| LRA[⚙️ lightweight_risk_aggregator<br/>轻量级风险聚合]
    LRS_DECISION -->|是| FANOUT{选择专家}

    FANOUT --> SA[🤖 semantic_agent<br/>语义分析专家]
    FANOUT --> LA[🤖 logical_agent<br/>逻辑分析专家]
    FANOUT --> DA[🤖 domain_agent<br/>领域知识专家]
    FANOUT --> PLA[🤖 psycho_linguistic_agent<br/>心理语言学专家]

    SA --> DG[⚙️ debate_gate<br/>辩论门控]
    LA --> DG
    DA --> DG
    PLA --> DG

    DG --> DG_DECISION{需要辩论？}

    DG_DECISION -->|是| DN[🤖 debate_node<br/>专家辩论]
    DG_DECISION -->|否| RA[⚙️ risk_aggregator<br/>风险聚合器]

    DN --> RA

    LRA --> ROUTE{round_id >= max_rounds?}
    RA --> ROUTE

    ROUTE -->|是| RG[🤖 report_generation<br/>生成最终报告]
    ROUTE -->|否| FG[🤖 followup_generation<br/>生成跟进问题]

    RG --> END([结束])
    FG --> END