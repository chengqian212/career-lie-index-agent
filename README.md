# Career Lie Index Agent

基于 LangGraph 的多 Agent 谎言指数测评系统，面向交友聊天场景，围绕用户对职业身份的多轮叙述进行内部一致性分析，输出可解释的谎言指数。

## 项目结构

```
career-lie-index-agent/
├── v1/                  ← 第一版：单链路工作流
├── v2/                  ← 第二版：多 Agent 协同 + Debate 机制
├── .gitignore
└── README.md
```

## V1 — 单链路工作流

基于 LangGraph 的职业身份谎言指数测评系统，采用串行工作流：

```
用户回答 → 事实抽取 → 异常表达识别 → 历史事实比对 → 状态更新 → 自然追问/最终报告
```

### 核心能力

- 职业身份相关事实抽取
- 事实历史记录与一致性比对
- 异常表达识别（细节缺失、回避、答非所问、模糊、过度解释）
- 谎言指数计算（规则加权）
- 自然追问生成
- 最终测评报告

### 运行

```bash
cd v1
pip install -r requirements.txt
# 在 v1/ 目录下创建 .env 文件，填入 API Key
python run_cli.py
```

## V2 — 多 Agent 协同 + Debate 机制

在 V1 基础上升级，引入多 Agent 并行分析与轻量争议讨论机制：

```
用户回答
  → V1 基础节点（事实抽取、异常识别、一致性判断、状态更新）
  → 4 个 Specialist Agent 并行分析
    - Semantic Agent：语义一致性
    - Logical Agent：逻辑与时间线
    - Domain Agent：职业常识
    - Psycho-Linguistic Agent：心理语言学线索
  → Debate Gate（争议检测）
  → Debate Node（结构化争议汇总，按需触发）
  → Risk Aggregator（维度加权谎言指数）
  → Strategy Supervisor（策略决策）
  → 自然追问 / 最终报告
```

### 核心升级

- **多 Agent 并行分析**：4 个 Specialist Agent 从不同维度评分
- **Debate 机制**：分数分歧大时触发结构化争议讨论
- **可解释维度评分**：语义、逻辑、领域、心理语言学、未澄清异常
- **谎言指数聚合**：加权公式 + Debate 调整

### 运行

```bash
cd v2
pip install -r requirements.txt
# 在 v2/ 目录下创建 .env 文件，填入 API Key
python run_cli.py
```

### 环境变量

在 `v2/` 目录下创建 `.env` 文件：

```env
DASHSCOPE_API_KEY=你的阿里云百炼API_KEY
BAILIAN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_NAME=deepseek-v4-pro
MAX_ROUNDS=5
TEMPERATURE=0.2
```

## 技术栈

- Python 3.10+
- LangGraph
- LangChain Core
- 阿里云百炼 DeepSeek-V4-Pro（OpenAI-compatible API）
- python-dotenv / pydantic

## 注意事项

- 系统不做外部联网核查，不判定"对方一定在说谎"
- 仅根据对话内部信息分析职业身份叙述的一致性
- 启动时默认关闭系统代理，避免 API 调用受影响
