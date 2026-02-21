#!/usr/bin/env python3
"""
AI测试平台 - Prompt生成测试脚本

使用方法:
1. 配置环境变量:
   export LLM_API_KEY="your_openai_api_key"
   export LLM_PROVIDER="openai"
   export LLM_MODEL="gpt-4"

2. 运行测试:
   python test_prompt_generation.py
"""

import os
import sys
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prompts.prompt_manager import PromptManager
from prompts.prompt_config import PromptType
from core.llm_client import LLMClient, LLMConfig, LLMProvider


def test_without_api():
    """不调用API的Prompt测试"""
    print("=" * 60)
    print("测试1: Prompt构建测试 (无需API)")
    print("=" * 60)

    # 测试需求
    requirement = """
    用户注册功能:
    1. 输入手机号、密码、确认密码
    2. 手机号需要短信验证
    3. 密码长度8-20位
    """

    # 构建消息
    messages = PromptManager.build_messages(
        prompt_type=PromptType.GENERAL_TEST_CASE,
        user_input=requirement,
        variables={"input_description": requirement}
    )

    print(f"成功构建消息: {len(messages)} 条")
    print(f"- System消息长度: {len(messages[0]['content'])} 字符")
    print(f"- User消息长度: {len(messages[1]['content'])} 字符")

    # 验证所有Prompt类型
    print("\n可用的Prompt类型:")
    for pt in PromptType:
        try:
            prompt = PromptManager.PROMPT_MAP.get(pt)
            if prompt:
                print(f"  ✓ {pt.value}: {len(prompt)} 字符")
            else:
                print(f"  ✗ {pt.value}: 未找到")
        except Exception as e:
            print(f"  ✗ {pt.value}: 错误 - {e}")

    print("\n✅ Prompt构建测试通过!")
    return True


def test_with_api():
    """调用API的完整测试"""
    print("\n" + "=" * 60)
    print("测试2: LLM API调用测试")
    print("=" * 60)

    # 检查API Key
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        print("⚠️  未配置 LLM_API_KEY 环境变量")
        print("   请运行: export LLM_API_KEY='your_api_key'")
        return False

    print(f"API Provider: {os.getenv('LLM_PROVIDER', 'openai')}")
    print(f"Model: {os.getenv('LLM_MODEL', 'gpt-4')}")

    # 创建LLM客户端
    try:
        client = LLMClient()

        # 简单的API测试
        api_spec = """
        API: GET /api/users/{id}
        描述: 获取用户信息
        参数: id (path, required) - 用户ID
        响应: {"code": 0, "data": {"id": 1, "name": "张三"}}
        """

        print("\n正在生成API测试用例...")

        messages = PromptManager.build_messages(
            prompt_type=PromptType.API_TEST_CASE,
            user_input=api_spec,
            variables={"api_specification": api_spec}
        )

        result = client.generate_json(messages, max_tokens=2000)

        print("\n生成的测试用例:")
        print(json.dumps(result, ensure_ascii=False, indent=2)[:1000])

        if "test_cases" in result:
            print(f"\n✅ 成功生成 {len(result.get('test_cases', []))} 个测试用例!")

        client.close()
        return True

    except Exception as e:
        print(f"\n❌ API调用失败: {e}")
        return False


def main():
    """主函数"""
    print("\n🚀 AI测试平台 - Prompt生成测试\n")

    # 测试1: 无需API的测试
    test_without_api()

    # 测试2: API调用测试
    test_with_api()

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
