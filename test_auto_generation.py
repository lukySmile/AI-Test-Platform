#!/usr/bin/env python3
"""
测试自动用例生成功能

无需AI，基于规则自动生成测试用例
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.test_case_service import TestCaseService


# 示例OpenAPI文档
SAMPLE_OPENAPI = """
{
    "openapi": "3.0.0",
    "info": {
        "title": "用户管理API",
        "version": "1.0.0",
        "description": "用户管理相关接口"
    },
    "servers": [
        {"url": "https://api.example.com/v1"}
    ],
    "paths": {
        "/users": {
            "get": {
                "summary": "获取用户列表",
                "tags": ["用户管理"],
                "parameters": [
                    {
                        "name": "page",
                        "in": "query",
                        "required": false,
                        "schema": {"type": "integer", "default": 1}
                    },
                    {
                        "name": "size",
                        "in": "query",
                        "required": false,
                        "schema": {"type": "integer", "default": 20}
                    },
                    {
                        "name": "keyword",
                        "in": "query",
                        "required": false,
                        "schema": {"type": "string"},
                        "description": "搜索关键词"
                    }
                ],
                "responses": {
                    "200": {"description": "成功"},
                    "401": {"description": "未授权"}
                },
                "security": [{"bearerAuth": []}]
            },
            "post": {
                "summary": "创建用户",
                "tags": ["用户管理"],
                "requestBody": {
                    "required": true,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["username", "email", "password"],
                                "properties": {
                                    "username": {"type": "string", "example": "john_doe"},
                                    "email": {"type": "string", "example": "john@example.com"},
                                    "password": {"type": "string", "example": "Password123"},
                                    "age": {"type": "integer", "example": 25}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "201": {"description": "创建成功"},
                    "400": {"description": "参数错误"},
                    "401": {"description": "未授权"}
                },
                "security": [{"bearerAuth": []}]
            }
        },
        "/users/{id}": {
            "get": {
                "summary": "获取用户详情",
                "tags": ["用户管理"],
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": true,
                        "schema": {"type": "integer"},
                        "description": "用户ID"
                    }
                ],
                "responses": {
                    "200": {"description": "成功"},
                    "404": {"description": "用户不存在"}
                },
                "security": [{"bearerAuth": []}]
            },
            "put": {
                "summary": "更新用户",
                "tags": ["用户管理"],
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": true,
                        "schema": {"type": "integer"}
                    }
                ],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "username": {"type": "string"},
                                    "email": {"type": "string"},
                                    "age": {"type": "integer"}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {"description": "更新成功"},
                    "404": {"description": "用户不存在"}
                },
                "security": [{"bearerAuth": []}]
            },
            "delete": {
                "summary": "删除用户",
                "tags": ["用户管理"],
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": true,
                        "schema": {"type": "integer"}
                    }
                ],
                "responses": {
                    "204": {"description": "删除成功"},
                    "404": {"description": "用户不存在"}
                },
                "security": [{"bearerAuth": []}]
            }
        },
        "/login": {
            "post": {
                "summary": "用户登录",
                "tags": ["认证"],
                "requestBody": {
                    "required": true,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["username", "password"],
                                "properties": {
                                    "username": {"type": "string"},
                                    "password": {"type": "string"}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {"description": "登录成功"},
                    "401": {"description": "用户名或密码错误"}
                }
            }
        }
    },
    "components": {
        "securitySchemes": {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer"
            }
        }
    }
}
"""


def main():
    print("=" * 60)
    print("自动测试用例生成演示")
    print("=" * 60)
    print()
    print("使用测试设计方法：")
    print("  - 等价类划分（有效/无效输入）")
    print("  - 边界值分析")
    print("  - 错误猜测")
    print("  - 安全测试（SQL注入、XSS等）")
    print()

    # 创建服务（不需要AI）
    service = TestCaseService(llm_client=None)

    # 生成测试用例
    print("正在解析API文档并生成测试用例...")
    result = service.generate_api_test_cases_auto(SAMPLE_OPENAPI)

    # 输出结果
    print()
    print("=" * 60)
    print(f"API名称: {result['api_name']}")
    print(f"API版本: {result['api_version']}")
    print(f"基础URL: {result['base_url']}")
    print(f"生成时间: {result['generated_at']}")
    print()

    # 统计信息
    summary = result["summary"]
    print("=" * 60)
    print("生成统计")
    print("=" * 60)
    print(f"接口数量: {summary['total_endpoints']}")
    print(f"用例总数: {summary['total_cases']}")
    print()

    print("按类型分布:")
    for test_type, count in summary["by_type"].items():
        print(f"  {test_type}: {count}")
    print()

    print("按优先级分布:")
    for priority, count in summary["by_priority"].items():
        print(f"  {priority}: {count}")
    print()

    # 输出测试套件详情
    print("=" * 60)
    print("测试套件详情")
    print("=" * 60)

    for suite in result["test_suites"]:
        print(f"\n【{suite['suite_name']}】 - {len(suite['test_cases'])}个用例")
        print("-" * 40)

        for i, case in enumerate(suite["test_cases"][:5], 1):  # 只显示前5个
            print(f"  {i}. [{case['priority']}] {case['title']}")
            print(f"     类型: {case['test_type']}")
            print(f"     方法: {case['design_method']}")
            print(f"     预期状态: {case['expected_status']}")
            print()

        if len(suite["test_cases"]) > 5:
            print(f"  ... 还有 {len(suite['test_cases']) - 5} 个用例")

    # 保存完整结果到文件
    output_file = "generated_test_cases.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 60)
    print(f"完整结果已保存到: {output_file}")
    print("=" * 60)

    return result


if __name__ == "__main__":
    main()
