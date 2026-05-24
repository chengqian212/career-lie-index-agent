# V1 三 Agent 版代码开发顺序说明

本文档用于指导代码生成 Agent 直接落地实现 `v1` 项目。

本版根据老师建议，将原来的多个业务节点简化为 **3 个核心 Agent**：

```text
Agent 1：追问对话 Agent
Agent 2：信息比对 Agent
Agent 3：策略反馈 Agent
```

本项目不采用自由 ReAct-Agent，也不采用复杂多 Agent 群聊，而是采用：

```text
LangGraph 有状态工作流
+
3 个角色明确的 Agent 节点
+
共享 DialogueState 状态更新机制
```

核心思想是：

```text
Agent 2 负责看懂用户说了什么，并和历史信息比对；
Agent 3 负责根据比对结果决定下一步追问策略；
Agent 1 负责把策略转化成自然、不像审问的追问问题。
```

---

# 一、项目目标

本项目面向交友聊天中的职业身份叙述场景，围绕用户对自己职业、岗位、行业、工作内容、经历阶段等信息的多轮回答，进行内部一致性分析，并输出一个可解释的谎言指数 / 风险指数。

系统不做外部联网核查，不做真实身份认证，也不直接判定“对方一定在说谎”。

系统只根据多轮对话内部信息，分析是否存在：

```text
1. 前后事实不一致
2. 职业身份与工作内容不匹配
3. 时间阶段表达不清
4. 回避、模糊、答非所问等异常表达
5. 需要继续追问澄清的风险线索
```

第一版目标是实现一个可运行的命令行 Demo，完成以下闭环：

```text
用户输入回答
→ Agent 2 信息比对：抽取事实、识别异常、比对历史
→ Python 状态更新：更新事实表、异常表、谎言指数
→ Agent 3 策略反馈：决定下一轮追问重点
→ Agent 1 追问对话：生成自然追问
→ 多轮结束后输出最终测评报告
```

---

# 二、总体架构

## 2.1 三 Agent 分工

```text
Agent 1：追问对话 Agent / Follow-up Dialogue Agent

职责：
1. 根据 Agent 3 给出的追问策略生成下一轮问题。
2. 保持语气自然，像正常聊天中的好奇追问。
3. 不直接判断用户是否说谎。
4. 不直接负责事实比对。
5. 不使用“撒谎”“矛盾”“测谎”“核查”等词。
```

```text
Agent 2：信息比对 Agent / Evidence Comparison Agent

职责：
1. 从当前用户回答中抽取职业身份相关事实。
2. 识别当前回答中的异常表达。
3. 将当前事实与历史事实表进行比对。
4. 输出新增事实、补充细节、一致、潜在不匹配、明显冲突、无法判断等关系。
5. 为后续策略决策提供证据。
```

```text
Agent 3：策略反馈 Agent / Strategy Feedback Agent

职责：
1. 读取 Agent 2 的事实比对结果和异常结果。
2. 判断当前最值得追问的问题。
3. 决定下一轮追问策略。
4. 决定是否继续追问，还是生成最终报告。
5. 将追问重点反馈给 Agent 1。
```

---

## 2.2 为什么不用自由 ReAct-Agent

本项目流程较固定，不需要让模型自由决定工具调用顺序。

不建议采用自由 ReAct-Agent 的原因：

```text
1. 追问任务需要稳定、可控、可解释。
2. 自由 ReAct 容易导致追问发散。
3. 状态更新容易混乱。
4. 很难解释系统为什么提出某个问题。
5. 本项目核心是“事实表 + 异常表 + 追问策略”，更适合 LangGraph 有状态工作流。
```

因此，本版采用：

```text
静态 LangGraph 工作流
+
共享状态 DialogueState
+
3 个职责明确的 Agent 节点
```

---

# 三、系统工作流

## 3.1 单轮流程

每一轮用户回答之后，系统按以下顺序执行：

```text
用户输入 current_user_text
↓
Agent 2：information_comparison_agent_node
    - 抽取当前事实 current_facts
    - 识别当前异常 current_anomalies
    - 比对历史事实 consistency_results
↓
state_update_node
    - 更新 dialogue_history
    - 更新 facts_table
    - 更新 anomalies_table
    - 更新 indicator_history
    - 计算 lie_index
    - 计算 risk_level
↓
Agent 3：strategy_feedback_agent_node
    - 选择 priority_issue
    - 选择 followup_strategy
    - 决定 next_action
↓
条件路由 route_node
    - next_action = generate_followup → Agent 1
    - next_action = final_report → report_generation_node
↓
Agent 1：followup_dialogue_agent_node
    - 生成下一轮自然追问
```

