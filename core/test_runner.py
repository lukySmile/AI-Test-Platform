# 测试运行器 - 统一的测试执行入口

import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .llm_client import LLMClient
from .test_case_service import TestCaseService
from executors.api_executor import APITestExecutor, APITestSuiteResult
from executors.ios_executor import IOSTestExecutor, IOSTestSuiteResult
from reporters.api_reporter import APITestReporter
from reporters.ios_reporter import IOSTestReporter
from prompts.prompt_manager import PromptManager
from prompts.prompt_config import PromptType


@dataclass
class TestRunConfig:
    """测试运行配置"""
    # 通用配置
    output_dir: str = "./test_output"
    generate_reports: bool = True
    report_formats: List[str] = None  # ["markdown", "html", "json"]

    # API测试配置
    api_base_url: Optional[str] = None
    api_headers: Optional[Dict[str, str]] = None
    api_timeout: int = 30
    api_parallel: bool = False

    # iOS测试配置
    ios_project_path: Optional[str] = None
    ios_scheme: Optional[str] = None
    ios_device_name: str = "iPhone 15 Pro"
    ios_version: str = "17.0"
    ios_timeout: int = 600

    def __post_init__(self):
        if self.report_formats is None:
            self.report_formats = ["markdown", "html", "json"]


class TestRunner:
    """
    统一测试运行器

    整合测试用例生成、执行和报告生成的完整流程
    """

    def __init__(
        self,
        config: Optional[TestRunConfig] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        """
        初始化测试运行器

        Args:
            config: 测试运行配置
            llm_client: LLM客户端（可选，用于AI生成测试用例）
        """
        self.config = config or TestRunConfig()
        self.llm_client = llm_client
        self.test_case_service = TestCaseService(llm_client) if llm_client else None

        # 创建输出目录
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 初始化报告器
        self.api_reporter = APITestReporter(output_dir=str(self.output_dir))
        self.ios_reporter = IOSTestReporter(output_dir=str(self.output_dir))

    # ==================== API测试 ====================

    def run_api_tests(
        self,
        test_cases: Dict[str, Any],
        base_url: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
    ) -> APITestSuiteResult:
        """
        执行API测试

        Args:
            test_cases: 测试用例字典（LLM生成的格式）
            base_url: API基础URL（覆盖配置）
            variables: 预设变量（如token）

        Returns:
            测试套件结果
        """
        base_url = base_url or self.config.api_base_url or test_cases.get("base_url", "")

        if not base_url:
            raise ValueError("必须提供API基础URL")

        # 创建执行器
        executor = APITestExecutor(
            base_url=base_url,
            default_headers=self.config.api_headers,
            timeout=self.config.api_timeout,
        )

        # 设置预设变量
        if variables:
            for name, value in variables.items():
                executor.set_variable(name, value)

        # 提取测试用例列表
        cases = test_cases.get("test_cases", [])
        suite_name = test_cases.get("api_name", "API测试套件")

        # 执行测试
        try:
            result = executor.execute_suite(
                test_cases=cases,
                suite_name=suite_name,
                parallel=self.config.api_parallel,
            )

            # 生成报告
            if self.config.generate_reports:
                self._generate_api_reports(result)

            return result
        finally:
            executor.close()

    def generate_and_run_api_tests(
        self,
        api_spec: str,
        base_url: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> APITestSuiteResult:
        """
        使用AI生成测试用例并执行

        Args:
            api_spec: API规范/文档
            base_url: API基础URL
            variables: 预设变量

        Returns:
            测试套件结果
        """
        if not self.test_case_service:
            raise ValueError("需要配置LLM客户端才能使用AI生成功能")

        # 生成测试用例
        print("🤖 正在使用AI生成API测试用例...")
        test_cases = self.test_case_service.generate_api_test_cases(
            api_spec=api_spec,
            base_url=base_url,
        )

        print(f"✅ 已生成 {len(test_cases.get('test_cases', []))} 个测试用例")

        # 保存生成的测试用例
        cases_file = self.output_dir / f"api_test_cases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(cases_file, "w", encoding="utf-8") as f:
            json.dump(test_cases, f, ensure_ascii=False, indent=2)
        print(f"📄 测试用例已保存: {cases_file}")

        # 执行测试
        print("\n🚀 开始执行API测试...")
        return self.run_api_tests(test_cases, base_url, variables)

    def _generate_api_reports(self, result: APITestSuiteResult):
        """生成API测试报告"""
        for fmt in self.config.report_formats:
            try:
                path = self.api_reporter.save_report(result, format=fmt)
                print(f"📊 {fmt.upper()}报告已生成: {path}")
            except Exception as e:
                print(f"⚠️ {fmt}报告生成失败: {e}")

    # ==================== iOS测试 ====================

    def run_ios_tests(
        self,
        test_cases: Optional[Dict[str, Any]] = None,
        only_testing: Optional[List[str]] = None,
        skip_testing: Optional[List[str]] = None,
    ) -> IOSTestSuiteResult:
        """
        执行iOS测试

        Args:
            test_cases: 测试用例字典（用于生成Swift代码）
            only_testing: 只运行指定的测试
            skip_testing: 跳过指定的测试

        Returns:
            测试套件结果
        """
        if not self.config.ios_project_path or not self.config.ios_scheme:
            raise ValueError("必须配置iOS项目路径和scheme")

        # 创建执行器
        executor = IOSTestExecutor(
            project_path=self.config.ios_project_path,
            scheme=self.config.ios_scheme,
            output_dir=str(self.output_dir),
        )

        # 如果提供了测试用例，先生成Swift代码
        if test_cases:
            swift_file = self._generate_ios_test_code(executor, test_cases)
            print(f"📄 Swift测试代码已生成: {swift_file}")

        # 执行测试
        print(f"🍎 在 {self.config.ios_device_name} (iOS {self.config.ios_version}) 上执行测试...")
        result = executor.execute_tests(
            device_name=self.config.ios_device_name,
            ios_version=self.config.ios_version,
            only_testing=only_testing,
            skip_testing=skip_testing,
            timeout=self.config.ios_timeout,
        )

        # 生成报告
        if self.config.generate_reports:
            self._generate_ios_reports(result)

        return result

    def generate_and_run_ios_tests(
        self,
        app_description: str,
        bundle_id: Optional[str] = None,
    ) -> IOSTestSuiteResult:
        """
        使用AI生成iOS测试用例并执行

        Args:
            app_description: 应用功能描述
            bundle_id: 应用Bundle ID

        Returns:
            测试套件结果
        """
        if not self.test_case_service:
            raise ValueError("需要配置LLM客户端才能使用AI生成功能")

        # 生成测试用例
        print("🤖 正在使用AI生成iOS测试用例...")
        test_cases = self.test_case_service.generate_ios_test_cases(
            app_description=app_description,
            bundle_id=bundle_id,
        )

        # 统计
        total_cases = sum(
            len(suite.get("test_cases", []))
            for suite in test_cases.get("test_suites", [])
        )
        print(f"✅ 已生成 {total_cases} 个测试用例")

        # 保存生成的测试用例
        cases_file = self.output_dir / f"ios_test_cases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(cases_file, "w", encoding="utf-8") as f:
            json.dump(test_cases, f, ensure_ascii=False, indent=2)
        print(f"📄 测试用例已保存: {cases_file}")

        # 执行测试
        print("\n🚀 开始执行iOS测试...")
        return self.run_ios_tests(test_cases)

    def _generate_ios_test_code(
        self,
        executor: IOSTestExecutor,
        test_cases: Dict[str, Any],
    ) -> str:
        """生成iOS Swift测试代码"""
        all_cases = []
        for suite in test_cases.get("test_suites", []):
            all_cases.extend(suite.get("test_cases", []))

        if not all_cases:
            return ""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = str(self.output_dir / f"GeneratedUITests_{timestamp}.swift")

        return executor.generate_test_file(
            test_cases=all_cases,
            output_file=output_file,
            test_class_name="GeneratedUITests",
        )

    def _generate_ios_reports(self, result: IOSTestSuiteResult):
        """生成iOS测试报告"""
        for fmt in self.config.report_formats:
            try:
                path = self.ios_reporter.save_report(result, format=fmt)
                print(f"📊 {fmt.upper()}报告已生成: {path}")
            except Exception as e:
                print(f"⚠️ {fmt}报告生成失败: {e}")

    # ==================== 综合功能 ====================

    def analyze_test_failures(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用AI分析测试失败原因

        Args:
            results: 测试结果（APITestSuiteResult.to_dict() 或 IOSTestSuiteResult.to_dict()）

        Returns:
            分析结果
        """
        if not self.test_case_service:
            raise ValueError("需要配置LLM客户端才能使用AI分析功能")

        # 提取失败的测试
        failed_tests = [
            r for r in results.get("results", [])
            if r.get("status") in ["failed", "error"]
        ]

        if not failed_tests:
            return {"message": "没有失败的测试用例"}

        # 构建错误信息
        error_details = json.dumps(failed_tests, ensure_ascii=False, indent=2)

        # 调用AI分析
        config = PromptManager.get_prompt(
            PromptType.ERROR_ANALYSIS,
            {"error_details": error_details}
        )

        messages = [
            {"role": "system", "content": PromptManager.get_system_prompt()},
            {"role": "user", "content": config},
        ]

        analysis = self.llm_client.generate_json(messages)
        return analysis

    def list_available_simulators(self) -> List[Dict[str, str]]:
        """列出可用的iOS模拟器"""
        if not self.config.ios_project_path:
            # 创建临时执行器
            executor = IOSTestExecutor(
                project_path=".",
                scheme="",
                output_dir=str(self.output_dir),
            )
        else:
            executor = IOSTestExecutor(
                project_path=self.config.ios_project_path,
                scheme=self.config.ios_scheme or "",
                output_dir=str(self.output_dir),
            )

        devices = executor.list_simulators()
        return [
            {
                "name": d.name,
                "udid": d.udid,
                "runtime": d.runtime,
                "state": d.state,
            }
            for d in devices
        ]

    def close(self):
        """关闭资源"""
        if self.test_case_service:
            self.test_case_service.close()


# 便捷函数

def run_api_tests_from_spec(
    api_spec: str,
    base_url: str,
    llm_api_key: Optional[str] = None,
    output_dir: str = "./test_output",
) -> APITestSuiteResult:
    """
    从API规范运行测试的便捷函数

    Args:
        api_spec: API规范/文档
        base_url: API基础URL
        llm_api_key: LLM API密钥（可选，用于AI生成）
        output_dir: 输出目录

    Returns:
        测试结果
    """
    from .llm_client import LLMClient, LLMConfig, LLMProvider

    config = TestRunConfig(
        output_dir=output_dir,
        api_base_url=base_url,
    )

    llm_client = None
    if llm_api_key:
        llm_config = LLMConfig(
            provider=LLMProvider.OPENAI,
            api_key=llm_api_key,
            model="gpt-4",
        )
        llm_client = LLMClient(llm_config)

    runner = TestRunner(config=config, llm_client=llm_client)

    try:
        if llm_client:
            return runner.generate_and_run_api_tests(api_spec, base_url)
        else:
            raise ValueError("需要提供LLM API密钥才能从规范生成测试用例")
    finally:
        runner.close()


def run_api_tests_from_file(
    test_cases_file: str,
    base_url: str,
    output_dir: str = "./test_output",
) -> APITestSuiteResult:
    """
    从文件加载测试用例并运行

    Args:
        test_cases_file: 测试用例JSON文件路径
        base_url: API基础URL
        output_dir: 输出目录

    Returns:
        测试结果
    """
    with open(test_cases_file, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    config = TestRunConfig(
        output_dir=output_dir,
        api_base_url=base_url,
    )

    runner = TestRunner(config=config)
    return runner.run_api_tests(test_cases, base_url)
