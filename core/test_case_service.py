# 测试用例服务 - 用例生成的核心业务逻辑

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from .llm_client import LLMClient
from prompts.prompt_manager import PromptManager
from prompts.prompt_config import PromptType, get_prompt_config


@dataclass
class TestCase:
    """测试用例数据类"""
    id: str
    title: str
    priority: str
    category: str
    preconditions: List[str]
    steps: List[Dict[str, Any]]
    expected_result: str
    test_data: Optional[str] = None
    created_at: Optional[str] = None
    module: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class APITestCase(TestCase):
    """API测试用例"""
    method: str = "GET"
    endpoint: str = ""
    headers: Optional[Dict[str, str]] = None
    request_body: Optional[Dict[str, Any]] = None
    query_params: Optional[Dict[str, str]] = None
    expected_status: int = 200
    assertions: Optional[List[Dict[str, Any]]] = None


@dataclass
class IOSTestCase(TestCase):
    """iOS测试用例"""
    suite_name: str = ""
    element_actions: Optional[List[Dict[str, Any]]] = None
    accessibility_ids: Optional[List[str]] = None
    cleanup_steps: Optional[List[str]] = None


@dataclass
class AndroidTestCase(TestCase):
    """Android测试用例"""
    suite_name: str = ""
    element_actions: Optional[List[Dict[str, Any]]] = None
    resource_ids: Optional[List[str]] = None
    cleanup_steps: Optional[List[str]] = None


class TestCaseService:
    """测试用例服务"""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        初始化服务

        Args:
            llm_client: LLM客户端实例
        """
        self.llm_client = llm_client or LLMClient()

    def generate_test_cases(
        self,
        requirement: str,
        module_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        生成通用测试用例

        Args:
            requirement: 需求描述
            module_name: 模块名称

        Returns:
            包含测试用例的字典
        """
        config = get_prompt_config(PromptType.GENERAL_TEST_CASE)

        messages = PromptManager.build_messages(
            prompt_type=PromptType.GENERAL_TEST_CASE,
            user_input=requirement,
            variables={"input_description": requirement}
        )

        result = self.llm_client.generate_json(
            messages,
            max_tokens=config.max_tokens,
            temperature=config.temperature
        )

        # 添加元数据
        result["generated_at"] = datetime.now().isoformat()
        result["module"] = module_name or result.get("module", "未指定")

        return result

    def generate_api_test_cases(
        self,
        api_spec: str,
        base_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        生成API测试用例

        Args:
            api_spec: API规范/文档
            base_url: API基础URL

        Returns:
            包含API测试用例的字典
        """
        config = get_prompt_config(PromptType.API_TEST_CASE)

        messages = PromptManager.build_messages(
            prompt_type=PromptType.API_TEST_CASE,
            user_input=api_spec,
            variables={"api_specification": api_spec}
        )

        result = self.llm_client.generate_json(
            messages,
            max_tokens=config.max_tokens,
            temperature=config.temperature
        )

        if base_url:
            result["base_url"] = base_url

        result["generated_at"] = datetime.now().isoformat()

        return result

    def generate_ios_test_cases(
        self,
        app_description: str,
        bundle_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        生成iOS测试用例

        Args:
            app_description: 应用功能描述
            bundle_id: 应用Bundle ID

        Returns:
            包含iOS测试用例的字典
        """
        config = get_prompt_config(PromptType.IOS_UI_TEST_CASE)

        messages = PromptManager.build_messages(
            prompt_type=PromptType.IOS_UI_TEST_CASE,
            user_input=app_description,
            variables={"app_description": app_description}
        )

        result = self.llm_client.generate_json(
            messages,
            max_tokens=config.max_tokens,
            temperature=config.temperature
        )

        if bundle_id:
            result["bundle_id"] = bundle_id

        result["generated_at"] = datetime.now().isoformat()

        return result

    def generate_ios_test_code(
        self,
        test_case: Dict[str, Any],
    ) -> str:
        """
        生成iOS测试代码

        Args:
            test_case: 测试用例字典

        Returns:
            Swift测试代码
        """
        config = get_prompt_config(PromptType.IOS_TEST_CODE)

        messages = PromptManager.build_messages(
            prompt_type=PromptType.IOS_TEST_CODE,
            user_input=json.dumps(test_case, ensure_ascii=False, indent=2),
            variables={"test_case": json.dumps(test_case, ensure_ascii=False, indent=2)}
        )

        code = self.llm_client.chat(
            messages,
            max_tokens=config.max_tokens,
            temperature=config.temperature
        )

        # 提取代码块
        import re
        code_match = re.search(r'```swift\s*([\s\S]*?)\s*```', code)
        if code_match:
            return code_match.group(1)

        return code

    def generate_android_test_cases(
        self,
        app_description: str,
        package_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        生成Android测试用例

        Args:
            app_description: 应用功能描述
            package_name: 应用包名

        Returns:
            包含Android测试用例的字典
        """
        config = get_prompt_config(PromptType.ANDROID_UI_TEST_CASE)

        messages = PromptManager.build_messages(
            prompt_type=PromptType.ANDROID_UI_TEST_CASE,
            user_input=app_description,
            variables={"app_description": app_description}
        )

        result = self.llm_client.generate_json(
            messages,
            max_tokens=config.max_tokens,
            temperature=config.temperature
        )

        if package_name:
            result["package_name"] = package_name

        result["generated_at"] = datetime.now().isoformat()

        return result

    def generate_android_test_code(
        self,
        test_case: Dict[str, Any],
    ) -> str:
        """
        生成Android测试代码

        Args:
            test_case: 测试用例字典

        Returns:
            Kotlin测试代码
        """
        config = get_prompt_config(PromptType.ANDROID_TEST_CODE)

        messages = PromptManager.build_messages(
            prompt_type=PromptType.ANDROID_TEST_CODE,
            user_input=json.dumps(test_case, ensure_ascii=False, indent=2),
            variables={"test_case": json.dumps(test_case, ensure_ascii=False, indent=2)}
        )

        code = self.llm_client.chat(
            messages,
            max_tokens=config.max_tokens,
            temperature=config.temperature
        )

        # 提取代码块
        import re
        code_match = re.search(r'```kotlin\s*([\s\S]*?)\s*```', code)
        if code_match:
            return code_match.group(1)

        return code

    def analyze_requirement(
        self,
        requirement_doc: str,
    ) -> Dict[str, Any]:
        """
        分析需求文档

        Args:
            requirement_doc: 需求文档内容

        Returns:
            分析结果，包含测试点和风险点
        """
        config = get_prompt_config(PromptType.REQUIREMENT_ANALYSIS)

        messages = PromptManager.build_messages(
            prompt_type=PromptType.REQUIREMENT_ANALYSIS,
            user_input=requirement_doc,
            variables={"requirement_document": requirement_doc}
        )

        return self.llm_client.generate_json(
            messages,
            max_tokens=config.max_tokens,
            temperature=config.temperature
        )

    def generate_test_data(
        self,
        test_case_requirements: str,
    ) -> Dict[str, Any]:
        """
        生成测试数据

        Args:
            test_case_requirements: 用例数据需求描述

        Returns:
            测试数据集
        """
        config = get_prompt_config(PromptType.TEST_DATA_GENERATION)

        messages = PromptManager.build_messages(
            prompt_type=PromptType.TEST_DATA_GENERATION,
            user_input=test_case_requirements,
            variables={"test_case_requirements": test_case_requirements}
        )

        return self.llm_client.generate_json(
            messages,
            max_tokens=config.max_tokens,
            temperature=config.temperature
        )

    def close(self):
        """关闭服务"""
        self.llm_client.close()
