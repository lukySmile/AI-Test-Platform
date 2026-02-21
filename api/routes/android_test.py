# Android测试相关路由

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from core.llm_client import LLMClient
from core.test_case_service import TestCaseService
from executors.android_executor import AndroidTestExecutor
from reporters.android_reporter import AndroidTestReporter
from storage.test_case_store import TestCaseStore
from storage.test_result_store import TestResultStore
from utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)
case_store = TestCaseStore()
result_store = TestResultStore()


# ==================== 请求模型 ====================

class GenerateAndroidTestRequest(BaseModel):
    """生成Android测试用例请求"""
    app_description: str = Field(..., description="应用功能描述")
    package_name: Optional[str] = Field(None, description="应用包名")
    app_name: Optional[str] = Field(None, description="应用名称")

    class Config:
        json_schema_extra = {
            "example": {
                "app_description": "电商购物App商品详情页：图片轮播、价格显示、加入购物车、立即购买",
                "package_name": "com.example.shopping",
                "app_name": "购物App"
            }
        }


class GenerateAndroidCodeRequest(BaseModel):
    """生成Android测试代码请求"""
    test_case_id: Optional[str] = Field(None, description="测试用例ID")
    test_cases: Optional[List[Dict[str, Any]]] = Field(None, description="测试用例列表")
    class_name: str = Field("GeneratedUITests", description="测试类名")
    package_name: str = Field("com.example.app.test", description="测试包名")


class ExecuteAndroidTestRequest(BaseModel):
    """执行Android测试请求"""
    project_path: str = Field(..., description="Android项目路径")
    device_id: str = Field(..., description="设备ID")
    test_package: str = Field(..., description="测试包名")
    app_package: str = Field(..., description="应用包名")
    test_class: Optional[str] = Field(None, description="测试类")
    test_method: Optional[str] = Field(None, description="测试方法")
    timeout: int = Field(600, description="超时时间（秒）")
    use_gradle: bool = Field(True, description="是否使用Gradle执行")


class EmulatorCommand(BaseModel):
    """模拟器命令请求"""
    requirement: str = Field(..., description="需求描述")


# ==================== 状态存储 ====================

android_execution_status: Dict[str, Dict[str, Any]] = {}


# ==================== 路由处理 ====================

@router.post("/generate/cases")
async def generate_android_test_cases(request: GenerateAndroidTestRequest):
    """
    生成Android测试用例

    根据应用功能描述，自动生成Android UI测试用例。
    """
    try:
        logger.info(f"生成Android测试用例 - 应用: {request.app_name}")

        llm_client = LLMClient()
        service = TestCaseService(llm_client)

        result = service.generate_android_test_cases(
            app_description=request.app_description,
            package_name=request.package_name,
        )

        if request.app_name:
            result["app_name"] = request.app_name

        case_id = case_store.save(result)
        service.close()

        return {
            "id": case_id,
            "app_name": result.get("app_name", ""),
            "package_name": result.get("package_name", ""),
            "test_suites": result.get("test_suites", []),
            "generated_at": result.get("generated_at", datetime.now().isoformat()),
        }

    except Exception as e:
        logger.error(f"生成Android测试用例失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/code")
async def generate_android_test_code(request: GenerateAndroidCodeRequest):
    """
    生成Android测试代码

    根据测试用例生成可执行的Espresso/UI Automator Kotlin代码。
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
        executor = AndroidTestExecutor(
            project_path="",  # 不需要实际项目路径
        )

        # 生成代码
        code_lines = [
            f"package {request.package_name}",
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
            f"class {request.class_name} {{",
            "",
            "    @get:Rule",
            "    val activityRule = ActivityScenarioRule(MainActivity::class.java)",
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
            "package_name": request.package_name,
            "code": code,
            "test_count": len(test_cases),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成Android测试代码失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute")
async def execute_android_test(
    request: ExecuteAndroidTestRequest,
    background_tasks: BackgroundTasks,
):
    """
    执行Android测试

    在Android模拟器/设备上执行Espresso/UI Automator测试。
    """
    try:
        execution_id = f"android_exec_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        android_execution_status[execution_id] = {
            "status": "pending",
            "device": request.device_id,
            "started_at": datetime.now().isoformat(),
            "finished_at": None,
            "result": None,
        }

        background_tasks.add_task(
            run_android_test_task,
            execution_id=execution_id,
            project_path=request.project_path,
            device_id=request.device_id,
            test_package=request.test_package,
            app_package=request.app_package,
            test_class=request.test_class,
            test_method=request.test_method,
            timeout=request.timeout,
            use_gradle=request.use_gradle,
        )

        return {
            "execution_id": execution_id,
            "status": "pending",
            "device": request.device_id,
            "message": "Android测试已开始执行",
        }

    except Exception as e:
        logger.error(f"启动Android测试失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def run_android_test_task(
    execution_id: str,
    project_path: str,
    device_id: str,
    test_package: str,
    app_package: str,
    test_class: Optional[str],
    test_method: Optional[str],
    timeout: int,
    use_gradle: bool,
):
    """后台执行Android测试任务"""
    try:
        android_execution_status[execution_id]["status"] = "running"

        executor = AndroidTestExecutor(
            project_path=project_path,
        )

        result = executor.execute_tests(
            device_id=device_id,
            test_package=test_package,
            app_package=app_package,
            test_class=test_class,
            test_method=test_method,
            timeout=timeout,
            use_gradle=use_gradle,
        )

        # 保存结果
        result_id = result_store.save(result.to_dict())

        # 生成报告
        reporter = AndroidTestReporter()
        report_path = reporter.save_report(result, format="html")

        android_execution_status[execution_id].update({
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

        logger.info(f"Android测试执行完成: {execution_id}, 通过率: {result.pass_rate}%")

    except Exception as e:
        logger.error(f"Android测试执行失败: {execution_id}, 错误: {str(e)}")
        android_execution_status[execution_id].update({
            "status": "failed",
            "finished_at": datetime.now().isoformat(),
            "error": str(e),
        })


@router.get("/status/{execution_id}")
async def get_android_execution_status(execution_id: str):
    """获取Android测试执行状态"""
    if execution_id not in android_execution_status:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    return android_execution_status[execution_id]


@router.get("/devices")
async def list_devices():
    """列出可用的Android设备/模拟器"""
    try:
        executor = AndroidTestExecutor(project_path="")
        devices = executor.list_devices()

        return {
            "devices": [
                {
                    "device_id": d.device_id,
                    "model": d.model,
                    "android_version": d.android_version,
                    "state": d.state,
                    "is_emulator": d.is_emulator,
                }
                for d in devices
            ]
        }
    except Exception as e:
        logger.error(f"获取设备列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/emulators")
async def list_emulators():
    """列出可用的AVD"""
    try:
        executor = AndroidTestExecutor(project_path="")
        avds = executor.list_emulators()

        return {
            "avds": avds
        }
    except Exception as e:
        logger.error(f"获取AVD列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/emulator/command")
async def generate_emulator_command(request: EmulatorCommand):
    """
    生成模拟器控制命令

    根据需求描述生成adb命令。
    """
    try:
        llm_client = LLMClient()

        from prompts.prompt_manager import PromptManager
        from prompts.prompt_config import PromptType

        messages = PromptManager.build_messages(
            prompt_type=PromptType.ANDROID_EMULATOR_COMMAND,
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
