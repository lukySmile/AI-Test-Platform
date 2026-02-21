# iOS测试相关路由

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from core.llm_client import LLMClient
from core.test_case_service import TestCaseService
from executors.ios_executor import IOSTestExecutor
from reporters.ios_reporter import IOSTestReporter
from storage.test_case_store import TestCaseStore
from storage.test_result_store import TestResultStore
from utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)
case_store = TestCaseStore()
result_store = TestResultStore()


# ==================== 请求模型 ====================

class GenerateIOSTestRequest(BaseModel):
    """生成iOS测试用例请求"""
    app_description: str = Field(..., description="应用功能描述")
    bundle_id: Optional[str] = Field(None, description="应用Bundle ID")
    app_name: Optional[str] = Field(None, description="应用名称")

    class Config:
        json_schema_extra = {
            "example": {
                "app_description": "电商购物App商品详情页：图片轮播、价格显示、加入购物车、立即购买",
                "bundle_id": "com.example.shopping",
                "app_name": "购物App"
            }
        }


class GenerateIOSCodeRequest(BaseModel):
    """生成iOS测试代码请求"""
    test_case_id: Optional[str] = Field(None, description="测试用例ID")
    test_cases: Optional[List[Dict[str, Any]]] = Field(None, description="测试用例列表")
    class_name: str = Field("GeneratedUITests", description="测试类名")


class ExecuteIOSTestRequest(BaseModel):
    """执行iOS测试请求"""
    project_path: str = Field(..., description="Xcode项目路径")
    scheme: str = Field(..., description="测试Scheme名称")
    device_name: str = Field("iPhone 15 Pro", description="模拟器设备名称")
    ios_version: str = Field("17.0", description="iOS版本")
    test_targets: Optional[List[str]] = Field(None, description="测试目标")
    only_testing: Optional[List[str]] = Field(None, description="只运行指定测试")
    timeout: int = Field(600, description="超时时间（秒）")


class SimulatorCommand(BaseModel):
    """模拟器命令请求"""
    requirement: str = Field(..., description="需求描述")


# ==================== 状态存储 ====================

ios_execution_status: Dict[str, Dict[str, Any]] = {}


# ==================== 路由处理 ====================

@router.post("/generate/cases")
async def generate_ios_test_cases(request: GenerateIOSTestRequest):
    """
    生成iOS测试用例

    根据应用功能描述，自动生成iOS UI测试用例。
    """
    try:
        logger.info(f"生成iOS测试用例 - 应用: {request.app_name}")

        llm_client = LLMClient()
        service = TestCaseService(llm_client)

        result = service.generate_ios_test_cases(
            app_description=request.app_description,
            bundle_id=request.bundle_id,
        )

        if request.app_name:
            result["app_name"] = request.app_name

        case_id = case_store.save(result)
        service.close()

        return {
            "id": case_id,
            "app_name": result.get("app_name", ""),
            "bundle_id": result.get("bundle_id", ""),
            "test_suites": result.get("test_suites", []),
            "generated_at": result.get("generated_at", datetime.now().isoformat()),
        }

    except Exception as e:
        logger.error(f"生成iOS测试用例失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/code")
