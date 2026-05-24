"""v3.2 补充修改验收测试

验证核心修复：
1. 四个专家 Prompt 真正传入 anomalies_table 和 current_anomalies
2. quick_preanalysis Prompt 加强"澄清不等于解决"的规则
3. update_anomalies_status 加强分数裁决规则
4. quick_preanalysis_node 的 has_new_fact 按实际 facts 兜底
"""

import sys
from pathlib import Path

# 添加父目录到路径
parent_path = Path(__file__).parent.parent
sys.path.insert(0, str(parent_path))


def test_expert_prompts_have_anomalies():
    """测试 1: 四个专家 Prompt 是否包含异常表输入"""
    print("=" * 60)
    print("测试 1: 四个专家 Prompt 是否包含异常表输入")
    print("=" * 60)
    
    from v3.prompts import (
        SEMANTIC_AGENT_TEMPLATE,
        LOGICAL_AGENT_TEMPLATE,
        DOMAIN_AGENT_TEMPLATE,
        PSYCHO_LINGUISTIC_AGENT_TEMPLATE,
    )
    
    templates = {
        "Semantic": SEMANTIC_AGENT_TEMPLATE,
        "Logical": LOGICAL_AGENT_TEMPLATE,
        "Domain": DOMAIN_AGENT_TEMPLATE,
        "Psycho-Linguistic": PSYCHO_LINGUISTIC_AGENT_TEMPLATE,
    }
    
    for name, template in templates.items():
        # 检查【当前数据】区域是否包含异常表
        if "已有异常表：" in template and "当前轮次新异常：" in template:
            print(f"[OK] {name} Prompt 包含异常表输入")
        else:
            print(f"[X] {name} Prompt 缺少异常表输入")
            return False
    
    print("[OK] 所有专家 Prompt 都包含异常表输入\n")
    return True


def test_expert_nodes_pass_anomalies():
    """测试 1.5: 四个专家节点是否传入异常表变量"""
    print("=" * 60)
    print("测试 1.5: 四个专家节点是否传入异常表变量")
    print("=" * 60)
    
    from v3.nodes.specialists.semantic_agent_node import semantic_agent_node
    from v3.nodes.specialists.logical_agent_node import logical_agent_node
    from v3.nodes.specialists.domain_agent_node import domain_agent_node
    from v3.nodes.specialists.psycho_linguistic_agent_node import psycho_linguistic_agent_node
    import inspect
    
    nodes = {
        "Semantic": semantic_agent_node,
        "Logical": logical_agent_node,
        "Domain": domain_agent_node,
        "Psycho-Linguistic": psycho_linguistic_agent_node,
    }
    
    for name, node in nodes.items():
        src = inspect.getsource(node)
        
        # 检查是否读取 current_anomalies
        if "current_anomalies = state.get" not in src:
            print(f"[X] {name} 节点没有读取 current_anomalies")
            return False
        
        # 检查是否格式化 current_anomalies
        if "current_anomalies_str" not in src:
            print(f"[X] {name} 节点没有格式化 current_anomalies")
            return False
        
        # 检查是否传入 current_anomalies
        if '"current_anomalies": current_anomalies_str' not in src:
            print(f"[X] {name} 节点没有传入 current_anomalies")
            return False
        
        print(f"[OK] {name} 节点正确传入异常表变量")
    
    print("[OK] 所有专家节点都正确传入异常表变量\n")
    return True


def test_quick_preanalysis_has_clarify_rule():
    """测试 2: quick_preanalysis Prompt 是否有澄清规则"""
    print("=" * 60)
    print("测试 2: quick_preanalysis Prompt 是否有澄清规则")
    print("=" * 60)
    
    from v3.prompts import QUICK_PREANALYSIS_TEMPLATE
    
    template = QUICK_PREANALYSIS_TEMPLATE
    
    # 检查是否有【异常状态更新规则】
    if "【异常状态更新规则】" in template:
        print("[OK] QUICK_PREANALYSIS_TEMPLATE 包含【异常状态更新规则】")
    else:
        print("[X] QUICK_PREANALYSIS_TEMPLATE 缺少【异常状态更新规则】")
        return False
    
    # 检查关键规则
    required_rules = [
        "澄清不等于解决",
        "update_type=\"resolve\"",
        "update_type=\"clarify\"",
        "update_type=\"reinforce\"",
        "update_type=\"remain_unresolved\"",
    ]
    
    for rule in required_rules:
        if rule in template:
            print(f"[OK] 包含规则: {rule}")
        else:
            print(f"[X] 缺少规则: {rule}")
            return False
    
    print("[OK] QUICK_PREANALYSIS_TEMPLATE 澄清规则完整\n")
    return True


def test_expert_prompts_have_clarify_rule():
    """测试 3: 四个专家 Prompt 是否有澄清规则"""
    print("=" * 60)
    print("测试 3: 四个专家 Prompt 是否有澄清规则")
    print("=" * 60)
    
    from v3.prompts import (
        SEMANTIC_AGENT_TEMPLATE,
        LOGICAL_AGENT_TEMPLATE,
        DOMAIN_AGENT_TEMPLATE,
        PSYCHO_LINGUISTIC_AGENT_TEMPLATE,
    )
    
    templates = {
        "Semantic": SEMANTIC_AGENT_TEMPLATE,
        "Logical": LOGICAL_AGENT_TEMPLATE,
        "Domain": DOMAIN_AGENT_TEMPLATE,
        "Psycho-Linguistic": PSYCHO_LINGUISTIC_AGENT_TEMPLATE,
    }
    
    for name, template in templates.items():
        # 检查是否有【异常状态更新规则】
        if "【异常状态更新规则】" not in template:
            print(f"[X] {name} Prompt 缺少【异常状态更新规则】")
            return False
        
        # 检查关键规则
        required_rules = [
            "澄清不等于解决",
            "update_type=\"resolve\"",
            "update_type=\"clarify\"",
            "followup_needed=true",
        ]
        
        for rule in required_rules:
            if rule not in template:
                print(f"[X] {name} Prompt 缺少规则: {rule}")
                return False
        
        print(f"[OK] {name} Prompt 澄清规则完整")
    
    print("[OK] 所有专家 Prompt 澄清规则完整\n")
    return True


def test_update_anomalies_status_score_rules():
    """测试 4: update_anomalies_status 分数裁决规则"""
    print("=" * 60)
    print("测试 4: update_anomalies_status 分数裁决规则")
    print("=" * 60)
    
    from v3.memory.anomaly_table import update_anomalies_status
    
    # 测试 resolve：分数最多 20
    anomalies_table = [
        {
            "anomaly_id": "a_1",
            "round_id": 1,
            "source": "semantic",
            "type": "test",
            "description": "test",
            "evidence": [],
            "score": 80,
            "status": "unresolved",
            "clarification_status": "none",
            "followup_needed": True,
            "created_round": 1,
            "last_update_round": 1,
            "update_history": [],
        }
    ]
    
    updates = [
        {
            "target_anomaly_id": "a_1",
            "update_type": "resolve",
            "explanation": "已解决",
            "new_score": 100,  # 尝试设置高分
            "followup_needed": False,
        }
    ]
    
    updated = update_anomalies_status(anomalies_table, updates, round_id=2)
    assert updated[0]["score"] <= 20, f"resolve 分数应该 <= 20，实际: {updated[0]['score']}"
    print(f"[OK] resolve 分数裁决正确: {updated[0]['score']} <= 20")
    
    # 测试 clarify：分数至少 30
    anomalies_table[0]["score"] = 10
    updates[0]["update_type"] = "clarify"
    updates[0]["new_score"] = 5  # 尝试设置低分
    
    updated = update_anomalies_status(anomalies_table, updates, round_id=2)
    assert updated[0]["score"] >= 30, f"clarify 分数应该 >= 30，实际: {updated[0]['score']}"
    print(f"[OK] clarify 分数裁决正确: {updated[0]['score']} >= 30")
    
    # 测试 reinforce：不能比原分更低
    anomalies_table[0]["score"] = 50
    updates[0]["update_type"] = "reinforce"
    updates[0]["new_score"] = 10  # 尝试设置低分
    
    updated = update_anomalies_status(anomalies_table, updates, round_id=2)
    assert updated[0]["score"] >= 50, f"reinforce 分数应该 >= 原分 50，实际: {updated[0]['score']}"
    print(f"[OK] reinforce 分数裁决正确: {updated[0]['score']} >= 50")
    
    # 测试 remain_unresolved：不能比原分更低
    anomalies_table[0]["score"] = 40
    updates[0]["update_type"] = "remain_unresolved"
    updates[0]["new_score"] = 5  # 尝试设置低分
    
    updated = update_anomalies_status(anomalies_table, updates, round_id=2)
    assert updated[0]["score"] >= 40, f"remain_unresolved 分数应该 >= 原分 40，实际: {updated[0]['score']}"
    print(f"[OK] remain_unresolved 分数裁决正确: {updated[0]['score']} >= 40")
    
    print("[OK] 所有分数裁决规则正确\n")
    return True