---

## 3.2 总体流程图

```text
START
  ↓
user_input
  ↓
information_comparison_agent_node      # Agent 2
  ↓
state_update_node                      # Python 状态更新
  ↓
strategy_feedback_agent_node           # Agent 3
  ↓
route_node
  ├── generate_followup → followup_dialogue_agent_node → END
  └── final_report     → report_generation_node        → END
```

说明：

```text
1. Agent 2 是分析者，负责发现问题。
2. state_update_node 是记忆管理器，负责保存问题。
3. Agent 3 是策略者，负责决定问什么。
4. Agent 1 是表达者，负责把追问说得自然。
```

---

# 四、技术路线

第一版采用：

```text
Python 3.10+
LangGraph
LangChain Core
OpenAI-compatible 客户端
阿里云百炼 deepseek-v3
python-dotenv
pydantic / TypedDict
CLI 命令行交互
```

不使用：

```text
1. 不训练 BERT 或其他本地模型
2. 不做 LoRA / 微调
3. 不使用向量数据库
4. 不使用图数据库
5. 不做外部搜索验证
6. 不接入语音、视频
7. 不做 Streamlit 页面
8. 不做复杂多 Agent 辩论
9. 不做自由 ReAct 工具循环
```

---

# 五、建议文件结构

```text
career_lie_index_agent_v1/
├── run_cli.py
├── config.py
├── llm_client.py
├── graph.py
├── state_schema.py
├── prompts.py
├── agents/
│   ├── __init__.py
│   ├── information_comparison_agent.py
│   ├── strategy_feedback_agent.py
│   └── followup_dialogue_agent.py
├── nodes/
│   ├── __init__.py
│   ├── state_update_node.py
│   └── report_generation_node.py
├── memory/
│   ├── __init__.py
│   ├── fact_table.py
│   └── anomaly_table.py
├── utils/
│   ├── __init__.py
│   ├── env_utils.py
│   ├── json_utils.py
│   └── text_utils.py
└── outputs/
    ├── logs/
    └── reports/
```

说明：

```text
1. 三个 Agent 放在 agents/ 目录下。
2. 纯 Python 状态更新逻辑放在 nodes/ 目录下。
3. 事实表和异常表的辅助操作放在 memory/ 目录下。
4. 通用工具函数放在 utils/ 目录下。
```

---

# 六、全局状态 DialogueState 设计

文件：

```text
state_schema.py
```

建议使用 `TypedDict` 定义全局状态。

```python
from typing import TypedDict, List, Dict, Optional, Any


class DialogueState(TypedDict):
    # 轮次控制
    round_id: int
    max_rounds: int

    # 当前输入
    current_user_text: str

    # 历史对话
    dialogue_history: List[Dict[str, Any]]

    # Agent 2 输出：当前事实、当前异常、事实比对结果
    current_facts: List[Dict[str, Any]]
    current_anomalies: List[Dict[str, Any]]
    consistency_results: List[Dict[str, Any]]

    # 状态表
    facts_table: List[Dict[str, Any]]
    anomalies_table: List[Dict[str, Any]]
    indicator_history: List[Dict[str, Any]]

    # Agent 3 输出：策略反馈
    priority_issue: str
    followup_strategy: str
    strategy_reason: str
    next_action: str

    # Agent 1 输出：追问
    last_followup_question: str
    followup_history: List[Dict[str, Any]]

    # 谎言指数
    lie_index: int
    risk_level: str

    # 最终报告
    final_report: Optional[Dict[str, Any]]
```

---

# 七、核心数据结构

## 7.1 职业事实结构

`facts_table` 中每条事实格式：

```json
{
  "fact_id": "f001",
  "round_id": 1,
  "slot": "work_content",
  "value": "参与新能源 IPO 项目",
  "evidence": "最近主要跟一个新能源 IPO 项目",
  "time_stage": "当前",
  "confidence": "medium"
}
```

