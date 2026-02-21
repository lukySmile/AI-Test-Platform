# iOS模拟器测试执行器

import subprocess
import json
import os
import time
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path


class IOSTestStatus(Enum):
    """iOS测试状态"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class IOSDevice:
    """iOS设备信息"""
    udid: str
    name: str
    device_type: str
    runtime: str
    state: str  # Booted, Shutdown

    @classmethod
    def from_simctl(cls, data: Dict[str, Any], runtime: str) -> "IOSDevice":
        return cls(
            udid=data.get("udid", ""),
            name=data.get("name", ""),
            device_type=data.get("deviceTypeIdentifier", ""),
            runtime=runtime,
            state=data.get("state", ""),
        )


@dataclass
class IOSTestCaseResult:
    """iOS测试用例结果"""
    test_case_id: str
    test_case_title: str
    test_class: str
    test_method: str
    status: IOSTestStatus
    duration_seconds: float
    error_message: str = ""
    failure_reason: str = ""
    screenshot_path: str = ""
    log_path: str = ""
    executed_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["status"] = self.status.value
        return result


@dataclass
class IOSTestSuiteResult:
    """iOS测试套件结果"""
    suite_name: str
    device_name: str
    device_udid: str
    ios_version: str
    app_bundle_id: str
    total: int
    passed: int
    failed: int
    skipped: int
    error: int
    pass_rate: float
    total_duration_seconds: float
    results: List[IOSTestCaseResult]
    result_bundle_path: str
    started_at: str
    finished_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suite_name": self.suite_name,
            "device_name": self.device_name,
            "device_udid": self.device_udid,
            "ios_version": self.ios_version,
            "app_bundle_id": self.app_bundle_id,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "error": self.error,
            "pass_rate": self.pass_rate,
            "total_duration_seconds": self.total_duration_seconds,
            "results": [r.to_dict() for r in self.results],
            "result_bundle_path": self.result_bundle_path,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


class IOSTestExecutor:
    """iOS模拟器测试执行器"""

    def __init__(
        self,
        project_path: str,
        scheme: str,
        output_dir: str = "./test_output",
    ):
        """
        初始化iOS测试执行器

        Args:
            project_path: Xcode项目路径 (.xcodeproj 或 .xcworkspace)
            scheme: 测试scheme名称
            output_dir: 测试输出目录
        """
        self.project_path = project_path
        self.scheme = scheme
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 判断项目类型
        if project_path.endswith(".xcworkspace"):
            self.project_type = "workspace"
        else:
            self.project_type = "project"

    def list_simulators(self) -> List[IOSDevice]:
        """列出所有可用的iOS模拟器"""
        result = subprocess.run(
            ["xcrun", "simctl", "list", "devices", "-j"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"获取模拟器列表失败: {result.stderr}")

        data = json.loads(result.stdout)
        devices = []

        for runtime, device_list in data.get("devices", {}).items():
            # 提取iOS版本
            if "iOS" not in runtime:
                continue

            for device in device_list:
                if device.get("isAvailable", False):
                    devices.append(IOSDevice.from_simctl(device, runtime))

        return devices

    def boot_simulator(self, device_udid: str) -> bool:
        """启动模拟器"""
        result = subprocess.run(
            ["xcrun", "simctl", "boot", device_udid],
            capture_output=True,
            text=True
        )
        return result.returncode == 0 or "already booted" in result.stderr.lower()

    def shutdown_simulator(self, device_udid: str) -> bool:
        """关闭模拟器"""
        result = subprocess.run(
            ["xcrun", "simctl", "shutdown", device_udid],
            capture_output=True,
            text=True
        )
        return result.returncode == 0

    def install_app(self, device_udid: str, app_path: str) -> bool:
        """在模拟器上安装应用"""
        result = subprocess.run(
            ["xcrun", "simctl", "install", device_udid, app_path],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"安装应用失败: {result.stderr}")
            return False
        return True

    def uninstall_app(self, device_udid: str, bundle_id: str) -> bool:
        """卸载应用"""
        result = subprocess.run(
            ["xcrun", "simctl", "uninstall", device_udid, bundle_id],
            capture_output=True,
            text=True
        )
        return result.returncode == 0

    def take_screenshot(self, device_udid: str, output_path: str) -> bool:
        """截图"""
        result = subprocess.run(
            ["xcrun", "simctl", "io", device_udid, "screenshot", output_path],
            capture_output=True,
            text=True
        )
        return result.returncode == 0

    def start_video_recording(self, device_udid: str, output_path: str) -> subprocess.Popen:
        """开始录制视频"""
        process = subprocess.Popen(
            ["xcrun", "simctl", "io", device_udid, "recordVideo", output_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return process

    def execute_tests(
        self,
        device_name: str,
        ios_version: str,
        test_targets: Optional[List[str]] = None,
        only_testing: Optional[List[str]] = None,
        skip_testing: Optional[List[str]] = None,
        timeout: int = 600,
    ) -> IOSTestSuiteResult:
        """
        执行iOS测试

        Args:
            device_name: 设备名称 (如 "iPhone 15 Pro")
            ios_version: iOS版本 (如 "17.0")
            test_targets: 测试目标列表
            only_testing: 只运行指定的测试 (格式: TestTarget/TestClass/testMethod)
            skip_testing: 跳过指定的测试
            timeout: 超时时间（秒）

        Returns:
            测试套件结果
        """
        started_at = datetime.now().isoformat()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_bundle_path = str(self.output_dir / f"TestResults_{timestamp}.xcresult")

        # 构建xcodebuild命令
        cmd = [
            "xcodebuild", "test",
            f"-{self.project_type}", self.project_path,
            "-scheme", self.scheme,
            "-destination", f"platform=iOS Simulator,name={device_name},OS={ios_version}",
            "-resultBundlePath", result_bundle_path,
        ]

        if only_testing:
            for test in only_testing:
                cmd.extend(["-only-testing", test])

        if skip_testing:
            for test in skip_testing:
                cmd.extend(["-skip-testing", test])

        # 执行测试
        print(f"执行命令: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            output = result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            output = "测试执行超时"

        finished_at = datetime.now().isoformat()

        # 解析测试结果
        test_results = self._parse_xcodebuild_output(output)

        # 从模拟器列表获取设备信息
        devices = self.list_simulators()
        device = next((d for d in devices if d.name == device_name), None)
        device_udid = device.udid if device else ""

        # 统计
        passed = sum(1 for r in test_results if r.status == IOSTestStatus.PASSED)
        failed = sum(1 for r in test_results if r.status == IOSTestStatus.FAILED)
        skipped = sum(1 for r in test_results if r.status == IOSTestStatus.SKIPPED)
        error = sum(1 for r in test_results if r.status == IOSTestStatus.ERROR)
        total = len(test_results)
        total_duration = sum(r.duration_seconds for r in test_results)
        pass_rate = (passed / total * 100) if total > 0 else 0

        return IOSTestSuiteResult(
            suite_name=self.scheme,
            device_name=device_name,
            device_udid=device_udid,
            ios_version=ios_version,
            app_bundle_id="",
            total=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            error=error,
            pass_rate=round(pass_rate, 2),
            total_duration_seconds=round(total_duration, 2),
            results=test_results,
            result_bundle_path=result_bundle_path,
            started_at=started_at,
            finished_at=finished_at,
        )

    def _parse_xcodebuild_output(self, output: str) -> List[IOSTestCaseResult]:
        """解析xcodebuild输出"""
        results = []

        # 匹配测试结果行
        # Test Case '-[TestClass testMethod]' passed (0.123 seconds).
        # Test Case '-[TestClass testMethod]' failed (0.456 seconds).
        pattern = r"Test Case '-\[(\w+) (\w+)\]' (passed|failed) \(([\d.]+) seconds\)"

        for match in re.finditer(pattern, output):
            test_class = match.group(1)
            test_method = match.group(2)
            status_str = match.group(3)
            duration = float(match.group(4))

            status = IOSTestStatus.PASSED if status_str == "passed" else IOSTestStatus.FAILED

            # 尝试提取失败原因
            failure_reason = ""
            if status == IOSTestStatus.FAILED:
                # 查找失败详情
                failure_pattern = rf"{test_class}.*{test_method}.*\n\s*(.+error.+)"
                failure_match = re.search(failure_pattern, output, re.IGNORECASE)
                if failure_match:
                    failure_reason = failure_match.group(1).strip()

            results.append(IOSTestCaseResult(
                test_case_id=f"{test_class}_{test_method}",
                test_case_title=f"{test_class}.{test_method}",
                test_class=test_class,
                test_method=test_method,
                status=status,
                duration_seconds=duration,
                failure_reason=failure_reason,
            ))

        return results

    def generate_test_file(
        self,
        test_cases: List[Dict[str, Any]],
        output_file: str,
        test_class_name: str = "GeneratedUITests",
    ) -> str:
        """
        生成Swift测试文件

        Args:
            test_cases: 测试用例列表
            output_file: 输出文件路径
            test_class_name: 测试类名

        Returns:
            生成的文件路径
        """
        code_lines = [
            "import XCTest",
            "",
            f"class {test_class_name}: XCTestCase {{",
            "",
            "    var app: XCUIApplication!",
            "",
            "    override func setUpWithError() throws {",
            "        continueAfterFailure = false",
            "        app = XCUIApplication()",
            "        app.launch()",
            "    }",
            "",
            "    override func tearDownWithError() throws {",
            "        app.terminate()",
            "    }",
            "",
        ]

        for tc in test_cases:
            test_method = self._generate_test_method(tc)
            code_lines.extend(test_method)
            code_lines.append("")

        code_lines.append("}")

        code = "\n".join(code_lines)

        with open(output_file, "w") as f:
            f.write(code)

        return output_file

    def _generate_test_method(self, test_case: Dict[str, Any]) -> List[str]:
        """生成单个测试方法"""
        test_id = test_case.get("id", "unknownTest")
        title = test_case.get("title", "未命名测试")
        steps = test_case.get("steps", [])

        # 将ID转换为合法的Swift方法名
        method_name = re.sub(r'[^a-zA-Z0-9]', '', test_id)
        if not method_name[0].isalpha():
            method_name = "test" + method_name

        lines = [
            f"    /// {title}",
            f"    func test{method_name}() throws {{",
        ]

        for step in steps:
            action = step.get("action", "")
            element = step.get("element", {})
            value = step.get("value", "")

            swift_code = self._generate_step_code(action, element, value)
            lines.append(f"        {swift_code}")

        # 添加断言
        for assertion in test_case.get("assertions", []):
            assertion_code = self._generate_assertion_code(assertion)
            lines.append(f"        {assertion_code}")

        lines.append("    }")

        return lines

    def _generate_step_code(
        self,
        action: str,
        element: Dict[str, Any],
        value: str = "",
    ) -> str:
        """生成步骤代码"""
        element_type = element.get("type", "button")
        identifier = element.get("identifier", "")
        label = element.get("label", "")

        # 元素查找
        if identifier:
            element_query = f'app.{element_type}s["{identifier}"]'
        elif label:
            element_query = f'app.{element_type}s["{label}"]'
        else:
            index = element.get("index", 0)
            element_query = f'app.{element_type}s.element(boundBy: {index})'

        # 动作代码
        if action == "tap":
            return f'{element_query}.tap()'
        elif action == "doubleTap":
            return f'{element_query}.doubleTap()'
        elif action == "longPress":
            duration = element.get("duration", 1.0)
            return f'{element_query}.press(forDuration: {duration})'
        elif action == "typeText":
            return f'{element_query}.typeText("{value}")'
        elif action == "clearText":
            return f'{element_query}.tap()\n        {element_query}.buttons["Clear text"].tap()'
        elif action == "swipeUp":
            return f'{element_query}.swipeUp()'
        elif action == "swipeDown":
            return f'{element_query}.swipeDown()'
        elif action == "swipeLeft":
            return f'{element_query}.swipeLeft()'
        elif action == "swipeRight":
            return f'{element_query}.swipeRight()'
        elif action == "waitForExistence":
            timeout = element.get("timeout", 10)
            return f'XCTAssertTrue({element_query}.waitForExistence(timeout: {timeout}))'
        else:
            return f'// 未知动作: {action}'

    def _generate_assertion_code(self, assertion: Dict[str, Any]) -> str:
        """生成断言代码"""
        assertion_type = assertion.get("type", "exists")
        element_id = assertion.get("element", "")
        expected = assertion.get("expected_value", "")

        element_query = f'app.otherElements["{element_id}"]'

        if assertion_type == "exists":
            return f'XCTAssertTrue({element_query}.exists)'
        elif assertion_type == "notExists":
            return f'XCTAssertFalse({element_query}.exists)'
        elif assertion_type == "hasValue":
            return f'XCTAssertEqual({element_query}.value as? String, "{expected}")'
        elif assertion_type == "isEnabled":
            return f'XCTAssertTrue({element_query}.isEnabled)'
        elif assertion_type == "isSelected":
            return f'XCTAssertTrue({element_query}.isSelected)'
        else:
            return f'// 未知断言类型: {assertion_type}'
