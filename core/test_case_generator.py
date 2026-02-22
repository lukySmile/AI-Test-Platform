# 基于测试设计方法的自动测试用例生成器
# 支持：等价类划分、边界值分析、错误猜测、正交试验等

import re
import random
import string
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from itertools import product

from parsers.swagger_parser import APISpec, APIEndpoint, APIParameter


class TestCaseType(Enum):
    """测试用例类型"""
    POSITIVE = "positive"           # 正向测试
    NEGATIVE = "negative"           # 负向测试
    BOUNDARY = "boundary"           # 边界值测试
    EQUIVALENCE = "equivalence"     # 等价类测试
    ERROR_GUESS = "error_guess"     # 错误猜测
    SECURITY = "security"           # 安全测试
    PERFORMANCE = "performance"     # 性能测试


class TestPriority(Enum):
    """测试优先级"""
    P0 = "P0"  # 核心功能
    P1 = "P1"  # 重要功能
    P2 = "P2"  # 一般功能
    P3 = "P3"  # 边缘场景


@dataclass
class GeneratedTestCase:
    """生成的测试用例"""
    id: str
    title: str
    description: str
    test_type: TestCaseType
    priority: TestPriority
    endpoint: str
    method: str

    # 请求数据
    headers: Dict[str, str] = field(default_factory=dict)
    path_params: Dict[str, Any] = field(default_factory=dict)
    query_params: Dict[str, Any] = field(default_factory=dict)
    request_body: Optional[Dict[str, Any]] = None

    # 预期结果
    expected_status: int = 200
    expected_response: Optional[Dict[str, Any]] = None
    assertions: List[Dict[str, Any]] = field(default_factory=list)

    # 元数据
    tags: List[str] = field(default_factory=list)
    preconditions: List[str] = field(default_factory=list)
    design_method: str = ""  # 设计方法说明

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["test_type"] = self.test_type.value
        result["priority"] = self.priority.value
        return result


