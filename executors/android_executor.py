# Android模拟器测试执行器

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


class AndroidTestStatus(Enum):
    """Android测试状态"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class AndroidDevice:
    """Android设备信息"""
    device_id: str
    model: str
    android_version: str
    state: str  # device, offline, unauthorized
    is_emulator: bool

    @classmethod
    def from_adb(cls, line: str) -> Optional["AndroidDevice"]:
        """从adb devices输出解析设备信息"""
        parts = line.strip().split()
        if len(parts) < 2:
            return None

        device_id = parts[0]
        state = parts[1]

        # 判断是否为模拟器
        is_emulator = device_id.startswith("emulator-")

        return cls(
            device_id=device_id,
            model="",  # 后续通过getprop获取
            android_version="",
            state=state,
            is_emulator=is_emulator,
        )


@dataclass
class AndroidTestCaseResult:
    """Android测试用例结果"""
    test_case_id: str
    test_case_title: str
    test_class: str
    test_method: str
    status: AndroidTestStatus
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
class AndroidTestSuiteResult:
    """Android测试套件结果"""
    suite_name: str
    device_name: str
    device_id: str
    android_version: str
    package_name: str
    total: int
    passed: int
    failed: int
    skipped: int
    error: int
    pass_rate: float
    total_duration_seconds: float
    results: List[AndroidTestCaseResult]
    output_dir: str
    started_at: str
    finished_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suite_name": self.suite_name,
            "device_name": self.device_name,
            "device_id": self.device_id,
            "android_version": self.android_version,
            "package_name": self.package_name,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "error": self.error,
            "pass_rate": self.pass_rate,
            "total_duration_seconds": self.total_duration_seconds,
            "results": [r.to_dict() for r in self.results],
            "output_dir": self.output_dir,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


class AndroidTestExecutor:
    """Android模拟器测试执行器"""

    def __init__(
        self,
        project_path: str,
        output_dir: str = "./test_output",
        adb_path: str = "adb",
    ):
        """
        初始化Android测试执行器

        Args:
            project_path: Android项目路径
            output_dir: 测试输出目录
            adb_path: adb命令路径
        """
        self.project_path = project_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.adb_path = adb_path

    def list_devices(self) -> List[AndroidDevice]:
        """列出所有已连接的Android设备/模拟器"""
        result = subprocess.run(
            [self.adb_path, "devices"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"获取设备列表失败: {result.stderr}")

        devices = []
        lines = result.stdout.strip().split("\n")[1:]  # 跳过第一行

        for line in lines:
            if not line.strip():
                continue
            device = AndroidDevice.from_adb(line)
            if device:
                # 获取设备详细信息
                self._fill_device_info(device)
                devices.append(device)

        return devices

    def _fill_device_info(self, device: AndroidDevice):
        """填充设备详细信息"""
        if device.state != "device":
            return

        # 获取设备型号
        result = subprocess.run(
            [self.adb_path, "-s", device.device_id, "shell", "getprop", "ro.product.model"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            device.model = result.stdout.strip()

        # 获取Android版本
        result = subprocess.run(
            [self.adb_path, "-s", device.device_id, "shell", "getprop", "ro.build.version.release"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            device.android_version = result.stdout.strip()

    def list_emulators(self) -> List[str]:
        """列出所有可用的AVD"""
        result = subprocess.run(
            ["emulator", "-list-avds"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return []

        return [avd.strip() for avd in result.stdout.strip().split("\n") if avd.strip()]

    def start_emulator(self, avd_name: str, wait_for_boot: bool = True) -> bool:
        """启动模拟器"""
        # 后台启动模拟器
        process = subprocess.Popen(
            ["emulator", "-avd", avd_name, "-no-snapshot-load"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if not wait_for_boot:
            return True

        # 等待模拟器启动
        max_wait = 120  # 最多等待120秒
        start_time = time.time()

        while time.time() - start_time < max_wait:
            result = subprocess.run(
                [self.adb_path, "shell", "getprop", "sys.boot_completed"],
                capture_output=True,
                text=True
            )
            if result.stdout.strip() == "1":
                return True
            time.sleep(2)

        return False

    def shutdown_emulator(self, device_id: str) -> bool:
        """关闭模拟器"""
        result = subprocess.run(
            [self.adb_path, "-s", device_id, "emu", "kill"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0

    def install_app(self, device_id: str, apk_path: str, reinstall: bool = True) -> bool:
        """在设备上安装应用"""
        cmd = [self.adb_path, "-s", device_id, "install"]
        if reinstall:
            cmd.append("-r")
        cmd.append(apk_path)

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0 or "Failure" in result.stdout:
            print(f"安装应用失败: {result.stdout} {result.stderr}")
            return False
        return True

    def uninstall_app(self, device_id: str, package_name: str) -> bool:
        """卸载应用"""
        result = subprocess.run(
            [self.adb_path, "-s", device_id, "uninstall", package_name],
            capture_output=True,
            text=True
        )
        return result.returncode == 0

    def clear_app_data(self, device_id: str, package_name: str) -> bool:
        """清除应用数据"""
        result = subprocess.run(
            [self.adb_path, "-s", device_id, "shell", "pm", "clear", package_name],
            capture_output=True,
            text=True
        )
        return result.returncode == 0

    def take_screenshot(self, device_id: str, output_path: str) -> bool:
        """截图"""
        device_path = "/sdcard/screenshot_temp.png"

        # 在设备上截图
        result = subprocess.run(
            [self.adb_path, "-s", device_id, "shell", "screencap", device_path],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return False

        # 拉取到本地
        result = subprocess.run(
            [self.adb_path, "-s", device_id, "pull", device_path, output_path],
            capture_output=True,
            text=True
        )

        # 清理设备上的临时文件
        subprocess.run(
            [self.adb_path, "-s", device_id, "shell", "rm", device_path],
            capture_output=True
        )

        return result.returncode == 0

    def start_screen_record(self, device_id: str, output_path: str, time_limit: int = 180) -> subprocess.Popen:
        """开始录屏"""
        device_path = "/sdcard/screenrecord_temp.mp4"
        process = subprocess.Popen(
            [self.adb_path, "-s", device_id, "shell", "screenrecord",
             "--time-limit", str(time_limit), device_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return process

    def execute_tests(
        self,
        device_id: str,
        test_package: str,
        app_package: str,
        test_class: Optional[str] = None,
        test_method: Optional[str] = None,
        timeout: int = 600,
        use_gradle: bool = True,
    ) -> AndroidTestSuiteResult:
        """
        执行Android测试

        Args:
            device_id: 设备ID
            test_package: 测试包名
            app_package: 应用包名
            test_class: 测试类（可选，指定则只运行该类）
            test_method: 测试方法（可选，指定则只运行该方法）
            timeout: 超时时间（秒）
            use_gradle: 是否使用Gradle执行

        Returns:
            测试套件结果
        """
        started_at = datetime.now().isoformat()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_dir = str(self.output_dir / f"TestResults_{timestamp}")
        os.makedirs(result_dir, exist_ok=True)

        # 获取设备信息
        devices = self.list_devices()
        device = next((d for d in devices if d.device_id == device_id), None)
        device_name = device.model if device else device_id
        android_version = device.android_version if device else ""

        if use_gradle:
            output = self._execute_with_gradle(
                device_id, test_class, test_method, timeout
            )
        else:
            output = self._execute_with_am_instrument(
                device_id, test_package, test_class, test_method, timeout
            )

        finished_at = datetime.now().isoformat()

        # 解析测试结果
        test_results = self._parse_test_output(output)

        # 统计
        passed = sum(1 for r in test_results if r.status == AndroidTestStatus.PASSED)
        failed = sum(1 for r in test_results if r.status == AndroidTestStatus.FAILED)
        skipped = sum(1 for r in test_results if r.status == AndroidTestStatus.SKIPPED)
        error = sum(1 for r in test_results if r.status == AndroidTestStatus.ERROR)
        total = len(test_results)
        total_duration = sum(r.duration_seconds for r in test_results)
        pass_rate = (passed / total * 100) if total > 0 else 0

        return AndroidTestSuiteResult(
            suite_name=test_package,
            device_name=device_name,
            device_id=device_id,
            android_version=android_version,
            package_name=app_package,
            total=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            error=error,
            pass_rate=round(pass_rate, 2),
            total_duration_seconds=round(total_duration, 2),
            results=test_results,
            output_dir=result_dir,
            started_at=started_at,
            finished_at=finished_at,
        )

    def _execute_with_gradle(
        self,
        device_id: str,
        test_class: Optional[str],
        test_method: Optional[str],
        timeout: int,
    ) -> str:
        """使用Gradle执行测试"""
        cmd = ["./gradlew", "connectedDebugAndroidTest"]

        if test_class:
            if test_method:
                cmd.extend(["-Pandroid.testInstrumentationRunnerArguments.class",
                           f"={test_class}#{test_method}"])
            else:
                cmd.extend(["-Pandroid.testInstrumentationRunnerArguments.class",
                           f"={test_class}"])

        # 指定设备
        cmd.extend([f"-Pandroid.injected.build.serial={device_id}"])

        print(f"执行命令: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.project_path
            )
            return result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return "测试执行超时"

    def _execute_with_am_instrument(
        self,
        device_id: str,
        test_package: str,
        test_class: Optional[str],
        test_method: Optional[str],
        timeout: int,
    ) -> str:
        """使用am instrument执行测试"""
        cmd = [
            self.adb_path, "-s", device_id, "shell",
            "am", "instrument", "-w"
        ]

        if test_class:
            if test_method:
                cmd.extend(["-e", "class", f"{test_class}#{test_method}"])
            else:
                cmd.extend(["-e", "class", test_class])

        cmd.append(f"{test_package}/androidx.test.runner.AndroidJUnitRunner")

        print(f"执行命令: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return "测试执行超时"

    def _parse_test_output(self, output: str) -> List[AndroidTestCaseResult]:
        """解析测试输出"""
        results = []

        # 匹配Gradle输出格式
        # > TestClass > testMethod PASSED/FAILED
        gradle_pattern = r">\s*(\w+)\s*>\s*(\w+)\s+(PASSED|FAILED)"

        for match in re.finditer(gradle_pattern, output):
            test_class = match.group(1)
            test_method = match.group(2)
            status_str = match.group(3)

            status = AndroidTestStatus.PASSED if status_str == "PASSED" else AndroidTestStatus.FAILED

            results.append(AndroidTestCaseResult(
                test_case_id=f"{test_class}_{test_method}",
                test_case_title=f"{test_class}.{test_method}",
                test_class=test_class,
                test_method=test_method,
                status=status,
                duration_seconds=0,
            ))

        # 如果没有匹配到Gradle格式，尝试am instrument格式
        if not results:
            # 匹配 am instrument 输出格式
            # OK (10 tests)
            # FAILURES!!!
            # Tests run: 10, Failures: 2, Errors: 1
            am_pattern = r"(\w+[\w.]*)\s*#\s*(\w+)\s*:\s*(OK|FAILURE|ERROR)"

            for match in re.finditer(am_pattern, output):
                test_class = match.group(1)
                test_method = match.group(2)
                status_str = match.group(3)

                if status_str == "OK":
                    status = AndroidTestStatus.PASSED
                elif status_str == "FAILURE":
                    status = AndroidTestStatus.FAILED
                else:
                    status = AndroidTestStatus.ERROR

                results.append(AndroidTestCaseResult(
                    test_case_id=f"{test_class}_{test_method}",
                    test_case_title=f"{test_class}.{test_method}",
                    test_class=test_class,
                    test_method=test_method,
                    status=status,
                    duration_seconds=0,
                ))

        return results

    def generate_test_file(
        self,
        test_cases: List[Dict[str, Any]],
        output_file: str,
        test_class_name: str = "GeneratedUITests",
        package_name: str = "com.example.app.test",
    ) -> str:
        """
        生成Kotlin测试文件

        Args:
            test_cases: 测试用例列表
            output_file: 输出文件路径
            test_class_name: 测试类名
            package_name: 包名

        Returns:
            生成的文件路径
        """
        code_lines = [
            f"package {package_name}",
            "",
            "import androidx.test.espresso.Espresso.onView",
            "import androidx.test.espresso.action.ViewActions.*",
            "import androidx.test.espresso.assertion.ViewAssertions.*",
            "import androidx.test.espresso.matcher.ViewMatchers.*",
            "import androidx.test.ext.junit.rules.ActivityScenarioRule",
            "import androidx.test.ext.junit.runners.AndroidJUnit4",
            "import org.junit.Rule",
            "import org.junit.Test",
            "import org.junit.runner.RunWith",
            "",
            "@RunWith(AndroidJUnit4::class)",
            f"class {test_class_name} {{",
            "",
            "    @get:Rule",
            "    val activityRule = ActivityScenarioRule(MainActivity::class.java)",
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

        # 将ID转换为合法的Kotlin方法名
        method_name = re.sub(r'[^a-zA-Z0-9]', '', test_id)
        if not method_name[0].isalpha():
            method_name = "test" + method_name

        lines = [
            f"    /**",
            f"     * {title}",
            f"     */",
            f"    @Test",
            f"    fun test{method_name}() {{",
        ]

        for step in steps:
            action = step.get("action", "")
            element = step.get("element", {})
            value = step.get("value", "")

            kotlin_code = self._generate_step_code(action, element, value)
            lines.append(f"        {kotlin_code}")

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
        element_id = element.get("id", "")
        text = element.get("text", "")
        content_desc = element.get("content_desc", "")

        # 元素查找
        if element_id:
            element_query = f'onView(withId(R.id.{element_id}))'
        elif text:
            element_query = f'onView(withText("{text}"))'
        elif content_desc:
            element_query = f'onView(withContentDescription("{content_desc}"))'
        else:
            index = element.get("index", 0)
            element_type = element.get("type", "view")
            element_query = f'onView(isAssignableFrom({element_type.capitalize()}::class.java))'

        # 动作代码
        if action == "click":
            return f'{element_query}.perform(click())'
        elif action == "longClick":
            return f'{element_query}.perform(longClick())'
        elif action == "doubleClick":
            return f'{element_query}.perform(doubleClick())'
        elif action == "typeText":
            return f'{element_query}.perform(typeText("{value}"))'
        elif action == "replaceText":
            return f'{element_query}.perform(replaceText("{value}"))'
        elif action == "clearText":
            return f'{element_query}.perform(clearText())'
        elif action == "swipeUp":
            return f'{element_query}.perform(swipeUp())'
        elif action == "swipeDown":
            return f'{element_query}.perform(swipeDown())'
        elif action == "swipeLeft":
            return f'{element_query}.perform(swipeLeft())'
        elif action == "swipeRight":
            return f'{element_query}.perform(swipeRight())'
        elif action == "scrollTo":
            return f'{element_query}.perform(scrollTo())'
        else:
            return f'// 未知动作: {action}'

    def _generate_assertion_code(self, assertion: Dict[str, Any]) -> str:
        """生成断言代码"""
        assertion_type = assertion.get("type", "isDisplayed")
        element_id = assertion.get("element", "")
        expected = assertion.get("expected_value", "")

        element_query = f'onView(withId(R.id.{element_id}))'

        if assertion_type == "isDisplayed":
            return f'{element_query}.check(matches(isDisplayed()))'
        elif assertion_type == "isNotDisplayed":
            return f'{element_query}.check(matches(not(isDisplayed())))'
        elif assertion_type == "hasText":
            return f'{element_query}.check(matches(withText("{expected}")))'
        elif assertion_type == "isEnabled":
            return f'{element_query}.check(matches(isEnabled()))'
        elif assertion_type == "isChecked":
            return f'{element_query}.check(matches(isChecked()))'
        elif assertion_type == "isNotChecked":
            return f'{element_query}.check(matches(isNotChecked()))'
        else:
            return f'// 未知断言类型: {assertion_type}'

    def get_logcat(self, device_id: str, tag: Optional[str] = None, lines: int = 100) -> str:
        """获取logcat日志"""
        cmd = [self.adb_path, "-s", device_id, "logcat", "-d", "-t", str(lines)]

        if tag:
            cmd.extend(["-s", tag])

        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout
