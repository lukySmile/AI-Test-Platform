#!/usr/bin/env python3
"""
LLM 集成测试脚本 (支持 Gemini, Claude, OpenAI)

使用方法:
1. 设置环境变量:
   # Gemini
   export LLM_PROVIDER=gemini
   export GEMINI_API_KEY="your-gemini-api-key"

   # 或 Claude
   export LLM_PROVIDER=anthropic
   export ANTHROPIC_API_KEY="your-anthropic-api-key"

   # 或 OpenAI
   export LLM_PROVIDER=openai
   export OPENAI_API_KEY="your-openai-api-key"

2. 运行测试:
   python test_claude_integration.py
"""

import os
import sys
import json

# 确保可以导入项目模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.llm_client import LLMClient, LLMProvider
from core.test_case_service import TestCaseService


def test_basic_chat():
    """测试基本对话功能"""
    print("=" * 50)
    print("测试1: 基本对话功能")
    print("=" * 50)

    client = LLMClient()
    print(f"使用提供商: {client.config.provider.value}")
    print(f"使用模型: {client.config.model}")

    messages = [
        {"role": "user", "content": "请用一句话介绍你自己"}
    ]

    try:
        response = client.chat(messages, max_tokens=100)
        print(f"响应: {response}")
        print("基本对话测试 PASSED")
        return True
    except Exception as e:
        print(f"基本对话测试 FAILED: {e}")
        return False


def test_json_generation():
    """测试JSON生成功能"""
    print("\n" + "=" * 50)
    print("测试2: JSON生成功能")
    print("=" * 50)

    client = LLMClient()

    messages = [
        {"role": "system", "content": "你是一个JSON生成助手，只输出有效的JSON格式。"},
        {"role": "user", "content": "生成一个简单的用户信息JSON，包含name、age、email字段"}
    ]

    try:
        result = client.generate_json(messages, max_tokens=200)
        print(f"生成的JSON: {json.dumps(result, ensure_ascii=False, indent=2)}")
        print("JSON生成测试 PASSED")
        return True
    except Exception as e:
        print(f"JSON生成测试 FAILED: {e}")
        return False


def test_ios_test_case_generation():
    """测试iOS测试用例生成"""
    print("\n" + "=" * 50)
    print("测试3: iOS测试用例生成")
    print("=" * 50)

    try:
        client = LLMClient()
        service = TestCaseService(client)

        app_description = "登录页面：包含用户名输入框、密码输入框、登录按钮"

        result = service.generate_ios_test_cases(
            app_description=app_description,
            bundle_id="com.example.login"
        )

        print(f"生成的测试用例数量: {len(result.get('test_suites', []))}")
        if result.get('test_suites'):
            first_suite = result['test_suites'][0]
            print(f"第一个套件名称: {first_suite.get('suite_name', 'N/A')}")
            test_cases = first_suite.get('test_cases', [])
            print(f"该套件包含 {len(test_cases)} 个测试用例")

        service.close()
        print("iOS测试用例生成测试 PASSED")
        return True
    except Exception as e:
        print(f"iOS测试用例生成测试 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_android_test_case_generation():
    """测试Android测试用例生成"""
    print("\n" + "=" * 50)
    print("测试4: Android测试用例生成")
    print("=" * 50)

    try:
        client = LLMClient()
        service = TestCaseService(client)

        app_description = "购物车页面：包含商品列表、数量加减按钮、删除按钮、结算按钮"

        result = service.generate_android_test_cases(
            app_description=app_description,
            package_name="com.example.shopping"
        )

        print(f"生成的测试用例数量: {len(result.get('test_suites', []))}")
        if result.get('test_suites'):
            first_suite = result['test_suites'][0]
            print(f"第一个套件名称: {first_suite.get('suite_name', 'N/A')}")
            test_cases = first_suite.get('test_cases', [])
            print(f"该套件包含 {len(test_cases)} 个测试用例")

        service.close()
        print("Android测试用例生成测试 PASSED")
        return True
    except Exception as e:
        print(f"Android测试用例生成测试 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\nLLM 集成测试")
    print("=" * 50)

    # 获取LLM提供商
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()

    # 根据提供商检查API Key
    api_key = os.getenv("LLM_API_KEY", "")
    if not api_key:
        if provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
        elif provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY", "")
        elif provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY", "")

    if not api_key:
        print(f"错误: 请设置 API Key 环境变量")
        print(f"\n当前提供商: {provider}")
        print("\n使用方法:")
        print("  # Gemini")
        print("  export LLM_PROVIDER=gemini")
        print("  export GEMINI_API_KEY='your-api-key'")
        print("")
        print("  # Claude")
        print("  export LLM_PROVIDER=anthropic")
        print("  export ANTHROPIC_API_KEY='your-api-key'")
        print("")
        print("  python test_claude_integration.py")
        sys.exit(1)

    print(f"LLM提供商: {provider}")
    print(f"API Key: {api_key[:8]}...{api_key[-4:]}")

    results = []

    # 运行测试
    results.append(("基本对话", test_basic_chat()))
    results.append(("JSON生成", test_json_generation()))
    results.append(("iOS用例生成", test_ios_test_case_generation()))
    results.append(("Android用例生成", test_android_test_case_generation()))

    # 汇总结果
    print("\n" + "=" * 50)
    print("测试结果汇总")
    print("=" * 50)

    passed = 0
    for name, result in results:
        status = "PASSED" if result else "FAILED"
        print(f"  {name}: {status}")
        if result:
            passed += 1

    print(f"\n总计: {passed}/{len(results)} 通过")

    if passed == len(results):
        print("\n所有测试通过! Claude LLM 集成配置正确。")
    else:
        print("\n部分测试失败，请检查配置。")


if __name__ == "__main__":
    main()
