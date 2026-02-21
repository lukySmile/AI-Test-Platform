# API测试执行器

import json
import time
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import httpx
from concurrent.futures import ThreadPoolExecutor, as_completed


class TestStatus(Enum):
    """测试状态"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class AssertionResult:
    """断言结果"""
    assertion_type: str
    path: str
    expected: Any
    actual: Any
    passed: bool
    message: str = ""


@dataclass
class APITestResult:
    """API测试结果"""
    test_case_id: str
    test_case_title: str
    status: TestStatus
    method: str
    endpoint: str
    request_headers: Dict[str, str]
    request_body: Optional[Dict[str, Any]]
    response_status: int
    response_body: Any
    response_time_ms: float
    assertions: List[AssertionResult] = field(default_factory=list)
    error_message: str = ""
    executed_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["status"] = self.status.value
        result["assertions"] = [asdict(a) for a in self.assertions]
        return result


@dataclass
class APITestSuiteResult:
    """API测试套件结果"""
    suite_name: str
    base_url: str
    total: int
    passed: int
    failed: int
    skipped: int
    error: int
    pass_rate: float
    total_time_ms: float
    results: List[APITestResult]
    started_at: str
    finished_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suite_name": self.suite_name,
            "base_url": self.base_url,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "error": self.error,
            "pass_rate": self.pass_rate,
            "total_time_ms": self.total_time_ms,
            "results": [r.to_dict() for r in self.results],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


class APITestExecutor:
    """API测试执行器"""

    def __init__(
        self,
        base_url: str,
        default_headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        max_workers: int = 5,
    ):
        """
        初始化API测试执行器

        Args:
            base_url: API基础URL
            default_headers: 默认请求头
            timeout: 请求超时时间（秒）
            max_workers: 最大并发数
        """
        self.base_url = base_url.rstrip("/")
        self.default_headers = default_headers or {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self.timeout = timeout
        self.max_workers = max_workers
        self._client = httpx.Client(timeout=timeout)
        self._variables: Dict[str, Any] = {}  # 用于存储变量（如token）

    def set_variable(self, name: str, value: Any):
        """设置变量"""
        self._variables[name] = value

    def get_variable(self, name: str) -> Any:
        """获取变量"""
        return self._variables.get(name)

    def _replace_variables(self, text: str) -> str:
        """替换文本中的变量占位符"""
        if not isinstance(text, str):
            return text

        pattern = r'\{(\w+)\}'
        def replacer(match):
            var_name = match.group(1)
            return str(self._variables.get(var_name, match.group(0)))

        return re.sub(pattern, replacer, text)

    def _process_dict_variables(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理字典中的变量"""
        if not data:
            return data

        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self._replace_variables(value)
            elif isinstance(value, dict):
                result[key] = self._process_dict_variables(value)
            else:
                result[key] = value
        return result

    def execute_single(self, test_case: Dict[str, Any]) -> APITestResult:
        """
        执行单个API测试用例

        Args:
            test_case: 测试用例字典

        Returns:
            测试结果
        """
        test_id = test_case.get("id", "unknown")
        test_title = test_case.get("title", "未命名测试")
        method = test_case.get("method", "GET").upper()
        endpoint = self._replace_variables(test_case.get("endpoint", ""))

        # 构建请求
        url = f"{self.base_url}{endpoint}"
        headers = {**self.default_headers}
        if test_case.get("headers"):
            headers.update(self._process_dict_variables(test_case["headers"]))

        query_params = self._process_dict_variables(test_case.get("query_params", {}))
        request_body = self._process_dict_variables(test_case.get("request_body", {}))

        # 执行请求
        start_time = time.time()
        try:
            response = self._client.request(
                method=method,
                url=url,
                headers=headers,
                params=query_params if query_params else None,
                json=request_body if request_body and method in ["POST", "PUT", "PATCH"] else None,
            )

            response_time = (time.time() - start_time) * 1000  # 转换为毫秒

            # 解析响应
            try:
                response_body = response.json()
            except json.JSONDecodeError:
                response_body = response.text

            # 执行断言
            assertions = self._run_assertions(
                test_case,
                response.status_code,
                response_body
            )

            # 提取变量（用于后续请求）
            self._extract_variables(test_case.get("extract", {}), response_body)

            # 判断测试状态
            all_passed = all(a.passed for a in assertions)
            status = TestStatus.PASSED if all_passed else TestStatus.FAILED

            return APITestResult(
                test_case_id=test_id,
                test_case_title=test_title,
                status=status,
                method=method,
                endpoint=endpoint,
                request_headers=headers,
                request_body=request_body,
                response_status=response.status_code,
                response_body=response_body,
                response_time_ms=response_time,
                assertions=assertions,
            )

        except httpx.TimeoutException as e:
            return APITestResult(
                test_case_id=test_id,
                test_case_title=test_title,
                status=TestStatus.ERROR,
                method=method,
                endpoint=endpoint,
                request_headers=headers,
                request_body=request_body,
                response_status=0,
                response_body=None,
                response_time_ms=(time.time() - start_time) * 1000,
                error_message=f"请求超时: {str(e)}",
            )
        except Exception as e:
            return APITestResult(
                test_case_id=test_id,
                test_case_title=test_title,
                status=TestStatus.ERROR,
                method=method,
                endpoint=endpoint,
                request_headers=headers,
                request_body=request_body,
                response_status=0,
                response_body=None,
                response_time_ms=(time.time() - start_time) * 1000,
                error_message=f"执行错误: {str(e)}",
            )

    def _run_assertions(
        self,
        test_case: Dict[str, Any],
        status_code: int,
        response_body: Any,
    ) -> List[AssertionResult]:
        """执行断言"""
        assertions = []

        # 状态码断言
        expected_status = test_case.get("expected_status", 200)
        assertions.append(AssertionResult(
            assertion_type="status_code",
            path="status_code",
            expected=expected_status,
            actual=status_code,
            passed=status_code == expected_status,
            message=f"状态码{'匹配' if status_code == expected_status else '不匹配'}"
        ))

        # 响应体断言
        expected_response = test_case.get("expected_response", {})
        for assertion in expected_response.get("assertions", []):
            result = self._evaluate_assertion(assertion, response_body)
            assertions.append(result)

        return assertions

    def _evaluate_assertion(
        self,
        assertion: Dict[str, Any],
        response_body: Any,
    ) -> AssertionResult:
        """评估单个断言"""
        path = assertion.get("path", "")
        operator = assertion.get("operator", "exists")
        expected = assertion.get("value")

        # 使用JSONPath提取值
        actual = self._extract_json_path(response_body, path)

        passed = False
        message = ""

        if operator == "exists":
            passed = actual is not None
            message = f"字段 {path} {'存在' if passed else '不存在'}"
        elif operator == "equals":
            passed = actual == expected
            message = f"字段 {path} 值{'匹配' if passed else '不匹配'}"
        elif operator == "contains":
            passed = expected in str(actual) if actual else False
            message = f"字段 {path} {'包含' if passed else '不包含'} '{expected}'"
        elif operator == "not_equals":
            passed = actual != expected
            message = f"字段 {path} 值{'不相等' if passed else '相等'}"
        elif operator == "greater_than":
            passed = actual > expected if actual is not None else False
            message = f"字段 {path} {'>' if passed else '<='} {expected}"
        elif operator == "less_than":
            passed = actual < expected if actual is not None else False
            message = f"字段 {path} {'<' if passed else '>='} {expected}"
        elif operator == "type_is":
            type_map = {"string": str, "int": int, "float": float, "bool": bool, "list": list, "dict": dict}
            expected_type = type_map.get(expected)
            passed = isinstance(actual, expected_type) if expected_type else False
            message = f"字段 {path} 类型{'匹配' if passed else '不匹配'}"
        elif operator == "matches":
            passed = bool(re.match(expected, str(actual))) if actual else False
            message = f"字段 {path} {'匹配' if passed else '不匹配'}正则"

        return AssertionResult(
            assertion_type=operator,
            path=path,
            expected=expected,
            actual=actual,
            passed=passed,
            message=message
        )

    def _extract_json_path(self, data: Any, path: str) -> Any:
        """简单的JSONPath提取"""
        if not path or not data:
            return None

        # 支持 $.field.subfield 或 field.subfield 格式
        path = path.lstrip("$").lstrip(".")

        # 处理根数组索引 [0].field 格式
        if path.startswith("["):
            root_match = re.match(r'\[(\d+)\]\.?(.*)', path)
            if root_match:
                index = int(root_match.group(1))
                remaining_path = root_match.group(2)
                if isinstance(data, list) and len(data) > index:
                    if remaining_path:
                        return self._extract_json_path(data[index], remaining_path)
                    return data[index]
                return None

        parts = path.split(".")

        current = data
        for part in parts:
            if not part:
                continue

            # 处理数组索引 field[0]
            match = re.match(r'(\w+)\[(\d+)\]', part)
            if match:
                field_name = match.group(1)
                index = int(match.group(2))
                if isinstance(current, dict) and field_name in current:
                    current = current[field_name]
                    if isinstance(current, list) and len(current) > index:
                        current = current[index]
                    else:
                        return None
                else:
                    return None
            # 处理纯数组索引 [0]
            elif part.startswith("["):
                idx_match = re.match(r'\[(\d+)\]', part)
                if idx_match and isinstance(current, list):
                    index = int(idx_match.group(1))
                    if len(current) > index:
                        current = current[index]
                    else:
                        return None
                else:
                    return None
            elif isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current

    def _extract_variables(self, extract_config: Dict[str, str], response_body: Any):
        """从响应中提取变量"""
        for var_name, path in extract_config.items():
            value = self._extract_json_path(response_body, path)
            if value is not None:
                self._variables[var_name] = value

    def execute_suite(
        self,
        test_cases: List[Dict[str, Any]],
        suite_name: str = "API测试套件",
        parallel: bool = False,
    ) -> APITestSuiteResult:
        """
        执行测试套件

        Args:
            test_cases: 测试用例列表
            suite_name: 套件名称
            parallel: 是否并行执行

        Returns:
            测试套件结果
        """
        started_at = datetime.now().isoformat()
        results: List[APITestResult] = []

        if parallel:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(self.execute_single, tc): tc
                    for tc in test_cases
                }
                for future in as_completed(futures):
                    results.append(future.result())
        else:
            for test_case in test_cases:
                result = self.execute_single(test_case)
                results.append(result)

        finished_at = datetime.now().isoformat()

        # 统计
        passed = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in results if r.status == TestStatus.FAILED)
        skipped = sum(1 for r in results if r.status == TestStatus.SKIPPED)
        error = sum(1 for r in results if r.status == TestStatus.ERROR)
        total = len(results)
        total_time = sum(r.response_time_ms for r in results)
        pass_rate = (passed / total * 100) if total > 0 else 0

        return APITestSuiteResult(
            suite_name=suite_name,
            base_url=self.base_url,
            total=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            error=error,
            pass_rate=round(pass_rate, 2),
            total_time_ms=round(total_time, 2),
            results=results,
            started_at=started_at,
            finished_at=finished_at,
        )

    def close(self):
        """关闭执行器"""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
