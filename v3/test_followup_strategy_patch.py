"""追问策略优化验收测试

验证核心修复：
1. FOLLOWUP_GENERATION_TEMPLATE 包含追问深度边界和 6 个允许策略
2. LIGHTWEIGHT_ROUTING_SUPERVISOR_TEMPLATE 包含 6 个允许策略
3. followup_generation_node.py 有 ALLOWED_FOLLOWUP_STRATEGIES 常量
4. lightweight_routing_supervisor_node.py 有 ALLOWED_FOLLOWUP_STRATEGIES 常量
5. 旧策略词不再作为实际返回值出现
"""

import sys
import re
from pathlib import Path

# 添加父目录到路径
parent_path = Path(__file__).parent.parent
sys.path.insert(0, str(parent_path))


def test_followup_prompt_has_depth_boundary():
    """测试 1: FOLLOWUP_GENERATION_TEMPLATE 包含追问深度边界"""
    print("=" * 60)
    print("测试 1: FOLLOWUP_GENERATION_TEMPLATE 包含追问深度边界")
    print("=" * 60)

    from v3.prompts import FOLLOWUP_GENERATION_TEMPLATE

    template = FOLLOWUP_GENERATION_TEMPLATE

    required_keywords = [
        "追问深度边界",
        "不是工作面试",
        "专业考试",
        "背景调查",
        "不能直接暴露给用户",
        "priority_issue",
    ]

    all_ok = True
    for kw in required_keywords:
        if kw in template:
            print(f"[OK] 包含: {kw}")
        else:
            print(f"[X] 缺少: {kw}")
            all_ok = False

    if all_ok:
        print("[OK] FOLLOWUP_GENERATION_TEMPLATE 追问深度边界完整\n")
    else:
        print("[X] FOLLOWUP_GENERATION_TEMPLATE 追问深度边界不完整\n")

    return all_ok


def test_followup_prompt_has_six_strategies():
    """测试 2: FOLLOWUP_GENERATION_TEMPLATE 包含 6 个允许策略"""
    print("=" * 60)
    print("测试 2: FOLLOWUP_GENERATION_TEMPLATE 包含 6 个允许策略")
    print("=" * 60)

    from v3.prompts import FOLLOWUP_GENERATION_TEMPLATE

    template = FOLLOWUP_GENERATION_TEMPLATE

    allowed = [
        "daily_routine",
        "entry_experience",
        "work_style",
        "recent_memory",
        "light_clarification",
        "topic_shift_buffer",
    ]

    all_ok = True
    for s in allowed:
        if s in template:
            print(f"[OK] 包含策略: {s}")
        else:
            print(f"[X] 缺少策略: {s}")
            all_ok = False

    if all_ok:
        print("[OK] FOLLOWUP_GENERATION_TEMPLATE 6 个策略完整\n")
    else:
        print("[X] FOLLOWUP_GENERATION_TEMPLATE 策略不完整\n")

    return all_ok


def test_routing_prompt_has_six_strategies():
    """测试 3: LIGHTWEIGHT_ROUTING_SUPERVISOR_TEMPLATE 包含 6 个允许策略"""
    print("=" * 60)
    print("测试 3: LIGHTWEIGHT_ROUTING_SUPERVISOR_TEMPLATE 包含 6 个允许策略")
    print("=" * 60)

    from v3.prompts import LIGHTWEIGHT_ROUTING_SUPERVISOR_TEMPLATE

    template = LIGHTWEIGHT_ROUTING_SUPERVISOR_TEMPLATE

    allowed = [
        "daily_routine",
        "entry_experience",
        "work_style",
        "recent_memory",
        "light_clarification",
        "topic_shift_buffer",
    ]

    all_ok = True
    for s in allowed:
        if s in template:
            print(f"[OK] 包含策略: {s}")
        else:
            print(f"[X] 缺少策略: {s}")
            all_ok = False

    if all_ok:
        print("[OK] LIGHTWEIGHT_ROUTING_SUPERVISOR_TEMPLATE 6 个策略完整\n")
    else:
        print("[X] LIGHTWEIGHT_ROUTING_SUPERVISOR_TEMPLATE 策略不完整\n")

    return all_ok


def test_node_files_have_allowed_strategies():
    """测试 4: 两个 node 文件都有 ALLOWED_FOLLOWUP_STRATEGIES"""
    print("=" * 60)
    print("测试 4: 两个 node 文件都有 ALLOWED_FOLLOWUP_STRATEGIES")
    print("=" * 60)

    import inspect
    import v3.nodes.followup_generation_node as followup_module
    import v3.nodes.lightweight_routing_supervisor_node as routing_module

    all_ok = True

    # 检查 followup_generation_node.py 模块源码
    src_followup = inspect.getsource(followup_module)
    if "ALLOWED_FOLLOWUP_STRATEGIES" in src_followup:
        print("[OK] followup_generation_node.py 包含 ALLOWED_FOLLOWUP_STRATEGIES")
    else:
        print("[X] followup_generation_node.py 缺少 ALLOWED_FOLLOWUP_STRATEGIES")
        all_ok = False

    # 检查 lightweight_routing_supervisor_node.py 模块源码
    src_routing = inspect.getsource(routing_module)
    if "ALLOWED_FOLLOWUP_STRATEGIES" in src_routing:
        print("[OK] lightweight_routing_supervisor_node.py 包含 ALLOWED_FOLLOWUP_STRATEGIES")
    else:
        print("[X] lightweight_routing_supervisor_node.py 缺少 ALLOWED_FOLLOWUP_STRATEGIES")
        all_ok = False

    if all_ok:
        print("[OK] 两个 node 文件都包含 ALLOWED_FOLLOWUP_STRATEGIES\n")
    else:
        print("[X] 部分 node 文件缺少 ALLOWED_FOLLOWUP_STRATEGIES\n")

    return all_ok


