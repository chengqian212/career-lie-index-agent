"""
代理关闭工具：清除 http/https 代理环境变量，避免影响阿里云百炼 API 调用。
调用关系：被 run_cli.py 在启动时调用。
输入：无
输出：disable_proxy() 函数
"""
import os


def disable_proxy():
    """清除代理环境变量，避免影响阿里云百炼 API 调用"""
    proxy_keys = [
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
    ]
    for key in proxy_keys:
        os.environ.pop(key, None)

    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"
