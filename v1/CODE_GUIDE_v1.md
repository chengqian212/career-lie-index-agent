# V1 三 Agent 版代码开发顺序说明

本文档交代 `v1` 文件夹中各个代码文件的完成顺序，并对每个代码用一句话概括其功能。

本版将原来的 6 个业务节点简化为 **3 个核心 Agent + 2 个普通节点**，采用 LangGraph 有状态工作流 + 共享 DialogueState 状态更新机制。

---

## 一、基础配置层

开发顺序：**第 1 阶段**

这些文件是整个项目的基础设施，不依赖其他业务代码。

| 文件路径 | 功能概括 |
|---------|---------|
| `config.py` | 保存 API 密钥、模型名、最大轮数、谎言指数权重、风险等级阈值等全局常量配置。 |
| `state_schema.py` | 定义 `DialogueState` TypedDict，标注各字段的 reducer（Overwrite 覆写 / Append 追加）规则。 |
| `prompts.py` | 保存 3 个 Agent 和报告生成节点共 4 个提示词模板（信息比对、策略反馈、追问对话、报告生成）。 |

---

## 二、工具函数层

开发顺序：**第 2 阶段**

这些文件提供通用工具函数，被其他模块调用。

| 文件路径 | 功能概括 |
|---------|---------|
| `utils/env_utils.py` | 清除 http/https 代理环境变量，避免影响阿里云百炼 API 调用。 |
| `utils/json_utils.py` | 从 LLM 响应中解析 JSON，兼容直接 JSON、代码块包裹、裸花括号三种格式。 |
| `utils/text_utils.py` | 提供文本截断、事实表格式化等辅助函数。 |

---

## 三、LLM 调用层

开发顺序：**第 3 阶段**

依赖：`config.py`

| 文件路径 | 功能概括 |
|---------|---------|
| `llm_client.py` | 封装 LLM 调用，提供纯文本和 JSON 两种调用方式，连接阿里云百炼 deepseek-v3。 |

---

## 四、数据存储层

开发顺序：**第 4 阶段**

这些文件提供事实表和异常表的查询与操作函数。

| 文件路径 | 功能概括 |
|---------|---------|
| `memory/fact_table.py` | 提供按 slot、按 fact_id 查询事实以及生成事实表摘要的辅助函数。 |
| `memory/anomaly_table.py` | 提供查找未澄清异常、按 id 查找、标记已澄清等辅助函数。 |

---

## 五、三个 Agent 层

开发顺序：**第 5 阶段**

依赖：`state_schema.py`, `llm_client.py`, `prompts.py`, `utils/json_utils.py`, `utils/text_utils.py`, `memory/*`

| 文件路径 | 功能概括 |
|---------|---------|
| `agents/information_comparison_agent.py` | Agent 2：调用 LLM 完成事实抽取、异常识别、历史比对，输出结构化分析结果。 |
| `agents/strategy_feedback_agent.py` | Agent 3：调用 LLM 根据比对结果和异常表决定下一轮追问策略及是否生成报告。 |
| `agents/followup_dialogue_agent.py` | Agent 1：调用 LLM 根据策略生成一个自然、温和、不像审问的追问问题。 |

---

## 六、普通节点层

开发顺序：**第 6 阶段**

依赖：`state_schema.py`, `config.py`, `llm_client.py`, `prompts.py`, `utils/json_utils.py`

| 文件路径 | 功能概括 |
|---------|---------|
| `nodes/state_update_node.py` | 用 Python 更新事实表、异常表、对话历史，计算谎言指数和风险等级（不调用 LLM）。 |
| `nodes/report_generation_node.py` | 调用 LLM 根据全部状态生成最终谎言指数测评报告。 |

---

## 七、工作流层

开发顺序：**第 7 阶段**

依赖：`state_schema.py`, 3 个 Agent 节点, 2 个普通节点

| 文件路径 | 功能概括 |
|---------|---------|
| `graph.py` | 定义 LangGraph 三 Agent 工作流，注册 5 个节点、串行边和条件路由，编译为可执行图。 |

---

## 八、应用入口层

开发顺序：**第 8 阶段（最后）**

依赖：`config.py`, `graph.py`, `utils/env_utils.py`

| 文件路径 | 功能概括 |
|---------|---------|
| `run_cli.py` | 命令行多轮对话入口，循环接收用户输入，调用工作流，展示追问、谎言指数、策略和最终报告。 |

---

## 总结：依赖关系图

```
config.py
    ↓
state_schema.py
    ↓
prompts.py
    ↓
utils/env_utils.py, utils/json_utils.py, utils/text_utils.py
    ↓
llm_client.py
    ↓
memory/fact_table.py, memory/anomaly_table.py
    ↓
agents/information_comparison_agent.py   ← Agent 2
agents/strategy_feedback_agent.py        ← Agent 3
agents/followup_dialogue_agent.py        ← Agent 1
    ↓
nodes/state_update_node.py
nodes/report_generation_node.py
    ↓
graph.py
    ↓
run_cli.py
```

---

## 工作流执行顺序

```
START
  ↓
information_comparison_agent   ← Agent 2：发现事实和异常
  ↓
state_update                   ← Python：维护事实表、异常表、风险分
  ↓
strategy_feedback_agent        ← Agent 3：决定追问策略
  ↓
route_next
  ├── generate_followup → followup_dialogue_agent → END   ← Agent 1：自然追问
  └── final_report     → report_generation      → END
```

---

## 补充说明

- **`__init__.py` 文件**：各目录下的 `__init__.py` 为 Python 包标识文件，无需特别说明。
- **`outputs/` 目录**：存放运行时生成的日志和报告，不属于代码文件。
- **`requirements.txt`**：列出项目依赖包（langgraph, langchain-openai, langchain-core, python-dotenv）。