class TestDataGenerator:
    """测试数据生成器"""

    # 类型对应的有效值和边界值
    TYPE_VALUES = {
        "string": {
            "valid": ["test", "hello", "example"],
            "invalid": [None, "", 123, True, [], {}],
            "boundary": ["", "a", "a" * 255, "a" * 256],
            "special": ["<script>alert(1)</script>", "'; DROP TABLE users;--",
                       "test\n\r\t", "测试中文", "🎉emoji", " spaces "],
        },
        "integer": {
            "valid": [1, 100, 999],
            "invalid": [None, "", "abc", 1.5, True, [], {}],
            "boundary": [0, 1, -1, 2147483647, -2147483648, 2147483648],
            "special": [0, -0],
        },
        "number": {
            "valid": [1.0, 3.14, 100.5],
            "invalid": [None, "", "abc", True, [], {}],
            "boundary": [0.0, 0.001, -0.001, 1e10, -1e10, float('inf')],
            "special": [0.0, -0.0],
        },
        "boolean": {
            "valid": [True, False],
            "invalid": [None, "", 0, 1, "true", "false", [], {}],
            "boundary": [],
            "special": [],
        },
        "array": {
            "valid": [[], [1], [1, 2, 3]],
            "invalid": [None, "", 123, True, {}],
            "boundary": [[], list(range(100)), list(range(1000))],
            "special": [[None], [{}], [[]]],
        },
        "object": {
            "valid": [{}, {"key": "value"}],
            "invalid": [None, "", 123, True, []],
            "boundary": [{}, {f"key{i}": i for i in range(100)}],
            "special": [{"": ""}, {None: None}],
        },
    }

    # 常见字段的特定测试值
    FIELD_SPECIFIC_VALUES = {
        "email": {
            "valid": ["test@example.com", "user.name@domain.org"],
            "invalid": ["invalid", "@domain.com", "user@", "user@.com", "user@domain", ""],
            "boundary": ["a@b.co", "a" * 64 + "@example.com"],
        },
        "phone": {
            "valid": ["13800138000", "18612345678", "+8613800138000"],
            "invalid": ["123", "abc", "1380013800", "138001380001", ""],
            "boundary": ["10000000000", "19999999999"],
        },
        "password": {
            "valid": ["Password123", "Abcd@1234", "Test#Pass1"],
            "invalid": ["123", "abc", "12345678", "password", ""],
            "boundary": ["Aa1@56", "Aa1@" + "x" * 100],
        },
        "username": {
            "valid": ["user123", "test_user", "admin"],
            "invalid": ["", "a", "user name", "user@name", "<script>"],
            "boundary": ["ab", "a" * 50],
        },
        "id": {
            "valid": [1, 100, 9999],
            "invalid": [0, -1, "", None, "abc"],
            "boundary": [1, 2147483647],
        },
        "page": {
            "valid": [1, 2, 10],
            "invalid": [0, -1, "", None, "abc"],
            "boundary": [1, 1000, 10000],
        },
        "size": {
            "valid": [10, 20, 50],
            "invalid": [0, -1, "", None, 1001],
            "boundary": [1, 100, 500],
        },
        "date": {
            "valid": ["2024-01-01", "2024-12-31"],
            "invalid": ["", "2024", "01-01-2024", "2024-13-01", "2024-01-32"],
            "boundary": ["1970-01-01", "2099-12-31"],
        },
        "url": {
            "valid": ["https://example.com", "http://localhost:8080/path"],
            "invalid": ["", "example.com", "ftp://example.com", "://invalid"],
            "boundary": ["http://a.co", "https://" + "a" * 200 + ".com"],
        },
        "age": {
            "valid": [18, 25, 60],
            "invalid": [-1, 0, 200, "", None],
            "boundary": [1, 17, 18, 120, 121],
        },
        "amount": {
            "valid": [100, 1000.50, 9999.99],
            "invalid": [-1, "", None, "abc"],
            "boundary": [0, 0.01, 999999.99, 1000000],
        },
    }

    @classmethod
    def get_valid_value(cls, param_type: str, param_name: str = "") -> Any:
        """获取有效值"""
        # 先检查字段特定值
        name_lower = param_name.lower()
        for field_key, values in cls.FIELD_SPECIFIC_VALUES.items():
            if field_key in name_lower:
                return random.choice(values["valid"])

        # 使用类型默认值
        type_lower = param_type.lower()
        if type_lower in cls.TYPE_VALUES:
            return random.choice(cls.TYPE_VALUES[type_lower]["valid"])

        return "test_value"

    @classmethod
    def get_invalid_values(cls, param_type: str, param_name: str = "") -> List[Any]:
        """获取无效值列表"""
        name_lower = param_name.lower()
        for field_key, values in cls.FIELD_SPECIFIC_VALUES.items():
            if field_key in name_lower:
                return values["invalid"]

        type_lower = param_type.lower()
        if type_lower in cls.TYPE_VALUES:
            return cls.TYPE_VALUES[type_lower]["invalid"]

        return [None, "", 123]

    @classmethod
    def get_boundary_values(cls, param_type: str, param_name: str = "") -> List[Any]:
        """获取边界值列表"""
        name_lower = param_name.lower()
        for field_key, values in cls.FIELD_SPECIFIC_VALUES.items():
            if field_key in name_lower:
                return values.get("boundary", [])

        type_lower = param_type.lower()
        if type_lower in cls.TYPE_VALUES:
            return cls.TYPE_VALUES[type_lower]["boundary"]

        return []

    @classmethod
    def get_special_values(cls, param_type: str) -> List[Any]:
        """获取特殊值列表（用于安全测试）"""
        type_lower = param_type.lower()
        if type_lower in cls.TYPE_VALUES:
            return cls.TYPE_VALUES[type_lower].get("special", [])
        return []


