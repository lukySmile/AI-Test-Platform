#!/usr/bin/env python3
"""
AI测试平台 - 真实API测试示例

使用 JSONPlaceholder (https://jsonplaceholder.typicode.com) 进行测试
这是一个免费的在线REST API，用于测试和原型开发
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.test_runner import TestRunner, TestRunConfig
from executors.api_executor import APITestExecutor


def test_with_predefined_cases():
    """使用预定义的测试用例测试JSONPlaceholder API"""

    print("=" * 60)
    print("🚀 测试JSONPlaceholder API")
    print("=" * 60)

    # JSONPlaceholder API的测试用例
    test_cases = {
        "api_name": "JSONPlaceholder API",
        "base_url": "https://jsonplaceholder.typicode.com",
        "test_cases": [
            # 1. 获取所有帖子
            {
                "id": "API_001",
                "title": "获取所有帖子",
                "method": "GET",
                "endpoint": "/posts",
                "expected_status": 200,
                "expected_response": {
                    "assertions": [
                        {"path": "$[0].id", "operator": "exists"},
                        {"path": "$[0].title", "operator": "exists"},
                        {"path": "$[0].userId", "operator": "exists"},
                    ]
                },
                "category": "正向测试",
                "priority": "P0"
            },
            # 2. 获取单个帖子
            {
                "id": "API_002",
                "title": "获取单个帖子 (ID=1)",
                "method": "GET",
                "endpoint": "/posts/1",
                "expected_status": 200,
                "expected_response": {
                    "assertions": [
                        {"path": "$.id", "operator": "equals", "value": 1},
                        {"path": "$.userId", "operator": "exists"},
                        {"path": "$.title", "operator": "exists"},
                        {"path": "$.body", "operator": "exists"},
                    ]
                },
                "category": "正向测试",
                "priority": "P0"
            },
            # 3. 获取不存在的帖子
            {
                "id": "API_003",
                "title": "获取不存在的帖子 (ID=999999)",
                "method": "GET",
                "endpoint": "/posts/999999",
                "expected_status": 404,
                "expected_response": {
                    "assertions": []
                },
                "category": "异常测试",
                "priority": "P1"
            },
            # 4. 创建新帖子
            {
                "id": "API_004",
                "title": "创建新帖子",
                "method": "POST",
                "endpoint": "/posts",
                "headers": {
                    "Content-Type": "application/json"
                },
                "request_body": {
                    "title": "测试标题",
                    "body": "测试内容",
                    "userId": 1
                },
                "expected_status": 201,
                "expected_response": {
                    "assertions": [
                        {"path": "$.id", "operator": "exists"},
                        {"path": "$.title", "operator": "equals", "value": "测试标题"},
                    ]
                },
                "category": "正向测试",
                "priority": "P0"
            },
            # 5. 更新帖子
            {
                "id": "API_005",
                "title": "更新帖子 (PUT)",
                "method": "PUT",
                "endpoint": "/posts/1",
                "headers": {
                    "Content-Type": "application/json"
                },
                "request_body": {
                    "id": 1,
                    "title": "更新后的标题",
                    "body": "更新后的内容",
                    "userId": 1
                },
                "expected_status": 200,
                "expected_response": {
                    "assertions": [
                        {"path": "$.title", "operator": "equals", "value": "更新后的标题"},
                    ]
                },
                "category": "正向测试",
                "priority": "P1"
            },
            # 6. 部分更新帖子
            {
                "id": "API_006",
                "title": "部分更新帖子 (PATCH)",
                "method": "PATCH",
                "endpoint": "/posts/1",
                "headers": {
                    "Content-Type": "application/json"
                },
                "request_body": {
                    "title": "PATCH更新的标题"
                },
                "expected_status": 200,
                "expected_response": {
                    "assertions": [
                        {"path": "$.title", "operator": "equals", "value": "PATCH更新的标题"},
                        {"path": "$.id", "operator": "equals", "value": 1},
                    ]
                },
                "category": "正向测试",
                "priority": "P1"
            },
            # 7. 删除帖子
            {
                "id": "API_007",
                "title": "删除帖子",
                "method": "DELETE",
                "endpoint": "/posts/1",
                "expected_status": 200,
                "expected_response": {
                    "assertions": []
                },
                "category": "正向测试",
                "priority": "P1"
            },
            # 8. 获取用户的所有帖子 (查询参数)
            {
                "id": "API_008",
                "title": "获取用户1的所有帖子",
                "method": "GET",
                "endpoint": "/posts",
                "query_params": {
                    "userId": "1"
                },
                "expected_status": 200,
                "expected_response": {
                    "assertions": [
                        {"path": "$[0].userId", "operator": "equals", "value": 1},
                    ]
                },
                "category": "正向测试",
                "priority": "P1"
            },
            # 9. 获取帖子的评论
            {
                "id": "API_009",
                "title": "获取帖子1的评论",
                "method": "GET",
                "endpoint": "/posts/1/comments",
                "expected_status": 200,
                "expected_response": {
                    "assertions": [
                        {"path": "$[0].postId", "operator": "equals", "value": 1},
                        {"path": "$[0].email", "operator": "exists"},
                        {"path": "$[0].body", "operator": "exists"},
                    ]
                },
                "category": "正向测试",
                "priority": "P1"
            },
            # 10. 获取所有用户
            {
                "id": "API_010",
                "title": "获取所有用户",
                "method": "GET",
                "endpoint": "/users",
                "expected_status": 200,
                "expected_response": {
                    "assertions": [
                        {"path": "$[0].id", "operator": "exists"},
                        {"path": "$[0].name", "operator": "exists"},
                        {"path": "$[0].email", "operator": "exists"},
                        {"path": "$[0].address", "operator": "exists"},
                    ]
                },
                "category": "正向测试",
                "priority": "P0"
            },
        ]
    }

    # 配置测试运行器
    config = TestRunConfig(
        output_dir="./real_api_test_output",
        api_base_url="https://jsonplaceholder.typicode.com",
        generate_reports=True,
        report_formats=["markdown", "html", "json"],
    )

    runner = TestRunner(config=config)

    print(f"\n📋 测试用例: {len(test_cases['test_cases'])} 个")
    for tc in test_cases["test_cases"]:
        print(f"   - [{tc['id']}] {tc['title']}")

    print("\n🔧 开始执行测试...")
    print("-" * 60)

    # 执行测试
    result = runner.run_api_tests(test_cases)

    # 打印结果摘要
    print("\n" + "=" * 60)
    print("📊 测试结果摘要")
    print("=" * 60)
    print(f"   总用例: {result.total}")
    print(f"   ✅ 通过: {result.passed}")
    print(f"   ❌ 失败: {result.failed}")
    print(f"   ⚠️  错误: {result.error}")
    print(f"   📈 通过率: {result.pass_rate}%")
    print(f"   ⏱️  总耗时: {result.total_time_ms:.0f}ms")

    # 打印每个用例的结果
    print("\n📝 详细结果:")
    print("-" * 60)
    for r in result.results:
        status = "✅" if r.status.value == "passed" else "❌"
        print(f"   {status} [{r.test_case_id}] {r.test_case_title}")
        print(f"      {r.method} {r.endpoint} → {r.response_status} ({r.response_time_ms:.0f}ms)")

        # 打印失败的断言
        failed_assertions = [a for a in r.assertions if not a.passed]
        if failed_assertions:
            for a in failed_assertions:
                print(f"      ❌ 断言失败: {a.message}")

    print("\n" + "=" * 60)
    print("📁 报告文件:")
    print("   ./real_api_test_output/")
    print("=" * 60)

    return result


def test_with_executor_directly():
    """直接使用执行器测试API"""

    print("\n" + "=" * 60)
    print("🔧 直接使用APITestExecutor测试")
    print("=" * 60)

    # 创建执行器
    executor = APITestExecutor(
        base_url="https://jsonplaceholder.typicode.com",
        timeout=30
    )

    # 简单测试
    test_case = {
        "id": "QUICK_001",
        "title": "快速测试 - 获取帖子",
        "method": "GET",
        "endpoint": "/posts/1",
        "expected_status": 200,
        "expected_response": {
            "assertions": [
                {"path": "$.id", "operator": "equals", "value": 1},
            ]
        }
    }

    print(f"\n执行: {test_case['method']} {test_case['endpoint']}")

    result = executor.execute_single(test_case)

    print(f"状态: {'✅ 通过' if result.status.value == 'passed' else '❌ 失败'}")
    print(f"响应状态码: {result.response_status}")
    print(f"响应时间: {result.response_time_ms:.0f}ms")
    print(f"响应体: {json.dumps(result.response_body, ensure_ascii=False)[:200]}...")

    executor.close()


if __name__ == "__main__":
    # 运行完整测试套件
    test_with_predefined_cases()

    # 也可以直接使用执行器
    # test_with_executor_directly()