第一版只抽取以下 slot：

```text
claimed_identity：声称职业身份
job_title：岗位 / 职位
industry：行业
organization_type：机构类型
work_content：主要工作内容
work_location：工作地点
time_stage：时间阶段
career_evidence：支撑职业身份的辅助经历细节
```

要求：

```text
1. 只抽取用户明确表达的信息。
2. 不要猜测。
3. 必须保留 evidence 原文片段。
4. 如果没有明确事实，返回空列表。
```

---

## 7.2 异常表达结构

`current_anomalies` 中每条异常表达格式：

```json
{
  "indicator": "细节缺失",
  "evidence": "就客户那边的一些事情吧",
  "severity": "medium",
  "explanation": "回答较模糊，没有说明具体工作内容"
}
```

第一版识别 5 类异常表达：

```text
细节缺失
明显回避
答非所问
表达模糊
过度解释
```

注意：

```text
1. 异常表达只能作为风险线索。
2. 不能因为表达异常就直接判断用户说谎。
3. 纯文本版本不重点识别“犹豫语气明显”。
```

---

## 7.3 事实关系判断结构

`consistency_results` 中每条格式：

```json
{
  "history_fact_id": "f001",
  "current_fact_id": "f003",
  "relation": "潜在不匹配",
  "severity": "medium",
  "explanation": "第1轮说当前主要参与 IPO 项目，第3轮说主要推荐理财产品，两者都属于当前工作内容，但业务类型差异较大，需要澄清是否属于不同阶段或不同岗位内容。",
  "need_followup": true
}
```

关系类型只允许：

```text
新增事实
补充细节
与前文一致
潜在不匹配
明显冲突
无法判断
```

---

## 7.4 异常表结构

`anomalies_table` 中每条格式：

```json
{
  "anomaly_id": "a001",
  "round_id": 3,
  "type": "职业内容潜在不匹配",
  "related_fact_ids": ["f001", "f003"],
  "description": "当前工作内容前后存在潜在不匹配",
  "severity": "medium",
  "status": "unresolved",
  "evidence": [
    "第1轮：最近新能源 IPO 项目挺忙的",
    "第3轮：主要给客户推荐理财产品"
  ]
}
```

状态只允许：

```text
unresolved：待澄清
resolved：已澄清
ignored：暂不处理
```

---

# 八、三个 Agent 详细设计

---

## 8.1 Agent 2：信息比对 Agent

文件：

```text
agents/information_comparison_agent.py
```

节点函数：

```text
information_comparison_agent_node(state: DialogueState) -> dict
```

### 职责

该 Agent 负责本轮回答的全部分析工作，包括：

```text
1. 职业事实抽取
2. 异常表达识别
3. 当前事实与历史事实比对
```

### 输入

从 state 中读取：

```text
current_user_text
round_id
facts_table
last_followup_question
dialogue_history
```

### 输出

写入 state：

```text
current_facts
current_anomalies
consistency_results
```

### 输出 JSON 格式

```json
{
  "current_facts": [
    {
      "slot": "work_content",
      "value": "新能源 IPO 项目",
      "evidence": "最近主要跟一个新能源 IPO 项目",
      "time_stage": "当前",
      "confidence": "medium"
    }
  ],
  "current_anomalies": [
    {
      "indicator": "表达模糊",
      "evidence": "客户那边的一些事",
      "severity": "medium",
      "explanation": "回答较笼统，没有说明具体职责"
    }
  ],
  "consistency_results": [
    {
      "history_fact_id": "f001",
      "current_fact_temp_id": "current_001",
      "relation": "潜在不匹配",
      "severity": "medium",
      "explanation": "当前工作内容与历史职业描述存在业务类型差异，需要澄清是否属于不同阶段。",
      "need_followup": true
    }
  ]
}
```

### 实现要求

```text
1. 该 Agent 只负责分析，不负责生成追问。
2. 输出必须是 JSON。
3. 不得输出“用户在说谎”。
4. 所有判断必须引用 evidence。
5. 如果 facts_table 为空，consistency_results 中所有当前事实都标记为“新增事实”。
6. 如果当前回答没有明确事实，current_facts 返回空列表。
7. 如果没有异常表达，current_anomalies 返回空列表。
```

### Prompt 要点

写入 `prompts.py`：

