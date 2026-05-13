"""
全局配置：保存 API 密钥、模型名、谎言指数权重、风险等级阈值等常量。
调用关系：被 llm_client.py、state_update_node.py、run_cli.py 引用。
输入：无
输出：API_KEY, BASE_URL, MODEL_NAME, MAX_ROUNDS, LIE_INDEX_WEIGHTS, LIE_INDEX_MAX, RISK_LEVELS
"""

# 阿里云百炼 API 配置
API_KEY = "sk-7e4f567862e84ab2ab8936bf21d657e3"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL_NAME = "deepseek-v4-pro"

# 对话轮数
MAX_ROUNDS = 5

# 谎言指数权重
LIE_INDEX_WEIGHTS = {
    "明显冲突": 30,
    "潜在不匹配": 20,
    "无法判断": 10,
    "细节缺失": 8,
    "明显回避": 10,
    "答非所问": 10,
    "表达模糊": 5,
    "过度解释": 5,
}

# 谎言指数上限
LIE_INDEX_MAX = 100

# 风险等级阈值
RISK_LEVELS = {
    "低": (0, 30),
    "中": (31, 60),
    "高": (61, 100),
}
