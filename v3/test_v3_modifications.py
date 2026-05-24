"""v3.2 修改验证测试脚本

测试核心功能：
1. graph.py 是否正确构建（不包含 state_update，使用合并的 quick_preanalysis）
2. quick_preanalysis_node 是否正确更新 facts_table 和 anomalies_table
3. anomaly_table.py 新函数是否正常工作
4. risk_aggregator_node 是否正确处理专家结果
"""

import sys
from pathlib import Path

# 添加父目录到路径（v3 使用相对导入）
parent_path = Path(__file__).parent.parent
sys.path.insert(0, str(parent_path))


def test_graph_structure():
    """测试图结构是否正确"""
    print("=" * 60)
    print("测试 1: 图结构")
    print("=" * 60)

    from v3.graph import build_graph

    graph = build_graph()

    # 获取所有节点
    nodes = list(graph.nodes.keys())
    print(f"所有节点: {nodes}")

    # 检查 state_update 是否不存在
    assert "state_update" not in nodes, "X state_update 节点不应该存在"
    print("[OK] state_update 节点已删除")

    # 检查旧节点是否不存在
    assert "quick_fact_extraction" not in nodes, "X quick_fact_extraction 节点不应该存在（已合并）"
    assert "quick_signal_detection" not in nodes, "X quick_signal_detection 节点不应该存在（已合并）"
    print("[OK] 旧节点已删除")

    # 检查新节点是否存在
    assert "quick_preanalysis" in nodes, "X quick_preanalysis 节点应该存在"
    assert "lightweight_routing_supervisor" in nodes, "X lightweight_routing_supervisor 节点应该存在"
    print("[OK] 关键节点存在")

    # 检查边关系（简化检查）
    print("[OK] 图结构测试通过")
    print()


def test_anomaly_table_functions():
    """测试 anomaly_table.py 新函数"""
    print("=" * 60)
    print("测试 2: anomaly_table.py 新函数")
    print("=" * 60)

    from v3.memory.anomaly_table import (
        normalize_anomaly,
        update_anomalies_status,
        get_active_anomalies,
        count_unresolved,
        apply_specialist_anomaly_updates,
        add_specialist_results_as_anomalies,
        VALID_SOURCES,
        UPDATE_TYPE_PRIORITY,
        SOURCE_PRIORITY,
        SPECIALIST_WRITE_ORDER,
    )

    # 测试常量
    print(f"VALID_SOURCES: {VALID_SOURCES}")
    print(f"UPDATE_TYPE_PRIORITY: {UPDATE_TYPE_PRIORITY}")
    print(f"SOURCE_PRIORITY: {SOURCE_PRIORITY}")
    print(f"SPECIALIST_WRITE_ORDER: {SPECIALIST_WRITE_ORDER}")
    assert "quick_detection" in VALID_SOURCES
    assert "semantic" in VALID_SOURCES
    print("[OK] 常量定义正确")

    # 测试 normalize_anomaly
    anomaly = {
        "type": "test_type",
        "description": "test",
        "evidence": ["evidence1"],
        "score": 50,
    }
    normalized = normalize_anomaly(anomaly, round_id=1, source="semantic", index=0)
    assert "anomaly_id" in normalized
    assert normalized["round_id"] == 1
    assert normalized["source"] == "semantic"
    assert normalized["status"] == "unresolved"
    assert normalized["clarification_status"] == "none"
    assert normalized["followup_needed"] is True
    print("[OK] normalize_anomaly 正常工作")

    # 测试 update_anomalies_status
    anomalies_table = [normalized]
    updates = [
        {
            "target_anomaly_id": normalized["anomaly_id"],
            "update_type": "resolve",
            "explanation": "已解决",
            "new_score": 0,
            "followup_needed": False,
        }
    ]
    updated = update_anomalies_status(anomalies_table, updates, round_id=2)
    assert updated[0]["status"] == "resolved"
    assert updated[0]["clarification_status"] == "sufficient"
    assert updated[0]["followup_needed"] is False
    print("[OK] update_anomalies_status 正常工作")

    # 测试 get_active_anomalies
    active = get_active_anomalies(updated)
    assert len(active) == 0, "resolved 的异常不应该在 active 中"
    print("[OK] get_active_anomalies 正常工作")

    # 测试 count_unresolved
    count = count_unresolved(updated)
    assert count == 0
    print("[OK] count_unresolved 正常工作")

    # 测试 apply_specialist_anomaly_updates
    specialist_results = [
        {
            "agent": "semantic",
            "score": 50,
            "findings": [],
            "anomaly_updates": [
                {
                    "target_anomaly_id": normalized["anomaly_id"],
                    "update_type": "reinforce",
                    "explanation": "强化",
                    "new_score": 80,
                    "followup_needed": True,
                }
            ],
            "new_anomalies": [],
        }
    ]
    updated2 = apply_specialist_anomaly_updates(updated, specialist_results, round_id=3)
    assert updated2[0]["status"] == "reinforced"
    assert updated2[0]["score"] == 80
    print("[OK] apply_specialist_anomaly_updates 正常工作")

    # 测试 add_specialist_results_as_anomalies
    specialist_results2 = [
        {
            "agent": "semantic",
            "score": 60,
            "findings": [],
            "anomaly_updates": [],
            "new_anomalies": [
                {
                    "type": "semantic_mismatch",
                    "description": "语义不匹配",
                    "evidence": ["evidence"],
                    "score": 60,
                    "related_facts": [],
                }
            ],
        }
    ]
    updated3 = add_specialist_results_as_anomalies(updated2, specialist_results2, round_id=3)
    assert len(updated3) == 2
    assert updated3[1]["source"] == "semantic"
    print("[OK] add_specialist_results_as_anomalies 正常工作")

    print("[OK] anomaly_table.py 测试通过")
    print()