```text
你是信息比对 Agent，负责分析用户职业身份叙述中的事实和表达线索。

你需要完成三件事：
1. 从当前回答中抽取职业身份相关事实；
2. 识别当前回答中的异常表达；
3. 将当前事实与历史事实表进行比对。

你只能根据用户已说出的内容判断，不得猜测。
你不能说用户在说谎，只能说存在待澄清线索。
你必须输出严格 JSON。
```

---

## 8.2 Agent 3：策略反馈 Agent

文件：

```text
agents/strategy_feedback_agent.py
```

节点函数：

```text
strategy_feedback_agent_node(state: DialogueState) -> dict
```

### 职责

该 Agent 负责根据 Agent 2 的分析结果，决定下一轮系统应该怎么追问。

### 输入

从 state 中读取：

```text
round_id
max_rounds
lie_index
risk_level
facts_table
anomalies_table
current_anomalies
consistency_results
dialogue_history
```

### 输出

写入 state：

```text
priority_issue
followup_strategy
strategy_reason
next_action
```

### followup_strategy 允许值

```text
identity_clarification：澄清职业身份
work_content_clarification：澄清工作内容
time_stage_clarification：澄清时间阶段
detail_completion：补全职业细节
avoidance_response：回应回避或模糊表达
normal_expansion：无明显异常时继续自然展开
final_summary：生成最终报告
```

### next_action 允许值

```text
generate_followup
final_report
```

### 输出 JSON 格式

```json
{
  "priority_issue": "当前工作内容与前文职业描述存在潜在不匹配",
  "followup_strategy": "time_stage_clarification",
  "strategy_reason": "第1轮提到当前做新能源 IPO，第3轮提到主要推荐理财产品，两者可能属于不同阶段，也可能是当前工作内容不一致，需要澄清时间阶段。",
  "next_action": "generate_followup"
}
```

### 路由规则

```text
1. 如果 round_id >= max_rounds，next_action 必须为 final_report。
2. 如果存在 unresolved anomaly，优先围绕 unresolved anomaly 追问。
3. 如果 consistency_results 中存在“明显冲突”，优先追问该冲突。
4. 如果 consistency_results 中存在“潜在不匹配”，优先追问该不匹配。
5. 如果当前回答存在明显回避、答非所问、表达模糊，优先要求自然补充细节。
6. 如果没有明显异常，则继续进行 normal_expansion。
```

### 实现要求

```text
1. Agent 3 不重新抽取事实。
2. Agent 3 不重新做历史比对。
3. Agent 3 只负责策略选择。
4. 输出必须是 JSON。
5. strategy_reason 要简短，不要长篇分析。
6. priority_issue 应该是一个明确可追问的问题点。
```

### Prompt 要点

写入 `prompts.py`：

```text
你是策略反馈 Agent，负责根据事实比对结果和异常表决定下一轮追问策略。

你不能重新抽取事实。
你不能重新判断所有矛盾。
你只需要判断：下一轮最应该追问什么、采用什么追问策略、是否结束对话。

如果轮次达到上限，必须生成最终报告。
如果存在未解决异常，优先追问未解决异常。
你必须输出严格 JSON。
```

---

## 8.3 Agent 1：追问对话 Agent

文件：

```text
agents/followup_dialogue_agent.py
```

节点函数：

```text
followup_dialogue_agent_node(state: DialogueState) -> dict
```

### 职责

该 Agent 负责根据 Agent 3 的策略，生成一个自然、温和、不像审问的追问问题。

### 输入

从 state 中读取：

```text
dialogue_history
facts_table
anomalies_table
priority_issue
followup_strategy
strategy_reason
last_followup_question
```

### 输出

写入 state：

```text
last_followup_question
followup_history
```

### 输出 JSON 格式

```json
{
  "question": "你刚才提到做 IPO，后面又说到推荐理财产品，我有点好奇，这两部分是现在工作里都会涉及，还是不同阶段的经历呀？"
}
```

### 追问要求

