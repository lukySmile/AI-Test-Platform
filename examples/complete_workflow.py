# AI测试平台 - 完整工作流示例

"""
本示例展示AI测试平台的完整工作流程：
1. 从需求文档生成测试用例
2. 执行API测试
3. 执行iOS测试
4. 生成综合报告
"""

import sys
import json
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.llm_client import LLMClient
from core.test_case_service import TestCaseService
from executors.api_executor import APITestExecutor
from executors.ios_executor import IOSTestExecutor
from reporters.api_reporter import APITestReporter
from reporters.ios_reporter import IOSTestReporter
from reporters.html_reporter import HTMLReporter


def demo_api_test_workflow():
    """
    演示API测试完整流程
    """
    print("=" * 60)
    print("🚀 API测试完整流程演示")
    print("=" * 60)

    # 1. 定义API规范
    api_spec = """
    API名称: 用户管理接口

    ## 1. 用户登录
    - 接口: POST /api/v1/auth/login
    - 请求体:
        - username: string, 必填, 用户名
        - password: string, 必填, 密码
    - 响应:
        - code: 0表示成功
        - data.token: 登录令牌
        - data.user_id: 用户ID

    ## 2. 获取用户信息
    - 接口: GET /api/v1/users/{user_id}
    - 请求头: Authorization: Bearer {token}
    - 响应:
        - code: 0表示成功
        - data: 用户信息对象

    ## 3. 更新用户信息
    - 接口: PUT /api/v1/users/{user_id}
    - 请求头: Authorization: Bearer {token}
    - 请求体:
        - nickname: string, 可选
        - avatar: string, 可选
    - 响应:
        - code: 0表示成功
    """

    print("\n📝 步骤1: 生成API测试用例")
    print("-" * 40)

    # 模拟生成的测试用例（实际使用时调用LLM生成）
    test_cases = {
        "api_name": "用户管理接口",
        "base_url": "https://api.example.com",
        "test_cases": [
            {
                "id": "API_TC_001",
                "title": "用户登录-正常流程",
                "method": "POST",
                "endpoint": "/api/v1/auth/login",
                "headers": {"Content-Type": "application/json"},
                "request_body": {
                    "username": "testuser",
                    "password": "Test@123456"
                },
                "expected_status": 200,
                "expected_response": {
                    "assertions": [
                        {"path": "$.code", "operator": "equals", "value": 0},
                        {"path": "$.data.token", "operator": "exists"},
                        {"path": "$.data.user_id", "operator": "exists"}
                    ]
                },
                "extract": {
                    "token": "$.data.token",
                    "user_id": "$.data.user_id"
                },
                "category": "正向测试",
                "priority": "P0"
            },
            {
                "id": "API_TC_002",
                "title": "用户登录-密码错误",
                "method": "POST",
                "endpoint": "/api/v1/auth/login",
                "headers": {"Content-Type": "application/json"},
                "request_body": {
                    "username": "testuser",
                    "password": "wrongpassword"
                },
                "expected_status": 401,
                "expected_response": {
                    "assertions": [
                        {"path": "$.code", "operator": "not_equals", "value": 0}
                    ]
                },
                "category": "异常测试",
                "priority": "P1"
            },
            {
                "id": "API_TC_003",
                "title": "获取用户信息",
                "method": "GET",
                "endpoint": "/api/v1/users/{user_id}",
                "headers": {
                    "Authorization": "Bearer {token}"
                },
                "expected_status": 200,
                "expected_response": {
                    "assertions": [
                        {"path": "$.code", "operator": "equals", "value": 0},
                        {"path": "$.data", "operator": "exists"}
                    ]
                },
                "category": "正向测试",
                "priority": "P0"
            }
        ]
    }

    print(f"✅ 已生成 {len(test_cases['test_cases'])} 个测试用例")
    for tc in test_cases["test_cases"]:
        print(f"   - [{tc['id']}] {tc['title']}")

    print("\n🔧 步骤2: 执行API测试")
    print("-" * 40)

    # 注意: 这里使用模拟的响应，实际使用时需要真实的API服务
    print("⚠️  演示模式 - 使用模拟数据")

    # 模拟执行结果
    from executors.api_executor import APITestResult, APITestSuiteResult, TestStatus, AssertionResult
    from datetime import datetime

    mock_results = [
        APITestResult(
            test_case_id="API_TC_001",
            test_case_title="用户登录-正常流程",
            status=TestStatus.PASSED,
            method="POST",
            endpoint="/api/v1/auth/login",
            request_headers={"Content-Type": "application/json"},
            request_body={"username": "testuser", "password": "Test@123456"},
            response_status=200,
            response_body={"code": 0, "data": {"token": "xxx", "user_id": 123}},
            response_time_ms=156.5,
            assertions=[
                AssertionResult("equals", "$.code", 0, 0, True, "状态码匹配"),
                AssertionResult("exists", "$.data.token", None, "xxx", True, "token存在"),
            ]
        ),
        APITestResult(
            test_case_id="API_TC_002",
            test_case_title="用户登录-密码错误",
            status=TestStatus.PASSED,
            method="POST",
            endpoint="/api/v1/auth/login",
            request_headers={"Content-Type": "application/json"},
            request_body={"username": "testuser", "password": "wrongpassword"},
            response_status=401,
            response_body={"code": 10001, "message": "密码错误"},
            response_time_ms=89.2,
            assertions=[
                AssertionResult("not_equals", "$.code", 0, 10001, True, "状态码不等于0"),
            ]
        ),
        APITestResult(
            test_case_id="API_TC_003",
            test_case_title="获取用户信息",
            status=TestStatus.FAILED,
            method="GET",
            endpoint="/api/v1/users/123",
            request_headers={"Authorization": "Bearer xxx"},
            request_body=None,
            response_status=403,
            response_body={"code": 10002, "message": "无权限"},
            response_time_ms=45.8,
            assertions=[
                AssertionResult("equals", "$.code", 0, 10002, False, "状态码不匹配"),
            ]
        ),
    ]

    suite_result = APITestSuiteResult(
        suite_name="用户管理接口",
        base_url="https://api.example.com",
        total=3,
        passed=2,
        failed=1,
        skipped=0,
        error=0,
        pass_rate=66.67,
        total_time_ms=291.5,
        results=mock_results,
        started_at=datetime.now().isoformat(),
        finished_at=datetime.now().isoformat(),
    )

    print(f"✅ 测试执行完成")
    print(f"   总用例: {suite_result.total}")
    print(f"   通过: {suite_result.passed} ✅")
    print(f"   失败: {suite_result.failed} ❌")
    print(f"   通过率: {suite_result.pass_rate}%")

    print("\n📊 步骤3: 生成测试报告")
    print("-" * 40)

    reporter = APITestReporter(output_dir="./demo_reports")

    # 生成Markdown报告
    md_path = reporter.save_report(suite_result, format="markdown")
    print(f"✅ Markdown报告: {md_path}")

    # 生成HTML报告
    html_path = reporter.save_report(suite_result, format="html")
    print(f"✅ HTML报告: {html_path}")

    # 生成JSON报告
    json_path = reporter.save_report(suite_result, format="json")
    print(f"✅ JSON报告: {json_path}")

    return suite_result.to_dict()