class APITestCaseGenerator:
    """API测试用例生成器"""

    def __init__(self, api_spec: APISpec):
        """
        初始化生成器

        Args:
            api_spec: 解析后的API规范
        """
        self.api_spec = api_spec
        self.case_counter = 0

    def generate_all(self) -> Dict[str, Any]:
        """
        为所有端点生成测试用例

        Returns:
            包含所有测试用例的字典
        """
        result = {
            "api_name": self.api_spec.title,
            "api_version": self.api_spec.version,
            "base_url": self.api_spec.base_url,
            "generated_at": datetime.now().isoformat(),
            "test_suites": [],
            "summary": {
                "total_endpoints": len(self.api_spec.endpoints),
                "total_cases": 0,
                "by_type": {},
                "by_priority": {},
            }
        }

        # 按tag分组
        tag_groups: Dict[str, List[APIEndpoint]] = {}
        for endpoint in self.api_spec.endpoints:
            tag = endpoint.tags[0] if endpoint.tags else "default"
            if tag not in tag_groups:
                tag_groups[tag] = []
            tag_groups[tag].append(endpoint)

        # 为每个分组生成测试套件
        for tag, endpoints in tag_groups.items():
            suite = {
                "suite_name": tag,
                "description": f"{tag}模块测试用例",
                "test_cases": []
            }

            for endpoint in endpoints:
                cases = self.generate_for_endpoint(endpoint)
                suite["test_cases"].extend([c.to_dict() for c in cases])

            result["test_suites"].append(suite)
            result["summary"]["total_cases"] += len(suite["test_cases"])

        # 统计
        for suite in result["test_suites"]:
            for case in suite["test_cases"]:
                test_type = case["test_type"]
                priority = case["priority"]
                result["summary"]["by_type"][test_type] = result["summary"]["by_type"].get(test_type, 0) + 1
                result["summary"]["by_priority"][priority] = result["summary"]["by_priority"].get(priority, 0) + 1

        return result

    def generate_for_endpoint(self, endpoint: APIEndpoint) -> List[GeneratedTestCase]:
        """
        为单个端点生成测试用例

        Args:
            endpoint: API端点

        Returns:
            测试用例列表
        """
        cases = []

        # 1. 正向测试 - 基本成功场景
        cases.extend(self._generate_positive_cases(endpoint))

        # 2. 等价类测试
        cases.extend(self._generate_equivalence_cases(endpoint))

        # 3. 边界值测试
        cases.extend(self._generate_boundary_cases(endpoint))

        # 4. 错误猜测测试
        cases.extend(self._generate_error_guess_cases(endpoint))

        # 5. 安全测试
        cases.extend(self._generate_security_cases(endpoint))

        return cases

    def _generate_case_id(self) -> str:
        """生成用例ID"""
        self.case_counter += 1
        return f"TC_{self.case_counter:04d}"

    def _generate_positive_cases(self, endpoint: APIEndpoint) -> List[GeneratedTestCase]:
        """生成正向测试用例"""
        cases = []

        # 基本成功场景
        path_params, query_params, headers, body = self._build_valid_request(endpoint)

        case = GeneratedTestCase(
            id=self._generate_case_id(),
            title=f"{endpoint.method} {endpoint.path} - 正常请求成功",
            description=f"验证{endpoint.summary or endpoint.path}接口正常调用成功",
            test_type=TestCaseType.POSITIVE,
            priority=TestPriority.P0,
            endpoint=endpoint.path,
            method=endpoint.method,
            headers=headers,
            path_params=path_params,
            query_params=query_params,
            request_body=body,
            expected_status=200,
            assertions=[
                {"type": "status_code", "expected": 200},
                {"type": "response_time", "max_ms": 3000},
            ],
            tags=endpoint.tags,
            design_method="正向测试 - 有效等价类",
        )
        cases.append(case)

        # 如果有可选参数，生成只有必填参数的用例
        required_only = self._has_optional_params(endpoint)
        if required_only:
            path_params, query_params, headers, body = self._build_valid_request(endpoint, required_only=True)
            case = GeneratedTestCase(
                id=self._generate_case_id(),
                title=f"{endpoint.method} {endpoint.path} - 仅必填参数",
                description="验证只传必填参数时接口正常工作",
                test_type=TestCaseType.POSITIVE,
                priority=TestPriority.P1,
                endpoint=endpoint.path,
                method=endpoint.method,
                headers=headers,
                path_params=path_params,
                query_params=query_params,
                request_body=body,
                expected_status=200,
                assertions=[
                    {"type": "status_code", "expected": 200},
                ],
                tags=endpoint.tags,
                design_method="正向测试 - 最小有效输入",
            )
            cases.append(case)

        return cases

    def _generate_equivalence_cases(self, endpoint: APIEndpoint) -> List[GeneratedTestCase]:
        """生成等价类测试用例"""
        cases = []

        # 为每个参数生成无效等价类测试
        for param in endpoint.parameters:
            if param.location in ["query", "path"]:
                invalid_values = TestDataGenerator.get_invalid_values(param.param_type, param.name)

                for invalid_value in invalid_values[:3]:  # 限制数量
                    path_params, query_params, headers, body = self._build_valid_request(endpoint)

                    # 替换为无效值
                    if param.location == "query":
                        query_params[param.name] = invalid_value
                    elif param.location == "path":
                        path_params[param.name] = invalid_value

                    case = GeneratedTestCase(
                        id=self._generate_case_id(),
                        title=f"{endpoint.method} {endpoint.path} - {param.name}参数无效值({type(invalid_value).__name__})",
                        description=f"验证{param.name}参数传入无效值{repr(invalid_value)}时的错误处理",
                        test_type=TestCaseType.EQUIVALENCE,
                        priority=TestPriority.P1 if param.required else TestPriority.P2,
                        endpoint=endpoint.path,
                        method=endpoint.method,
                        headers=headers,
                        path_params=path_params,
                        query_params=query_params,
                        request_body=body,
                        expected_status=400,
                        assertions=[
                            {"type": "status_code", "expected": 400},
                            {"type": "response_contains", "field": "error"},
                        ],
                        tags=endpoint.tags,
                        design_method=f"等价类划分 - {param.name}无效等价类",
                    )
                    cases.append(case)

        # 必填参数缺失测试
        for param in endpoint.parameters:
            if param.required and param.location in ["query", "path"]:
                path_params, query_params, headers, body = self._build_valid_request(endpoint)

                # 移除必填参数
                if param.location == "query":
                    query_params.pop(param.name, None)
                elif param.location == "path":
                    path_params.pop(param.name, None)

                case = GeneratedTestCase(
                    id=self._generate_case_id(),
                    title=f"{endpoint.method} {endpoint.path} - 缺少必填参数{param.name}",
                    description=f"验证缺少必填参数{param.name}时返回正确的错误信息",
                    test_type=TestCaseType.EQUIVALENCE,
                    priority=TestPriority.P0,
                    endpoint=endpoint.path,
                    method=endpoint.method,
                    headers=headers,
                    path_params=path_params,
                    query_params=query_params,
                    request_body=body,
                    expected_status=400,
                    assertions=[
                        {"type": "status_code", "expected": 400},
                        {"type": "response_contains", "field": "error"},
                    ],
                    tags=endpoint.tags,
                    design_method=f"等价类划分 - 必填参数{param.name}缺失",
                )
                cases.append(case)

        return cases

    def _generate_boundary_cases(self, endpoint: APIEndpoint) -> List[GeneratedTestCase]:
        """生成边界值测试用例"""
        cases = []

        for param in endpoint.parameters:
            if param.location not in ["query", "path"]:
                continue

            boundary_values = TestDataGenerator.get_boundary_values(param.param_type, param.name)

            for boundary_value in boundary_values[:4]:  # 限制数量
                path_params, query_params, headers, body = self._build_valid_request(endpoint)

                if param.location == "query":
                    query_params[param.name] = boundary_value
                elif param.location == "path":
                    path_params[param.name] = boundary_value

                # 判断是否为有效边界值
                is_valid = self._is_valid_boundary(param, boundary_value)
                expected_status = 200 if is_valid else 400

                case = GeneratedTestCase(
                    id=self._generate_case_id(),
                    title=f"{endpoint.method} {endpoint.path} - {param.name}边界值({repr(boundary_value)[:20]})",
                    description=f"验证{param.name}参数边界值{repr(boundary_value)[:50]}的处理",
                    test_type=TestCaseType.BOUNDARY,
                    priority=TestPriority.P1,
                    endpoint=endpoint.path,
                    method=endpoint.method,
                    headers=headers,
                    path_params=path_params,
                    query_params=query_params,
                    request_body=body,
                    expected_status=expected_status,
                    assertions=[
                        {"type": "status_code", "expected": expected_status},
                    ],
                    tags=endpoint.tags,
                    design_method=f"边界值分析 - {param.name}参数边界",
                )
                cases.append(case)

        return cases

    def _generate_error_guess_cases(self, endpoint: APIEndpoint) -> List[GeneratedTestCase]:
        """生成错误猜测测试用例"""
        cases = []

        # 1. 空请求体（POST/PUT/PATCH）
        if endpoint.method in ["POST", "PUT", "PATCH"] and endpoint.request_body:
            path_params, query_params, headers, _ = self._build_valid_request(endpoint)

            case = GeneratedTestCase(
                id=self._generate_case_id(),
                title=f"{endpoint.method} {endpoint.path} - 空请求体",
                description="验证发送空请求体时的错误处理",
                test_type=TestCaseType.ERROR_GUESS,
                priority=TestPriority.P1,
                endpoint=endpoint.path,
                method=endpoint.method,
                headers=headers,
                path_params=path_params,
                query_params=query_params,
                request_body={},
                expected_status=400,
                assertions=[
                    {"type": "status_code", "expected": 400},
                ],
                tags=endpoint.tags,
                design_method="错误猜测 - 空请求体",
            )
            cases.append(case)

        # 2. 无效的Content-Type
        if endpoint.method in ["POST", "PUT", "PATCH"]:
            path_params, query_params, _, body = self._build_valid_request(endpoint)

            case = GeneratedTestCase(
                id=self._generate_case_id(),
                title=f"{endpoint.method} {endpoint.path} - 无效Content-Type",
                description="验证发送无效Content-Type时的错误处理",
                test_type=TestCaseType.ERROR_GUESS,
                priority=TestPriority.P2,
                endpoint=endpoint.path,
                method=endpoint.method,
                headers={"Content-Type": "text/plain"},
                path_params=path_params,
                query_params=query_params,
                request_body=body,
                expected_status=415,
                assertions=[
                    {"type": "status_code", "expected": 415},
                ],
                tags=endpoint.tags,
                design_method="错误猜测 - 无效Content-Type",
            )
            cases.append(case)

        # 3. 超大请求体
        if endpoint.method in ["POST", "PUT", "PATCH"]:
            path_params, query_params, headers, _ = self._build_valid_request(endpoint)
            large_body = {"data": "x" * 1000000}  # 1MB数据

            case = GeneratedTestCase(
                id=self._generate_case_id(),
                title=f"{endpoint.method} {endpoint.path} - 超大请求体",
                description="验证发送超大请求体时的处理（防止DoS）",
                test_type=TestCaseType.ERROR_GUESS,
                priority=TestPriority.P2,
                endpoint=endpoint.path,
                method=endpoint.method,
                headers=headers,
                path_params=path_params,
                query_params=query_params,
                request_body=large_body,
                expected_status=413,
                assertions=[
                    {"type": "status_code_in", "expected": [413, 400]},
                ],
                tags=endpoint.tags,
                design_method="错误猜测 - 请求体过大",
            )
            cases.append(case)

        # 4. 不存在的资源ID
        for param in endpoint.parameters:
            if param.location == "path" and "id" in param.name.lower():
                path_params, query_params, headers, body = self._build_valid_request(endpoint)
                path_params[param.name] = 999999999  # 不存在的ID

                case = GeneratedTestCase(
                    id=self._generate_case_id(),
                    title=f"{endpoint.method} {endpoint.path} - 资源不存在",
                    description=f"验证访问不存在的资源ID时返回404",
                    test_type=TestCaseType.ERROR_GUESS,
                    priority=TestPriority.P1,
                    endpoint=endpoint.path,
                    method=endpoint.method,
                    headers=headers,
                    path_params=path_params,
                    query_params=query_params,
                    request_body=body,
                    expected_status=404,
                    assertions=[
                        {"type": "status_code", "expected": 404},
                    ],
                    tags=endpoint.tags,
                    design_method="错误猜测 - 资源不存在",
                )
                cases.append(case)
                break

        return cases

    def _generate_security_cases(self, endpoint: APIEndpoint) -> List[GeneratedTestCase]:
        """生成安全测试用例"""
        cases = []

        # 1. 未授权访问（如果需要认证）
        if endpoint.security:
            path_params, query_params, _, body = self._build_valid_request(endpoint)

            case = GeneratedTestCase(
                id=self._generate_case_id(),
                title=f"{endpoint.method} {endpoint.path} - 未授权访问",
                description="验证未携带认证信息时返回401",
                test_type=TestCaseType.SECURITY,
                priority=TestPriority.P0,
                endpoint=endpoint.path,
                method=endpoint.method,
                headers={},  # 不带认证头
                path_params=path_params,
                query_params=query_params,
                request_body=body,
                expected_status=401,
                assertions=[
                    {"type": "status_code", "expected": 401},
                ],
                tags=endpoint.tags,
                design_method="安全测试 - 未授权访问",
            )
            cases.append(case)

            # 无效Token
            case = GeneratedTestCase(
                id=self._generate_case_id(),
                title=f"{endpoint.method} {endpoint.path} - 无效Token",
                description="验证携带无效Token时返回401/403",
                test_type=TestCaseType.SECURITY,
                priority=TestPriority.P0,
                endpoint=endpoint.path,
                method=endpoint.method,
                headers={"Authorization": "Bearer invalid_token_xxx"},
                path_params=path_params,
                query_params=query_params,
                request_body=body,
                expected_status=401,
                assertions=[
                    {"type": "status_code_in", "expected": [401, 403]},
                ],
                tags=endpoint.tags,
                design_method="安全测试 - 无效Token",
            )
            cases.append(case)

        # 2. SQL注入测试
        for param in endpoint.parameters:
            if param.param_type == "string" and param.location in ["query", "path"]:
                path_params, query_params, headers, body = self._build_valid_request(endpoint)

                sql_injection = "'; DROP TABLE users;--"
                if param.location == "query":
                    query_params[param.name] = sql_injection
                elif param.location == "path":
                    path_params[param.name] = sql_injection

                case = GeneratedTestCase(
                    id=self._generate_case_id(),
                    title=f"{endpoint.method} {endpoint.path} - SQL注入({param.name})",
                    description=f"验证{param.name}参数对SQL注入攻击的防护",
                    test_type=TestCaseType.SECURITY,
                    priority=TestPriority.P0,
                    endpoint=endpoint.path,
                    method=endpoint.method,
                    headers=headers,
                    path_params=path_params,
                    query_params=query_params,
                    request_body=body,
                    expected_status=400,
                    assertions=[
                        {"type": "status_code_in", "expected": [400, 200]},
                        {"type": "response_not_contains", "value": "error"},
                    ],
                    tags=endpoint.tags,
                    design_method="安全测试 - SQL注入",
                )
                cases.append(case)
                break  # 只测试一个参数

        # 3. XSS测试
        for param in endpoint.parameters:
            if param.param_type == "string" and param.location in ["query", "path"]:
                path_params, query_params, headers, body = self._build_valid_request(endpoint)

                xss_payload = "<script>alert('XSS')</script>"
                if param.location == "query":
                    query_params[param.name] = xss_payload
                elif param.location == "path":
                    path_params[param.name] = xss_payload

                case = GeneratedTestCase(
                    id=self._generate_case_id(),
                    title=f"{endpoint.method} {endpoint.path} - XSS攻击({param.name})",
                    description=f"验证{param.name}参数对XSS攻击的防护",
                    test_type=TestCaseType.SECURITY,
                    priority=TestPriority.P1,
                    endpoint=endpoint.path,
                    method=endpoint.method,
                    headers=headers,
                    path_params=path_params,
                    query_params=query_params,
                    request_body=body,
                    expected_status=400,
                    assertions=[
                        {"type": "response_not_contains", "value": "<script>"},
                    ],
                    tags=endpoint.tags,
                    design_method="安全测试 - XSS攻击",
                )
                cases.append(case)
                break

        return cases

    def _build_valid_request(
        self,
        endpoint: APIEndpoint,
        required_only: bool = False
    ) -> Tuple[Dict, Dict, Dict, Optional[Dict]]:
        """构建有效的请求参数"""
        path_params = {}
        query_params = {}
        headers = {"Content-Type": "application/json"}
        body = None

        for param in endpoint.parameters:
            if required_only and not param.required:
                continue

            value = None
            if param.example:
                value = param.example
            elif param.default:
                value = param.default
            elif param.enum:
                value = param.enum[0]
            else:
                value = TestDataGenerator.get_valid_value(param.param_type, param.name)

            if param.location == "path":
                path_params[param.name] = value
            elif param.location == "query":
                query_params[param.name] = value
            elif param.location == "header":
                headers[param.name] = str(value)

        # 处理请求体
        if endpoint.request_body:
            content = endpoint.request_body.get("content", {})
            for media_type, media_info in content.items():
                if "json" in media_type:
                    schema = media_info.get("schema", {})
                    body = self._generate_body_from_schema(schema, required_only)
                    break

        return path_params, query_params, headers, body

    def _generate_body_from_schema(
        self,
        schema: Dict[str, Any],
        required_only: bool = False
    ) -> Dict[str, Any]:
        """从schema生成请求体"""
        if not schema:
            return {}

        result = {}
        required_fields = schema.get("required", [])
        properties = schema.get("properties", {})

        for prop_name, prop_schema in properties.items():
            if required_only and prop_name not in required_fields:
                continue

            prop_type = prop_schema.get("type", "string")

            if "example" in prop_schema:
                result[prop_name] = prop_schema["example"]
            elif "default" in prop_schema:
                result[prop_name] = prop_schema["default"]
            elif "enum" in prop_schema:
                result[prop_name] = prop_schema["enum"][0]
            else:
                result[prop_name] = TestDataGenerator.get_valid_value(prop_type, prop_name)

        return result

    def _has_optional_params(self, endpoint: APIEndpoint) -> bool:
        """检查是否有可选参数"""
        for param in endpoint.parameters:
            if not param.required:
                return True
        return False

    def _is_valid_boundary(self, param: APIParameter, value: Any) -> bool:
        """判断边界值是否有效"""
        # 简单判断逻辑，可以根据实际情况扩展
        if value is None or value == "":
            return False
        if param.param_type == "integer" and isinstance(value, int):
            if value < 0 and "id" in param.name.lower():
                return False
        return True
