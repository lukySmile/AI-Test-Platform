# Prompt 配置管理

from dataclasses import dataclass
from typing import Dict, Optional
from enum import Enum


class PromptType(Enum):
    """Prompt类型枚举"""
    # 用例生成
    GENERAL_TEST_CASE = "general_test_case"
    API_TEST_CASE = "api_test_case"
    IOS_UI_TEST_CASE = "ios_ui_test_case"

    # 代码生成
    IOS_TEST_CODE = "ios_test_code"

    # 报告生成
    API_TEST_REPORT = "api_test_report"
    IOS_TEST_REPORT = "ios_test_report"

    # 分析类
    REQUIREMENT_ANALYSIS = "requirement_analysis"
    ERROR_ANALYSIS = "error_analysis"
    TEST_DATA_GENERATION = "test_data_generation"

    # 命令生成
    IOS_SIMULATOR_COMMAND = "ios_simulator_command"


@dataclass
class PromptConfig:
    """Prompt配置类"""
    name: str
    description: str
    prompt_type: PromptType
    max_tokens: int = 4096
    temperature: float = 0.7
    model: str = "gpt-4"

    # 输入输出格式
    input_format: str = "text"  # text, json, markdown
    output_format: str = "json"  # text, json, markdown, code


# Prompt配置映射
PROMPT_CONFIGS: Dict[PromptType, PromptConfig] = {
    PromptType.GENERAL_TEST_CASE: PromptConfig(
        name="通用测试用例生成",
        description="根据需求描述生成测试用例",
        prompt_type=PromptType.GENERAL_TEST_CASE,
        max_tokens=4096,
        temperature=0.7,
        output_format="json"
    ),
    PromptType.API_TEST_CASE: PromptConfig(
        name="API测试用例生成",
        description="根据API文档生成测试用例",
        prompt_type=PromptType.API_TEST_CASE,
        max_tokens=4096,
        temperature=0.5,
        output_format="json"
    ),
    PromptType.IOS_UI_TEST_CASE: PromptConfig(
        name="iOS UI测试用例生成",
        description="根据应用描述生成iOS测试用例",
        prompt_type=PromptType.IOS_UI_TEST_CASE,
        max_tokens=4096,
        temperature=0.7,
        output_format="json"
    ),
    PromptType.IOS_TEST_CODE: PromptConfig(
        name="iOS测试代码生成",
        description="生成XCUITest Swift代码",
        prompt_type=PromptType.IOS_TEST_CODE,
        max_tokens=8192,
        temperature=0.3,
        output_format="code"
    ),
    PromptType.API_TEST_REPORT: PromptConfig(
        name="API测试报告生成",
        description="根据测试结果生成报告",
        prompt_type=PromptType.API_TEST_REPORT,
        max_tokens=4096,
        temperature=0.5,
        output_format="markdown"
    ),
    PromptType.IOS_TEST_REPORT: PromptConfig(
        name="iOS测试报告生成",
        description="根据iOS测试结果生成报告",
        prompt_type=PromptType.IOS_TEST_REPORT,
        max_tokens=4096,
        temperature=0.5,
        output_format="markdown"
    ),
    PromptType.REQUIREMENT_ANALYSIS: PromptConfig(
        name="需求分析",
        description="分析需求文档提取测试点",
        prompt_type=PromptType.REQUIREMENT_ANALYSIS,
        max_tokens=4096,
        temperature=0.7,
        output_format="json"
    ),
    PromptType.ERROR_ANALYSIS: PromptConfig(
        name="错误分析",
        description="分析测试失败原因",
        prompt_type=PromptType.ERROR_ANALYSIS,
        max_tokens=2048,
        temperature=0.5,
        output_format="json"
    ),
    PromptType.TEST_DATA_GENERATION: PromptConfig(
        name="测试数据生成",
        description="生成测试数据集",
        prompt_type=PromptType.TEST_DATA_GENERATION,
        max_tokens=4096,
        temperature=0.7,
        output_format="json"
    ),
    PromptType.IOS_SIMULATOR_COMMAND: PromptConfig(
        name="iOS模拟器命令生成",
        description="生成模拟器控制命令",
        prompt_type=PromptType.IOS_SIMULATOR_COMMAND,
        max_tokens=2048,
        temperature=0.3,
        output_format="code"
    ),
}


def get_prompt_config(prompt_type: PromptType) -> Optional[PromptConfig]:
    """获取Prompt配置"""
    return PROMPT_CONFIGS.get(prompt_type)