def demo_ios_test_workflow():
    """
    演示iOS测试完整流程
    """
    print("\n" + "=" * 60)
    print("🍎 iOS测试完整流程演示")
    print("=" * 60)

    # 1. 定义应用功能
    app_description = """
    应用: 电商购物App
    页面: 商品详情页

    功能点:
    1. 商品图片轮播展示
    2. 商品标题、价格、库存显示
    3. 规格选择（颜色、尺码）
    4. 购买数量调整（加减按钮）
    5. 加入购物车
    6. 立即购买
    7. 收藏商品
    """

    print("\n📝 步骤1: 生成iOS测试用例")
    print("-" * 40)

    # 模拟生成的测试用例
    ios_test_cases = {
        "app_name": "电商购物App",
        "bundle_id": "com.example.shopping",
        "test_suites": [
            {
                "suite_name": "商品详情页测试",
                "test_cases": [
                    {
                        "id": "IOS_TC_001",
                        "title": "商品图片轮播",
                        "steps": [
                            {"action": "waitForExistence", "element": {"type": "image", "identifier": "product_image"}, "timeout": 10},
                            {"action": "swipeLeft", "element": {"type": "scrollView", "identifier": "image_carousel"}},
                            {"action": "swipeLeft", "element": {"type": "scrollView", "identifier": "image_carousel"}},
                        ],
                        "assertions": [
                            {"type": "exists", "element": "product_image"}
                        ]
                    },
                    {
                        "id": "IOS_TC_002",
                        "title": "加入购物车",
                        "steps": [
                            {"action": "tap", "element": {"type": "button", "identifier": "add_to_cart_button"}},
                            {"action": "waitForExistence", "element": {"type": "alert", "identifier": "cart_success_alert"}, "timeout": 5},
                        ],
                        "assertions": [
                            {"type": "exists", "element": "cart_success_alert"}
                        ]
                    }
                ]
            }
        ]
    }

    print(f"✅ 已生成测试套件")
    for suite in ios_test_cases["test_suites"]:
        print(f"   套件: {suite['suite_name']}")
        for tc in suite["test_cases"]:
            print(f"     - [{tc['id']}] {tc['title']}")

    print("\n🔧 步骤2: 生成测试代码")
    print("-" * 40)

    # 生成Swift测试代码
    test_code = """
import XCTest

class ProductDetailTests: XCTestCase {

    var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication()
        app.launch()
    }

    override func tearDownWithError() throws {
        app.terminate()
    }

    /// 商品图片轮播测试
    func testIOS_TC_001_ImageCarousel() throws {
        let productImage = app.images["product_image"]
        XCTAssertTrue(productImage.waitForExistence(timeout: 10))

        let carousel = app.scrollViews["image_carousel"]
        carousel.swipeLeft()
        carousel.swipeLeft()

        XCTAssertTrue(productImage.exists)
    }

    /// 加入购物车测试
    func testIOS_TC_002_AddToCart() throws {
        let addButton = app.buttons["add_to_cart_button"]
        addButton.tap()

        let alert = app.alerts["cart_success_alert"]
        XCTAssertTrue(alert.waitForExistence(timeout: 5))
    }
}
"""

    print("✅ 已生成Swift测试代码")
    print("-" * 40)
    print(test_code[:500] + "...")

    print("\n🚀 步骤3: 模拟执行测试")
    print("-" * 40)

    # 模拟执行结果
    from executors.ios_executor import IOSTestCaseResult, IOSTestSuiteResult, IOSTestStatus
    from datetime import datetime

    mock_ios_results = [
        IOSTestCaseResult(
            test_case_id="IOS_TC_001",
            test_case_title="商品图片轮播",
            test_class="ProductDetailTests",
            test_method="testIOS_TC_001_ImageCarousel",
            status=IOSTestStatus.PASSED,
            duration_seconds=3.45,
        ),
        IOSTestCaseResult(
            test_case_id="IOS_TC_002",
            test_case_title="加入购物车",
            test_class="ProductDetailTests",
            test_method="testIOS_TC_002_AddToCart",
            status=IOSTestStatus.FAILED,
            duration_seconds=5.12,
            failure_reason="XCTAssertTrue failed - 购物车弹窗未出现",
        ),
    ]

    ios_suite_result = IOSTestSuiteResult(
        suite_name="商品详情页测试",
        device_name="iPhone 15 Pro",
        device_udid="ABCD-1234-EFGH-5678",
        ios_version="17.0",
        app_bundle_id="com.example.shopping",
        total=2,
        passed=1,
        failed=1,
        skipped=0,
        error=0,
        pass_rate=50.0,
        total_duration_seconds=8.57,
        results=mock_ios_results,
        result_bundle_path="./test_output/TestResults.xcresult",
        started_at=datetime.now().isoformat(),
        finished_at=datetime.now().isoformat(),
    )

    print(f"✅ iOS测试执行完成")
    print(f"   设备: {ios_suite_result.device_name} (iOS {ios_suite_result.ios_version})")
    print(f"   总用例: {ios_suite_result.total}")
    print(f"   通过: {ios_suite_result.passed} ✅")
    print(f"   失败: {ios_suite_result.failed} ❌")
    print(f"   通过率: {ios_suite_result.pass_rate}%")

    print("\n📊 步骤4: 生成测试报告")
    print("-" * 40)

    reporter = IOSTestReporter(output_dir="./demo_reports")

    # 生成报告
    md_path = reporter.save_report(ios_suite_result, format="markdown")
    print(f"✅ Markdown报告: {md_path}")

    html_path = reporter.save_report(ios_suite_result, format="html")
    print(f"✅ HTML报告: {html_path}")

    return ios_suite_result.to_dict()


def demo_dashboard():
    """
    生成综合仪表板
    """
    print("\n" + "=" * 60)
    print("📊 生成综合测试仪表板")
    print("=" * 60)

    # 运行两个测试流程
    api_result = demo_api_test_workflow()
    ios_result = demo_ios_test_workflow()

    # 生成综合仪表板
    reporter = HTMLReporter(output_dir="./demo_reports")
    dashboard_path = reporter.save_dashboard(
        api_results=[api_result],
        ios_results=[ios_result],
    )

    print("\n" + "=" * 60)
    print(f"✅ 综合仪表板已生成: {dashboard_path}")
    print("=" * 60)


if __name__ == "__main__":
    # 创建输出目录
    Path("./demo_reports").mkdir(exist_ok=True)

    # 运行演示
    demo_dashboard()

    print("\n🎉 演示完成!")
    print("请查看 ./demo_reports 目录下的报告文件")