```text
1. 只生成 1 个问题。
2. 问题必须自然，像正常聊天中的好奇。
3. 不要像审问。
4. 不要连续追问多个问题。
5. 不要使用“谎言”“撒谎”“矛盾”“测谎”“核查”“审查”等词。
6. 优先围绕 priority_issue 追问。
7. 如果 followup_strategy 是 normal_expansion，则自然询问职业细节。
8. 如果 followup_strategy 是 time_stage_clarification，则重点澄清“现在 / 过去 / 实习 / 兼职 / 不同阶段”。
9. 如果 followup_strategy 是 work_content_clarification，则重点澄清“平时具体负责什么”。
10. 如果 followup_strategy 是 avoidance_response，则用温和语气引导用户正面回答。
```

### 示例

较好追问：

```text
你刚才说主要做新能源 IPO，我还挺好奇的，你平时在这个项目里主要负责哪一块呀？
```

较好追问：

```text
你前面提到现在在投行，后面又说到推荐理财产品，我想确认一下，这两部分是同一份工作里的不同内容，还是不同阶段的经历呀？
```

不允许追问：

```text
你前后说法矛盾，请解释。
```

不允许追问：

```text
你是不是在撒谎？
```

### Prompt 要点

写入 `prompts.py`：

```text
你是追问对话 Agent，负责根据策略生成一个自然追问问题。

你的问题要像正常聊天中的好奇，不要像审问。
你不能判断用户是否说谎。
你不能使用“谎言、撒谎、矛盾、测谎、核查、审查”等词。
你只能输出严格 JSON。
```

---

# 九、状态更新节点设计

文件：

```text
nodes/state_update_node.py
```

节点函数：

```text
state_update_node(state: DialogueState) -> dict
```

该节点不调用 LLM，只使用 Python 逻辑更新状态。

## 9.1 输入

```text
round_id
current_user_text
current_facts
current_anomalies
consistency_results
facts_table
anomalies_table
indicator_history
dialogue_history
lie_index
```

## 9.2 输出

```text
dialogue_history
facts_table
anomalies_table
indicator_history
lie_index
risk_level
```

## 9.3 更新逻辑

### 1. 更新 dialogue_history

加入本轮用户回答：

```json
{
  "round_id": 1,
  "role": "user",
  "content": "我现在在投行，最近主要做新能源 IPO。"
}
```

如果上一轮系统有追问，也记录系统追问：

```json
{
  "round_id": 1,
  "role": "assistant",
  "content": "你平时是做什么工作的呀？"
}
```

---

### 2. 更新 facts_table

为 `current_facts` 中每条事实生成正式 `fact_id`：

```text
f001
f002
f003
```

并写入：

```text
round_id
fact_id
slot
value
evidence
time_stage
confidence
```

---

### 3. 更新 indicator_history

将 `current_anomalies` 逐条写入历史记录。

---

### 4. 更新 anomalies_table

根据 `consistency_results` 和 `current_anomalies` 生成异常记录。

如果 relation 为：

```text
潜在不匹配
明显冲突
无法判断
```

则生成一条 `unresolved` 异常。

如果 current_anomalies 中存在：

```text
细节缺失
明显回避
答非所问
表达模糊
过度解释
```

也生成对应异常记录。

异常 ID：

```text
a001
a002
a003
```

---

### 5. 计算 lie_index

第一版使用简单规则：

```text
明显冲突 +30
潜在不匹配 +20
无法判断 +10
细节缺失 +8
明显回避 +10
答非所问 +10
表达模糊 +5
过度解释 +5
```

上限 100。

---

### 6. 计算 risk_level

```text
0-30：低
31-60：中
61-100：高
```

---

# 十、最终报告节点设计

文件：

```text
nodes/report_generation_node.py
```

节点函数：

```text
report_generation_node(state: DialogueState) -> dict
```

## 10.1 职责

根据完整状态生成最终谎言指数测评报告。

## 10.2 输入

```text
dialogue_history
facts_table
anomalies_table
indicator_history
lie_index
risk_level
```

## 10.3 输出

```text
final_report
```

## 10.4 报告内容

最终报告必须包括：

```text
1. 用户声称的职业身份概括
2. 已抽取的职业相关事实
3. 稳定一致的事实
4. 待澄清异常
5. 异常表达线索
6. 谎言指数
7. 风险等级
8. 建议后续核实方向
```

## 10.5 措辞要求

不允许说：

```text
对方在说谎
对方撒谎概率很高
```

建议说：

```text
当前职业身份叙述存在待澄清线索。
当前信息内部一致性不足。
该回答需要进一步确认时间阶段或具体职责。
```