async def generate_ios_test_code(request: GenerateIOSCodeRequest):
    """
    生成iOS测试代码

    根据测试用例生成可执行的XCUITest Swift代码。
    """
    try:
        # 获取测试用例
        if request.test_case_id:
            stored = case_store.get(request.test_case_id)
            if not stored:
                raise HTTPException(status_code=404, detail="测试用例不存在")
            test_suites = stored.get("test_suites", [])
            test_cases = []
            for suite in test_suites:
                test_cases.extend(suite.get("test_cases", []))
        elif request.test_cases:
            test_cases = request.test_cases
        else:
            raise HTTPException(status_code=400, detail="请提供test_case_id或test_cases")

        # 使用执行器生成代码
        executor = IOSTestExecutor(
            project_path="",  # 不需要实际项目路径
            scheme="",
        )

        # 生成代码
        code_lines = [
            "import XCTest",
            "",
            f"class {request.class_name}: XCTestCase {{",
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
            method_lines = executor._generate_test_method(tc)
            code_lines.extend(method_lines)
            code_lines.append("")

        code_lines.append("}")

        code = "\n".join(code_lines)

        return {
            "class_name": request.class_name,
            "code": code,
            "test_count": len(test_cases),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成iOS测试代码失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute")
async def execute_ios_test(
    request: ExecuteIOSTestRequest,
    background_tasks: BackgroundTasks,
):
    """
    执行iOS测试

    在iOS模拟器上执行XCUITest测试。
    """
    try:
        execution_id = f"ios_exec_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        ios_execution_status[execution_id] = {
            "status": "pending",
            "device": request.device_name,
            "ios_version": request.ios_version,
            "started_at": datetime.now().isoformat(),
            "finished_at": None,
            "result": None,
        }

        background_tasks.add_task(
            run_ios_test_task,
            execution_id=execution_id,
            project_path=request.project_path,
            scheme=request.scheme,
            device_name=request.device_name,
            ios_version=request.ios_version,
            test_targets=request.test_targets,
            only_testing=request.only_testing,
            timeout=request.timeout,
        )

        return {
            "execution_id": execution_id,
            "status": "pending",
            "device": request.device_name,
            "ios_version": request.ios_version,
            "message": "iOS测试已开始执行",
        }

    except Exception as e:
        logger.error(f"启动iOS测试失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def run_ios_test_task(
    execution_id: str,
    project_path: str,
    scheme: str,
    device_name: str,
    ios_version: str,
    test_targets: Optional[List[str]],
    only_testing: Optional[List[str]],
    timeout: int,
):
    """后台执行iOS测试任务"""
    try:
        ios_execution_status[execution_id]["status"] = "running"

        executor = IOSTestExecutor(
            project_path=project_path,
            scheme=scheme,
        )

        result = executor.execute_tests(
            device_name=device_name,
            ios_version=ios_version,
            test_targets=test_targets,
            only_testing=only_testing,
            timeout=timeout,
        )

        # 保存结果
        result_id = result_store.save(result.to_dict())

        # 生成报告
        reporter = IOSTestReporter()
        report_path = reporter.save_report(result, format="html")

        ios_execution_status[execution_id].update({
            "status": "completed",
            "finished_at": datetime.now().isoformat(),
            "result": {
                "result_id": result_id,
                "total": result.total,
                "passed": result.passed,
                "failed": result.failed,
                "pass_rate": result.pass_rate,
                "report_path": report_path,
            },
        })

        logger.info(f"iOS测试执行完成: {execution_id}, 通过率: {result.pass_rate}%")

    except Exception as e:
        logger.error(f"iOS测试执行失败: {execution_id}, 错误: {str(e)}")
        ios_execution_status[execution_id].update({
            "status": "failed",
            "finished_at": datetime.now().isoformat(),
            "error": str(e),
        })


@router.get("/status/{execution_id}")
async def get_ios_execution_status(execution_id: str):
    """获取iOS测试执行状态"""
    if execution_id not in ios_execution_status:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    return ios_execution_status[execution_id]


@router.get("/simulators")
async def list_simulators():
    """列出可用的iOS模拟器"""
    try:
        executor = IOSTestExecutor(project_path="", scheme="")
        devices = executor.list_simulators()

        return {
            "devices": [
                {
                    "udid": d.udid,
                    "name": d.name,
                    "runtime": d.runtime,
                    "state": d.state,
                }
                for d in devices
            ]
        }
    except Exception as e:
        logger.error(f"获取模拟器列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simulator/command")
async def generate_simulator_command(request: SimulatorCommand):
    """
    生成模拟器控制命令

    根据需求描述生成xcrun simctl命令。
    """
    try:
        llm_client = LLMClient()

        from prompts.prompt_manager import PromptManager
        from prompts.prompt_config import PromptType

        messages = PromptManager.build_messages(
            prompt_type=PromptType.IOS_SIMULATOR_COMMAND,
            user_input=request.requirement,
            variables={"user_requirement": request.requirement}
        )

        result = llm_client.chat(messages)
        llm_client.close()

        return {
            "requirement": request.requirement,
            "command": result,
        }

    except Exception as e:
        logger.error(f"生成模拟器命令失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