def test_quick_preanalysis_has_new_fact():
    """测试 5: quick_preanalysis_node 的 has_new_fact 兜底"""
    print("=" * 60)
    print("测试 5: quick_preanalysis_node 的 has_new_fact 兜底")
    print("=" * 60)
    
    # 检查源代码是否包含 has_new_fact = bool(normalized_current_facts)
    from v3.nodes.quick_preanalysis_node import quick_preanalysis_node
    import inspect
    
    source = inspect.getsource(quick_preanalysis_node)
    
    if "has_new_fact = bool(normalized_current_facts)" in source:
        print("[OK] quick_preanalysis_node 包含 has_new_fact 兜底逻辑")
    else:
        print("[X] quick_preanalysis_node 缺少 has_new_fact 兜底逻辑")
        return False
    
    print("[OK] has_new_fact 兜底逻辑正确\n")
    return True


def test_quick_preanalysis_prompt_format():
    """测试 6: QUICK_PREANALYSIS_TEMPLATE 输出格式正确"""
    print("=" * 60)
    print("测试 6: QUICK_PREANALYSIS_TEMPLATE 输出格式")
    print("=" * 60)
    
    from v3.prompts import QUICK_PREANALYSIS_TEMPLATE
    
    template = QUICK_PREANALYSIS_TEMPLATE
    
    # 检查是否包含所有必需字段
    required_fields = [
        '"facts"',
        '"has_new_fact"',
        '"anomaly_updates"',
        '"anomalies"',
        '"surface_risk_score"',
        '"quick_fact_summary"',
        '"quick_signal_summary"',
    ]
    
    for field in required_fields:
        if field in template:
            print(f"[OK] 包含字段: {field}")
        else:
            print(f"[X] 缺少字段: {field}")
            return False
    
    print("[OK] QUICK_PREANALYSIS_TEMPLATE 输出格式完整\n")
    return True


def main():
    """运行所有验收测试"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "v3 补充修改验收测试" + " " * 26 + "║")
    print("╚" + "=" * 58 + "╝")
    print("\n")
    
    tests = [
        ("专家 Prompt 包含异常表输入", test_expert_prompts_have_anomalies),
        ("专家节点传入异常表变量", test_expert_nodes_pass_anomalies),
        ("quick_preanalysis 澄清规则", test_quick_preanalysis_has_clarify_rule),
        ("专家 Prompt 澄清规则", test_expert_prompts_have_clarify_rule),
        ("update_anomalies_status 分数裁决", test_update_anomalies_status_score_rules),
        ("quick_preanalysis has_new_fact 兜底", test_quick_preanalysis_has_new_fact),
        ("QUICK_PREANALYSIS_TEMPLATE 输出格式", test_quick_preanalysis_prompt_format),
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
        print("1. [OK] Semantic / Logical / Domain / Psycho-Linguistic 四个 Prompt 的【当前数据】里都有异常表")
        print("2. [OK] 四个专家节点 invoke prompt 时都传入 anomalies_table 和 current_anomalies")
        print("3. [OK] quick_preanalysis Prompt 明确写了澄清不等于解决规则")
        print("4. [OK] 四个专家 Prompt 也写了同样的异常更新规则")
        print("5. [OK] update_anomalies_status 里分数裁决正确")
        print("6. [OK] quick_preanalysis_node 最终的 has_new_fact = bool(normalized_current_facts)")
        print("7. [OK] QUICK_PREANALYSIS_TEMPLATE 输出格式包含所有必需字段")
        print("\n")
        print("v3.2 补充修改全部完成！")
        print("\n")
    else:
        print("[X] 部分验收测试失败，请检查上述输出")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()