---

# 十一、基础文件开发顺序

---

## 第 1 阶段：基础配置层

这些文件是整个项目的基础设施，不依赖其他业务代码。

| 文件路径 | 功能概括 |
|---------|---------|
| `config.py` | 保存 API 密钥、模型名、最大轮数、谎言指数权重、风险等级阈值等全局配置。 |
| `state_schema.py` | 定义 `DialogueState` 类型，说明所有节点共享的状态字段。 |
| `prompts.py` | 保存 3 个 Agent 和最终报告节点使用的 Prompt 模板。 |

---

## 第 2 阶段：工具函数层

这些文件提供通用工具函数，被其他模块调用。

| 文件路径 | 功能概括 |
|---------|---------|
| `utils/env_utils.py` | 清除 http/https 代理环境变量，避免影响阿里云百炼 API 调用。 |
| `utils/json_utils.py` | 从 LLM 响应中解析 JSON，兼容直接 JSON、代码块包裹、裸花括号三种格式。 |
| `utils/text_utils.py` | 格式化事实表、异常表、对话历史，辅助放入 Prompt。 |

---

## 第 3 阶段：LLM 调用层

依赖：`config.py`

| 文件路径 | 功能概括 |
|---------|---------|
| `llm_client.py` | 封装 LLM 调用，提供纯文本和 JSON 两种调用方式，连接阿里云百炼 deepseek-v3。 |

---

## 第 4 阶段：数据存储层

这些文件提供事实表和异常表的查询与操作函数。

| 文件路径 | 功能概括 |
|---------|---------|
| `memory/fact_table.py` | 提供按 slot、按 fact_id 查询事实，以及生成事实摘要的辅助函数。 |
| `memory/anomaly_table.py` | 提供查找未澄清异常、按 id 查找、标记已澄清、统计未解决异常等辅助函数。 |

---

## 第 5 阶段：三个 Agent 层

依赖：

```text
state_schema.py
llm_client.py
prompts.py
utils/json_utils.py
utils/text_utils.py
```

| 文件路径 | 功能概括 |
|---------|---------|
| `agents/information_comparison_agent.py` | Agent 2：抽取当前事实、识别异常表达、比对历史事实，输出结构化分析结果。 |
| `agents/strategy_feedback_agent.py` | Agent 3：根据异常表和比对结果选择下一轮追问重点与追问策略。 |
| `agents/followup_dialogue_agent.py` | Agent 1：根据策略生成一个自然、温和、不像审问的追问问题。 |

---

## 第 6 阶段：普通节点层

| 文件路径 | 功能概括 |
|---------|---------|
| `nodes/state_update_node.py` | 用 Python 更新事实表、异常表、对话历史、谎言指数和风险等级。 |
| `nodes/report_generation_node.py` | 调用 LLM 根据全部状态生成最终谎言指数测评报告。 |

---

## 第 7 阶段：工作流层

依赖：

```text
state_schema.py
agents/*
nodes/*
```

| 文件路径 | 功能概括 |
|---------|---------|
| `graph.py` | 定义 LangGraph 工作流，注册 3 个 Agent 节点、状态更新节点、报告节点和条件路由。 |

---

## 第 8 阶段：应用入口层

依赖：

```text
config.py
graph.py
utils/env_utils.py
```

| 文件路径 | 功能概括 |
|---------|---------|
| `run_cli.py` | 命令行多轮对话入口，循环接收用户输入，调用 LangGraph 工作流，展示追问、谎言指数和最终报告。 |

---

# 十二、graph.py 实现要求

文件：

```text
graph.py
```

## 12.1 注册节点

需要注册以下节点：

```text
information_comparison_agent
state_update
strategy_feedback_agent
followup_dialogue_agent
report_generation
```

## 12.2 边设计

```text
START
→ information_comparison_agent
→ state_update
→ strategy_feedback_agent
→ route_next
```

条件路由：

```text
如果 next_action == "generate_followup":
    → followup_dialogue_agent
    → END

如果 next_action == "final_report":
    → report_generation
    → END
```

## 12.3 伪代码