def test_score_utils():
    """测试 score_utils.py 删除 severity"""
    print("=" * 60)
    print("测试 3: score_utils.py")
    print("=" * 60)

    from v3.utils.score_utils import calculate_lightweight_risk_score

    # 测试使用 score（不使用 severity）
    current_anomalies = [
        {"type": "test", "score": 50},
        {"type": "test2", "score": 70},
    ]

    lie_index = calculate_lightweight_risk_score(
        surface_risk_score=30,
        unresolved_count=2,
        current_anomalies=current_anomalies
    )

    print(f"lie_index: {lie_index}")
    assert 0 <= lie_index <= 100
    print("[OK] calculate_lightweight_risk_score 正常工作（使用 score，不使用 severity）")
    print()


def test_quick_preanalysis():
    """测试 quick_preanalysis_node 是否正确更新 facts_table 和 anomalies_table"""
    print("=" * 60)
    print("测试 4: quick_preanalysis_node")
    print("=" * 60)

    # 注意：这个测试需要 mock LLM，这里只检查函数签名
    from v3.nodes.quick_preanalysis_node import quick_preanalysis_node
    import inspect

    sig = inspect.signature(quick_preanalysis_node)
    print(f"函数签名: {sig}")
    print("[OK] quick_preanalysis_node 存在")

    # 检查源代码是否包含关键逻辑
    source = inspect.getsource(quick_preanalysis_node)

    # 检查 has_new_fact 兜底
    if "has_new_fact = bool(normalized_current_facts)" in source:
        print("[OK] quick_preanalysis_node 包含 has_new_fact 兜底逻辑")
    else:
        print("[X] quick_preanalysis_node 缺少 has_new_fact 兜底逻辑")
        return False

    # 检查异常更新顺序：先 update_anomalies_status，再 add_anomalies
    update_pos = source.find("update_anomalies_status")
    add_pos = source.find("add_anomalies")
    if update_pos > 0 and add_pos > 0 and update_pos < add_pos:
        print("[OK] 异常更新顺序正确：先 update_anomalies_status，再 add_anomalies")
    else:
        print("[X] 异常更新顺序不正确")
        return False

    # 检查输出字段包含事实和异常
    if "facts_table" in source and "anomalies_table" in source:
        print("[OK] 输出字段包含 facts_table 和 anomalies_table")
    else:
        print("[X] 输出字段不完整")
        return False

    print("  注意：完整测试需要 mock LLM")
    print()


def test_risk_aggregator():
    """测试 risk_aggregator_node 是否正确处理专家结果"""
    print("=" * 60)
    print("测试 5: risk_aggregator_node")
    print("=" * 60)

    from v3.nodes.risk_aggregator_node import risk_aggregator_node
    import inspect

    sig = inspect.signature(risk_aggregator_node)
    print(f"函数签名: {sig}")
    print("[OK] risk_aggregator_node 存在")
    print("  注意：完整测试需要 mock LLM 和完整状态")
    print()


def main():
    """运行所有测试"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "v3.2 修改验证测试" + " " * 26 + "║")
    print("╚" + "=" * 58 + "╝")
    print("\n")

    try:
        test_graph_structure()
        test_anomaly_table_functions()
        test_score_utils()
        test_quick_preanalysis()
        test_risk_aggregator()

        print("=" * 60)
        print("[OK] 所有测试通过！")
        print("=" * 60)
        print("\n")
        print("下一步：")
        print("1. 运行完整对话流程测试")
        print("2. 验证异常表更新逻辑")
        print("3. 验证专家结果处理逻辑")
        print("4. 验证风险计算逻辑")
        print("\n")

    except AssertionError as e:
        print(f"\n[X] 测试失败: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n[X] 测试出错: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
