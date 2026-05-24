# 多 Agent 谎言指数测评系统 v2.0 代码说明

本文档记录项目各代码文件的完成顺序及功能概述。

---

## 代码完成顺序

### 第1层：项目配置与基础设施

| 序号 | 文件 | 功能概述 |
|------|------|----------|
| 1 | `config.py` | 读取环境变量配置，提供全局参数，启动时关闭系统代理。 |
| 2 | `llm_client.py` | 封装 ChatOpenAI 客户端，统一管理 LLM 实例的创建。 |
| 3 | `state_schema.py` | 定义 LangGraph 全局状态 TypedDict，包含所有节点共享的字段。 |
| 4 | `prompts.py` | 集中管理所有 Agent 和节点的 Prompt 模板字符串。 |

---

### 第2层：工具模块

| 序号 | 文件 | 功能概述 |
|------|------|----------|
| 5 | `utils/json_utils.py` | 从 LLM 输出文本中提取 JSON，支持代码块和嵌入格式。 |
| 6 | `utils/text_utils.py` | 格式化对话历史、事实表、异常表，清理 LLM 输出噪音。 |
| 7 | `utils/score_utils.py` | 计算谎言指数（加权聚合）和判定风险等级。 |

---

### 第3层：记忆模块

| 序号 | 文件 | 功能概述 |
|------|------|----------|
| 8 | `memory/fact_table.py` | 管理对话中抽取的事实记录，支持增删查和摘要生成。 |
| 9 | `memory/anomaly_table.py` | 管理发现的异常记录，支持状态更新和未解决异常统计。 |

---

### 第4层：第一版基础节点

| 序号 | 文件 | 功能概述 |
|------|------|----------|
| 10 | `nodes/fact_extraction_node.py` | 从用户回答中抽取与职业身份相关的事实。 |
| 11 | `nodes/anomaly_detection_node.py` | 识别用户对话中可能存在问题的表达（如回避、矛盾）。 |
| 12 | `nodes/consistency_judge_node.py` | 比对新事实与已有事实表，判断是否一致或矛盾。 |
| 13 | `nodes/state_update_node.py` | 汇总本轮信息，更新指示器历史。 |

---

### 第5层：第二版 Specialist Agent 节点（并行执行）

| 序号 | 文件 | 功能概述 |
|------|------|----------|
| 14 | `nodes/specialists/semantic_agent_node.py` | 分析职业身份、岗位、工作内容表述的语义一致性。 |
| 15 | `nodes/specialists/logical_agent_node.py` | 分析职业叙述中的时间线、因果关系是否自洽。 |
| 16 | `nodes/specialists/domain_agent_node.py` | 判断职业描述是否符合基本职业常识（不联网）。 |
| 17 | `nodes/specialists/psycho_linguistic_agent_node.py` | 识别文本中的软性风险信号（回避、模糊、过度解释）。 |

---

### 第6层：第二版争议处理与聚合节点

| 序号 | 文件 | 功能概述 |
|------|------|----------|
| 18 | `nodes/debate_gate_node.py` | 根据分数差异和风险等级判断是否触发 Debate。 |
| 19 | `nodes/debate_node.py` | 汇总各 Agent 分歧，输出结构化争议总结和调整建议。 |
| 20 | `nodes/risk_aggregator_node.py` | 聚合各维度分数，计算综合谎言指数和风险等级。 |

---

### 第7层：策略决策与输出节点

| 序号 | 文件 | 功能概述 |
|------|------|----------|
| 21 | `nodes/strategy_supervisor_node.py` | 根据分析结果决定下一步是追问还是生成报告。 |
| 22 | `nodes/followup_generation_node.py` | 生成一个自然的追问问题，聚焦优先风险点。 |
| 23 | `nodes/report_generation_node.py` | 生成包含谎言指数和多维度分析的最终测评报告。 |

---

### 第8层：图编排与入口

| 序号 | 文件 | 功能概述 |
|------|------|----------|
| 24 | `graph.py` | 用 LangGraph 编排所有节点，构建并行分析和条件路由的工作流图。 |
| 25 | `run_cli.py` | CLI 交互入口，管理多轮对话循环，展示每轮分析摘要和最终报告。 |

---

## 流程图

```
用户输入
    ↓
fact_extraction → anomaly_detection → consistency_judge → state_update
    ↓
┌─────────────────────────────────────────────────────┐
│  并行执行 4 个 Specialist Agent                      │
│  semantic_agent | logical_agent | domain_agent | psycho_linguistic_agent
└─────────────────────────────────────────────────────┘
    ↓
debate_gate → debate（条件触发）→ risk_aggregator
    ↓
strategy_supervisor
    ↓
┌─────────────┐
│ followup_generation │ 或 │ report_generation │
└─────────────┘
    ↓
END
```

---

## 运行方式

```bash
conda activate distilbert
cd D:\lie-deception\code_agent_v2
python -m career_lie_index_agent.run_cli
```

---

## 依赖库

- langgraph
- langchain-core
- langchain-openai
- python-dotenv
- pydantic