```python
from langgraph.graph import StateGraph, START, END
from state_schema import DialogueState
from agents.information_comparison_agent import information_comparison_agent_node
from agents.strategy_feedback_agent import strategy_feedback_agent_node
from agents.followup_dialogue_agent import followup_dialogue_agent_node
from nodes.state_update_node import state_update_node
from nodes.report_generation_node import report_generation_node


def route_next(state: DialogueState) -> str:
    if state.get("next_action") == "final_report":
        return "report_generation"
    return "followup_dialogue_agent"


def build_graph():
    graph = StateGraph(DialogueState)

    graph.add_node("information_comparison_agent", information_comparison_agent_node)
    graph.add_node("state_update", state_update_node)
    graph.add_node("strategy_feedback_agent", strategy_feedback_agent_node)
    graph.add_node("followup_dialogue_agent", followup_dialogue_agent_node)
    graph.add_node("report_generation", report_generation_node)

    graph.add_edge(START, "information_comparison_agent")
    graph.add_edge("information_comparison_agent", "state_update")
    graph.add_edge("state_update", "strategy_feedback_agent")

    graph.add_conditional_edges(
        "strategy_feedback_agent",
        route_next,
        {
            "followup_dialogue_agent": "followup_dialogue_agent",
            "report_generation": "report_generation",
        },
    )

    graph.add_edge("followup_dialogue_agent", END)
    graph.add_edge("report_generation", END)

    return graph.compile()
```

---

# 十三、run_cli.py 实现要求

文件：

```text
run_cli.py
```

## 13.1 启动要求

程序启动时必须先关闭代理：

```python
from utils.env_utils import disable_proxy

disable_proxy()
```

## 13.2 初始状态

```python
state = {
    "round_id": 1,
    "max_rounds": 5,
    "current_user_text": "",
    "dialogue_history": [],
    "current_facts": [],
    "current_anomalies": [],
    "consistency_results": [],
    "facts_table": [],
    "anomalies_table": [],
    "indicator_history": [],
    "priority_issue": "",
    "followup_strategy": "",
    "strategy_reason": "",
    "next_action": "generate_followup",
    "last_followup_question": "你平时是做什么工作的呀？",
    "followup_history": [],
    "lie_index": 0,
    "risk_level": "低",
    "final_report": None,
}
```

## 13.3 交互逻辑

```text
1. 打印系统初始问题。
2. 用户输入回答。
3. 把回答写入 current_user_text。
4. 调用 graph.invoke(state)。
5. 打印当前谎言指数、风险等级、主要追问策略。
6. 如果 next_action 是 generate_followup，打印 last_followup_question。
7. 如果 next_action 是 final_report，打印 final_report 并结束。
8. 每轮结束后 round_id += 1。
```

## 13.4 每轮输出示例

```text
系统：你平时是做什么工作的呀？

用户：我现在在投行，最近主要做新能源 IPO。

当前谎言指数：18 / 100
当前风险等级：低
当前追问策略：detail_completion
策略理由：用户提到投行和 IPO 项目，但具体职责仍不清楚。
系统追问：你平时在 IPO 项目里主要负责哪一块呀？
```

---

# 十四、Prompt 模板清单

文件：

```text
prompts.py
```

至少需要定义 4 个 Prompt：

```text
INFORMATION_COMPARISON_AGENT_PROMPT
STRATEGY_FEEDBACK_AGENT_PROMPT
FOLLOWUP_DIALOGUE_AGENT_PROMPT
REPORT_GENERATION_PROMPT
```

## 14.1 INFORMATION_COMPARISON_AGENT_PROMPT

用途：

```text
给 Agent 2 使用，完成事实抽取、异常识别、事实比对。
```

必须包含：

```text
1. 当前用户回答
2. 历史事实表
3. 上一轮系统追问
4. 允许抽取的事实 slot
5. 允许识别的异常表达类型
6. 允许输出的事实关系类型
7. JSON 输出格式
```

---

## 14.2 STRATEGY_FEEDBACK_AGENT_PROMPT

用途：

```text
给 Agent 3 使用，决定下一轮追问策略。
```

必须包含：

```text
1. 当前轮次
2. 最大轮次
3. 谎言指数
4. 风险等级
5. 异常表
6. 本轮比对结果
7. 本轮异常表达
8. 允许的 followup_strategy
9. 允许的 next_action
10. JSON 输出格式
```

---

## 14.3 FOLLOWUP_DIALOGUE_AGENT_PROMPT

