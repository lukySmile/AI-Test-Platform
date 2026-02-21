# AI测试平台 - Prompt使用示例

import sys
sys.path.append('..')

from prompts import (
    GENERAL_TEST_CASE_PROMPT,
    API_TEST_CASE_PROMPT,
    IOS_UI_TEST_CASE_PROMPT,
)
from prompts.prompt_manager import (
    PromptManager,
    get_test_case_prompt,
    get_api_test_prompt,
    get_ios_test_prompt,
)
from prompts.prompt_config import PromptType


def example_general_test_case():
    """示例：生成通用测试用例"""
    print("=" * 50)
    print("示例1: 通用测试用例生成")
    print("=" * 50)

    # 需求描述
    requirement = """
    用户登录功能：
    1. 支持手机号+密码登录
    2. 支持手机号+验证码登录
    3. 密码要求：8-20位，包含字母和数字
    4. 验证码：6位数字，60秒有效期
    5. 登录失败3次后需要图形验证码
    """

    # 方式1: 直接使用Prompt
    prompt = GENERAL_TEST_CASE_PROMPT.format(input_description=requirement)
    print(f"Prompt长度: {len(prompt)} 字符")

    # 方式2: 使用便捷函数
    prompt = get_test_case_prompt(requirement)
    print(f"生成的Prompt:\n{prompt[:500]}...")


def example_api_test_case():
    """示例：生成API测试用例"""
    print("\n" + "=" * 50)
    print("示例2: API测试用例生成")
    print("=" * 50)

    # API规范
    api_spec = """
    API: POST /api/v1/user/login
    描述: 用户登录接口

    请求参数:
    - phone: string, 必填, 手机号
    - password: string, 必填, 密码
    - device_id: string, 可选, 设备ID

    响应:
    - code: int, 状态码 (0=成功)
    - message: string, 提示信息
    - data: object
      - token: string, 登录令牌
      - user_id: int, 用户ID
      - expires_in: int, 过期时间(秒)
    """

    prompt = get_api_test_prompt(api_spec)
    print(f"生成的Prompt:\n{prompt[:500]}...")


def example_ios_test_case():
    """示例：生成iOS测试用例"""
    print("\n" + "=" * 50)
    print("示例3: iOS UI测试用例生成")
    print("=" * 50)

    # 应用描述
    app_description = """
    应用: 购物App
    页面: 商品详情页

    功能点:
    1. 显示商品图片轮播
    2. 显示商品名称、价格、库存
    3. 规格选择（颜色、尺码）
    4. 数量加减
    5. 加入购物车按钮
    6. 立即购买按钮
    7. 收藏按钮
    8. 分享按钮
    """

    prompt = get_ios_test_prompt(app_description)
    print(f"生成的Prompt:\n{prompt[:500]}...")


def example_prompt_manager():
    """示例：使用PromptManager"""
    print("\n" + "=" * 50)
    print("示例4: 使用PromptManager")
    print("=" * 50)

    # 列出所有可用Prompt
    prompts = PromptManager.list_prompts()
    print("可用的Prompt类型:")
    for name, desc in prompts.items():
        print(f"  - {name}: {desc}")

    # 构建完整消息
    messages = PromptManager.build_messages(
        prompt_type=PromptType.API_TEST_CASE,
        user_input="请生成登录接口的测试用例",
        variables={"api_specification": "POST /api/login"},
        include_system_prompt=True
    )

    print(f"\n构建的消息数量: {len(messages)}")
    for i, msg in enumerate(messages):
        print(f"消息{i+1} ({msg['role']}): {msg['content'][:100]}...")


def example_with_llm_call():
    """示例：与LLM API集成（伪代码）"""
    print("\n" + "=" * 50)
    print("示例5: 与LLM API集成（伪代码）")
    print("=" * 50)

    code = '''
# 实际使用时的代码示例

from openai import OpenAI
from prompts.prompt_manager import PromptManager
from prompts.prompt_config import PromptType, get_prompt_config

client = OpenAI()

def generate_test_cases(requirement: str) -> dict:
    """生成测试用例"""

    # 获取配置
    config = get_prompt_config(PromptType.GENERAL_TEST_CASE)

    # 构建消息
    messages = PromptManager.build_messages(
        prompt_type=PromptType.GENERAL_TEST_CASE,
        user_input=requirement,
        variables={"input_description": requirement}
    )

    # 调用API
    response = client.chat.completions.create(
        model=config.model,
        messages=messages,
        max_tokens=config.max_tokens,
        temperature=config.temperature
    )

    # 解析结果
    result = response.choices[0].message.content
    return json.loads(result)


def run_api_tests(api_spec: str) -> dict:
    """执行API测试并生成报告"""

    # 1. 生成测试用例
    test_cases = generate_test_cases(api_spec)

    # 2. 执行测试
    results = execute_tests(test_cases)

    # 3. 生成报告
    report_prompt = PromptManager.get_prompt(
        PromptType.API_TEST_REPORT,
        {"test_results": json.dumps(results)}
    )

    report = call_llm(report_prompt)
    return report
'''
    print(code)


if __name__ == "__main__":
    example_general_test_case()
    example_api_test_case()
    example_ios_test_case()
    example_prompt_manager()
    example_with_llm_call()