def test_no_old_strategies_as_return_values():
    """测试 5: 禁止旧策略作为实际返回值

    检查 followup_generation_node.py 和 lightweight_routing_supervisor_node.py
    中不再将旧策略作为 followup_strategy 的返回值。

    注意：这些词可以出现在 prompt 的"禁止项"或注释中，
    但不应该作为 followup_strategy 的实际赋值出现。
    """
    print("=" * 60)
    print("测试 5: 禁止旧策略作为实际返回值")
    print("=" * 60)

    import inspect
    import v3.nodes.followup_generation_node as followup_module
    import v3.nodes.lightweight_routing_supervisor_node as routing_module

    old_strategies = ["deep_dive", "expansion", "continue", "clarification", "general"]

    all_ok = True

    # 检查 followup_generation_node.py 源码
    combined_followup = inspect.getsource(followup_module)

    for old in old_strategies:
        # 匹配类似 '"deep_dive"' 或 '"clarification"' 作为字符串返回值的模式
        # 排除注释行（以 # 开头）
        lines = combined_followup.split("\n")
        found_in_code = False
        for line in lines:
            stripped = line.strip()
            # 跳过注释行
            if stripped.startswith("#"):
                continue
            # 检查是否作为字符串值出现（引号包裹）
            if f'"{old}"' in stripped or f"'{old}'" in stripped:
                found_in_code = True
                break

        if found_in_code:
            print(f"[X] followup_generation_node.py 中仍使用旧策略: {old}")
            all_ok = False
        else:
            print(f"[OK] followup_generation_node.py 未使用旧策略: {old}")

    # 检查 lightweight_routing_supervisor_node.py 源码
    src_routing = inspect.getsource(routing_module)

    for old in old_strategies:
        lines = src_routing.split("\n")
        found_in_code = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if f'"{old}"' in stripped or f"'{old}'" in stripped:
                found_in_code = True
                break

        if found_in_code:
            print(f"[X] lightweight_routing_supervisor_node.py 中仍使用旧策略: {old}")
            all_ok = False
        else:
            print(f"[OK] lightweight_routing_supervisor_node.py 未使用旧策略: {old}")

    if all_ok:
        print("[OK] 旧策略不再作为实际返回值\n")
    else:
        print("[X] 部分旧策略仍作为返回值使用\n")

    return all_ok


def main():
    """运行所有验收测试"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 8 + "追问策略优化验收测试" + " " * 26 + "║")
    print("╚" + "=" * 58 + "╝")
    print("\n")

    tests = [
        ("FOLLOWUP_GENERATION_TEMPLATE 包含追问深度边界", test_followup_prompt_has_depth_boundary),
        ("FOLLOWUP_GENERATION_TEMPLATE 包含 6 个策略", test_followup_prompt_has_six_strategies),
        ("LIGHTWEIGHT_ROUTING_SUPERVISOR_TEMPLATE 包含 6 个策略", test_routing_prompt_has_six_strategies),
        ("两个 node 文件都有 ALLOWED_FOLLOWUP_STRATEGIES", test_node_files_have_allowed_strategies),
        ("禁止旧策略作为实际返回值", test_no_old_strategies_as_return_values),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n[X] 测试出错: {name} - {e}\n")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    print("=" * 60)
    print("验收测试结果汇总")
    print("=" * 60)

    all_passed = True
    for name, result in results:
        status = "[OK]" if result else "[X]"
        print(f"{status} {name}")
        if not result:
            all_passed = False

    print("=" * 60)
    if all_passed:
        print("[OK] 所有验收测试通过！")
        print("=" * 60)
        print("\n")
        print("验收标准检查：")
        print("1. [OK] FOLLOWUP_GENERATION_TEMPLATE 包含追问深度边界")
        print("2. [OK] FOLLOWUP_GENERATION_TEMPLATE 包含 6 个允许策略")
        print("3. [OK] LIGHTWEIGHT_ROUTING_SUPERVISOR_TEMPLATE 包含 6 个允许策略")
        print("4. [OK] 两个 node 文件都有 ALLOWED_FOLLOWUP_STRATEGIES")
        print("5. [OK] 旧策略不再作为实际返回值")
        print("\n")
        print("追问策略优化修改全部完成！")
        print("后台可以严肃判断职业一致性风险，前台必须像相亲聊天一样轻轻问。")
        print("\n")
    else:
        print("[X] 部分验收测试失败，请检查上述输出")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
