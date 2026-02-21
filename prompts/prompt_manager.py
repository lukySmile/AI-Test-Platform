# Prompt 管理器 - 统一管理和调用Prompt

from typing import Dict, Any, Optional
from .prompt_config import PromptType, get_prompt_config

# 导入所有Prompt
from .test_case_generator import (
    GENERAL_TEST_CASE_PROMPT,
    API_TEST_CASE_PROMPT,
    API_TEST_REPORT_PROMPT,
)
from .ios_simulator_test import (
    IOS_UI_TEST_CASE_PROMPT,
    IOS_TEST_CODE_GENERATOR_PROMPT,
    IOS_TEST_REPORT_PROMPT,
    IOS_SIMULATOR_COMMAND_PROMPT,
)
from .android_simulator_test import (
    ANDROID_UI_TEST_CASE_PROMPT,
    ANDROID_TEST_CODE_GENERATOR_PROMPT,
    ANDROID_TEST_REPORT_PROMPT,
    ANDROID_EMULATOR_COMMAND_PROMPT,
)
from .system_prompts import (
    PLATFORM_SYSTEM_PROMPT,
    REQUIREMENT_ANALYSIS_PROMPT,
    TEST_DATA_GENERATION_PROMPT,
    ERROR_ANALYSIS_PROMPT,
)


class PromptManager:
    """Prompt管理器"""

    # Prompt映射表
    PROMPT_MAP: Dict[PromptType, str] = {
        PromptType.GENERAL_TEST_CASE: GENERAL_TEST_CASE_PROMPT,
        PromptType.API_TEST_CASE: API_TEST_CASE_PROMPT,
        PromptType.IOS_UI_TEST_CASE: IOS_UI_TEST_CASE_PROMPT,
        PromptType.IOS_TEST_CODE: IOS_TEST_CODE_GENERATOR_PROMPT,
        PromptType.API_TEST_REPORT: API_TEST_REPORT_PROMPT,
        PromptType.IOS_TEST_REPORT: IOS_TEST_REPORT_PROMPT,
        PromptType.ANDROID_UI_TEST_CASE: ANDROID_UI_TEST_CASE_PROMPT,
        PromptType.ANDROID_TEST_CODE: ANDROID_TEST_CODE_GENERATOR_PROMPT,
        PromptType.ANDROID_TEST_REPORT: ANDROID_TEST_REPORT_PROMPT,
        PromptType.ANDROID_EMULATOR_COMMAND: ANDROID_EMULATOR_COMMAND_PROMPT,
        PromptType.REQUIREMENT_ANALYSIS: REQUIREMENT_ANALYSIS_PROMPT,
        PromptType.ERROR_ANALYSIS: ERROR_ANALYSIS_PROMPT,
        PromptType.TEST_DATA_GENERATION: TEST_DATA_GENERATION_PROMPT,
        PromptType.IOS_SIMULATOR_COMMAND: IOS_SIMULATOR_COMMAND_PROMPT,
    }

    @classmethod
    def get_prompt(
        cls,
        prompt_type: PromptType,
        variables: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        获取并填充Prompt

        Args:
            prompt_type: Prompt类型
            variables: 变量字典，用于填充Prompt中的占位符

        Returns:
            填充后的Prompt字符串
        """
        prompt_template = cls.PROMPT_MAP.get(prompt_type)
        if not prompt_template:
            raise ValueError(f"未找到Prompt类型: {prompt_type}")

        if variables:
            try:
                return prompt_template.format(**variables)
            except KeyError as e:
                raise ValueError(f"缺少必要的变量: {e}")

        return prompt_template

    @classmethod
    def get_system_prompt(cls) -> str:
        """获取系统级Prompt"""
        return PLATFORM_SYSTEM_PROMPT

    @classmethod
    def build_messages(
        cls,
        prompt_type: PromptType,
        user_input: str,
        variables: Optional[Dict[str, Any]] = None,
        include_system_prompt: bool = True
    ) -> list:
        """
        构建完整的消息列表，用于API调用

        Args:
            prompt_type: Prompt类型
            user_input: 用户输入
            variables: 变量字典
            include_system_prompt: 是否包含系统Prompt

        Returns:
            消息列表
        """
        messages = []

        # 添加系统Prompt
        if include_system_prompt:
            messages.append({
                "role": "system",
                "content": cls.get_system_prompt()
            })

        # 添加功能Prompt作为用户消息的一部分
        prompt = cls.get_prompt(prompt_type, variables)

        messages.append({
            "role": "user",
            "content": f"{prompt}\n\n## 用户输入\n{user_input}"
        })

        return messages

    @classmethod
    def list_prompts(cls) -> Dict[str, str]:
        """列出所有可用的Prompt"""
        return {
            pt.value: get_prompt_config(pt).description
            for pt in PromptType
        }


# 便捷函数
def get_test_case_prompt(input_description: str) -> str:
    """获取测试用例生成Prompt"""
    return PromptManager.get_prompt(
        PromptType.GENERAL_TEST_CASE,
        {"input_description": input_description}
    )


def get_api_test_prompt(api_specification: str) -> str:
    """获取API测试用例生成Prompt"""
    return PromptManager.get_prompt(
        PromptType.API_TEST_CASE,
        {"api_specification": api_specification}
    )


def get_ios_test_prompt(app_description: str) -> str:
    """获取iOS测试用例生成Prompt"""
    return PromptManager.get_prompt(
        PromptType.IOS_UI_TEST_CASE,
        {"app_description": app_description}
    )


def get_ios_code_prompt(test_case: str) -> str:
    """获取iOS测试代码生成Prompt"""
    return PromptManager.get_prompt(
        PromptType.IOS_TEST_CODE,
        {"test_case": test_case}
    )


def get_android_test_prompt(app_description: str) -> str:
    """获取Android测试用例生成Prompt"""
    return PromptManager.get_prompt(
        PromptType.ANDROID_UI_TEST_CASE,
        {"app_description": app_description}
    )


def get_android_code_prompt(test_case: str) -> str:
    """获取Android测试代码生成Prompt"""
    return PromptManager.get_prompt(
        PromptType.ANDROID_TEST_CODE,
        {"test_case": test_case}
    )


def get_report_prompt(prompt_type: PromptType, test_results: str) -> str:
    """获取测试报告生成Prompt"""
    return PromptManager.get_prompt(
        prompt_type,
        {"test_results": test_results}
    )