用途：

```text
给 Agent 1 使用，生成自然追问。
```

必须包含：

```text
1. 对话历史
2. 当前追问重点 priority_issue
3. 追问策略 followup_strategy
4. 策略理由 strategy_reason
5. 禁用词列表
6. 只生成一个问题
7. JSON 输出格式
```

---

## 14.4 REPORT_GENERATION_PROMPT

用途：

```text
生成最终谎言指数测评报告。
```

必须包含：

```text
1. 对话历史
2. 事实表
3. 异常表
4. 异常表达历史
5. 谎言指数
6. 风险等级
7. 报告结构
8. 措辞限制
```

---

# 十五、验收标准

第一版完成后，应满足以下要求：

```text
1. 可以连续进行 3-5 轮文本对话。
2. Agent 2 能从回答中抽取职业身份相关事实。
3. Agent 2 能识别至少 5 类异常表达。
4. Agent 2 能将当前事实与历史事实进行比对。
5. state_update_node 能维护 facts_table 和 anomalies_table。
6. state_update_node 能计算谎言指数和风险等级。
7. Agent 3 能根据异常结果选择追问策略。
8. Agent 1 能生成自然、不像审问的追问。
9. 系统能在最大轮次后输出最终报告。
10. CLI 可以完整展示每轮追问、风险分和最终测评报告。
```

---

# 十六、测试样例

至少准备 12 条测试样例。

```text
1. 职业身份一致型：3 条
2. 职业内容冲突型：3 条
3. 可澄清型：3 条
4. 模糊回避型：3 条
```

## 16.1 职业身份一致型示例

```text
第1轮：我现在在一家券商投行部，最近主要跟新能源 IPO 项目。
第2轮：我主要做材料整理、底稿核对，还有一些行业资料分析。
第3轮：项目上会跟企业财务和律师沟通，整理申报材料。
```

预期：

```text
风险等级：低
主要问题：细节逐渐补充，无明显冲突
```

---

## 16.2 职业内容冲突型示例

```text
第1轮：我现在在投行做 IPO。
第2轮：我主要给客户推荐理财产品。
第3轮：反正都是金融相关，也差不多吧。
```

预期：

```text
风险等级：中或高
主要问题：当前职业内容存在潜在不匹配
追问策略：work_content_clarification 或 time_stage_clarification
```

---

## 16.3 可澄清型示例

```text
第1轮：我现在在投行做 IPO。
第2轮：我之前在银行实习的时候接触过理财产品。
第3轮：现在这份工作主要还是跟 IPO 项目。
```

预期：

```text
风险等级：低或中
主要问题：第二轮信息可以被解释为过去经历
追问策略：time_stage_clarification
```

---

## 16.4 模糊回避型示例

```text
第1轮：我做金融相关的。
第2轮：就是客户和项目那些事，挺杂的。
第3轮：这个说起来比较复杂，也没啥好细说的。
```

预期：

```text
风险等级：中
主要问题：细节缺失、表达模糊、明显回避
追问策略：detail_completion 或 avoidance_response
```

---

# 十七、依赖关系图

```text
config.py
    ↓
state_schema.py
    ↓
prompts.py
    ↓
utils/env_utils.py
utils/json_utils.py
utils/text_utils.py
    ↓
llm_client.py
    ↓
memory/fact_table.py
memory/anomaly_table.py
    ↓
agents/information_comparison_agent.py
agents/strategy_feedback_agent.py
agents/followup_dialogue_agent.py
    ↓
nodes/state_update_node.py
nodes/report_generation_node.py
    ↓
graph.py
    ↓
run_cli.py
```

---

# 十八、最终总结

本版 v1 的核心不是做复杂多 Agent 系统，而是做一个清晰、可控、可落地的三 Agent 协同系统。

最终架构可以概括为：

```text
Agent 2 信息比对
负责发现事实和异常

+
Python 状态更新
负责维护事实表、异常表和风险分

+
Agent 3 策略反馈
负责决定下一轮问什么

+
Agent 1 追问对话
负责把问题自然地问出来
```

一句话总结：

```text
本项目采用 LangGraph 有状态工作流，以共享 DialogueState 作为协同机制，将谎言指数测评拆分为“信息比对—策略反馈—自然追问”三个 Agent 协同完成。
```
