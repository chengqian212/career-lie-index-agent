"""项目配置模块：读取 .env 并提供全局配置"""

import os
from dotenv import load_dotenv

# 加载 .env
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=False)


def disable_proxy():
    """关闭系统代理，避免 API 调用被本地代理影响"""
    for key in [
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
    ]:
        os.environ.pop(key, None)


# 启动时默认关闭代理
disable_proxy()

# --- 配置项 ---
DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
BAILIAN_BASE_URL: str = os.getenv(
    "BAILIAN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
)
MODEL_NAME: str = os.getenv("MODEL_NAME", "deepseek-v4-pro")
MAX_ROUNDS: int = int(os.getenv("MAX_ROUNDS", "5"))
TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.2"))

# 风险等级阈值
RISK_LOW_THRESHOLD: int = 30
RISK_HIGH_THRESHOLD: int = 60

# 谎言指数权重
WEIGHT_SEMANTIC: float = 0.30
WEIGHT_LOGICAL: float = 0.25
WEIGHT_DOMAIN: float = 0.20
WEIGHT_PSYCHO_LINGUISTIC: float = 0.15
WEIGHT_UNRESOLVED_FOLLOWUP: float = 0.10

# Debate 触发阈值
DEBATE_SCORE_THRESHOLD: int = 75
DEBATE_SCORE_DIFF_THRESHOLD: int = 40
UNRESOLVED_FOLLOWUP_PER_SCORE: int = 20
