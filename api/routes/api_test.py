# API测试相关路由

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio

from executors.api_executor import APITestExecutor, APITestSuiteResult
from reporters.api_reporter import APITestReporter
from storage.test_case_store import TestCaseStore
from storage.test_result_store import TestResultStore
from utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)
case_store = TestCaseStore()
result_store = TestResultStore()


# ==================== 请求模型 ====================

class ExecuteAPITestRequest(BaseModel):
    """执行API测试请求"""
    test_case_id: Optional[str] = Field(None, description="测试用例ID")
    test_cases: Optional[List[Dict[str, Any]]] = Field(None, description="直接提供的测试用例")
    base_url: str = Field(..., description="API基础URL")
    headers: Optional[Dict[str, str]] = Field(None, description="默认请求头")
    variables: Optional[Dict[str, str]] = Field(None, description="变量（如token）")
    parallel: bool = Field(False, description="是否并行执行")
    timeout: int = Field(30, description="请求超时时间（秒）")

    class Config:
        json_schema_extra = {
            "example": {
                "test_case_id": "tc_001",
                "base_url": "https://api.example.com",
                "headers": {"Authorization": "Bearer xxx"},
                "parallel": False
            }
        }


class TestExecutionStatus(BaseModel):
    """测试执行状态"""
    execution_id: str
    status: str  # pending, running, completed, failed
    progress: int
    total: int
    started_at: str
    finished_at: Optional[str]


# ==================== 状态存储 ====================

# 简单的内存存储，实际生产环境应使用Redis
execution_status: Dict[str, Dict[str, Any]] = {}


# ==================== 路由处理 ====================

@router.post("/execute")
async def execute_api_test(
    request: ExecuteAPITestRequest,
    background_tasks: BackgroundTasks,
):
    """
    执行API测试

    可以通过test_case_id引用已保存的测试用例，或直接提供test_cases。

    返回执行ID，可用于查询执行状态。
    """
    try:
        # 获取测试用例
        if request.test_case_id:
            stored = case_store.get(request.test_case_id)
            if not stored:
                raise HTTPException(status_code=404, detail="测试用例不存在")
            test_cases = stored.get("test_cases", [])
            suite_name = stored.get("api_name", stored.get("module", "API测试"))
        elif request.test_cases:
            test_cases = request.test_cases
            suite_name = "临时测试"
        else:
            raise HTTPException(status_code=400, detail="请提供test_case_id或test_cases")

        # 生成执行ID
        execution_id = f"exec_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 初始化状态
        execution_status[execution_id] = {
            "status": "pending",
            "progress": 0,
            "total": len(test_cases),
            "started_at": datetime.now().isoformat(),
            "finished_at": None,
            "result": None,
        }

        # 后台执行测试
        background_tasks.add_task(
            run_api_test_task,
            execution_id=execution_id,
            test_cases=test_cases,
            suite_name=suite_name,
            base_url=request.base_url,
            headers=request.headers,
            variables=request.variables,
            parallel=request.parallel,
            timeout=request.timeout,
        )

        return {
            "execution_id": execution_id,
            "status": "pending",
            "total_cases": len(test_cases),
            "message": "测试已开始执行，请通过执行ID查询状态",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动API测试失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def run_api_test_task(
    execution_id: str,
    test_cases: List[Dict[str, Any]],
    suite_name: str,
    base_url: str,
    headers: Optional[Dict[str, str]],
    variables: Optional[Dict[str, str]],
    parallel: bool,
    timeout: int,
):
    """后台执行API测试任务"""
    try:
        execution_status[execution_id]["status"] = "running"

        with APITestExecutor(
            base_url=base_url,
            default_headers=headers,
            timeout=timeout,
        ) as executor:
            # 设置变量
            if variables:
                for name, value in variables.items():
                    executor.set_variable(name, value)

            # 执行测试
            result = executor.execute_suite(
                test_cases=test_cases,
                suite_name=suite_name,
                parallel=parallel,
            )

        # 保存结果
        result_id = result_store.save(result.to_dict())

        # 生成报告
        reporter = APITestReporter()
        report_path = reporter.save_report(result, format="html")

        # 更新状态
        execution_status[execution_id].update({
            "status": "completed",
            "progress": len(test_cases),
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

        logger.info(f"测试执行完成: {execution_id}, 通过率: {result.pass_rate}%")

    except Exception as e:
        logger.error(f"测试执行失败: {execution_id}, 错误: {str(e)}")
        execution_status[execution_id].update({
            "status": "failed",
            "finished_at": datetime.now().isoformat(),
            "error": str(e),
        })


@router.get("/status/{execution_id}")
async def get_execution_status(execution_id: str):
    """获取测试执行状态"""
    if execution_id not in execution_status:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    return execution_status[execution_id]


@router.post("/execute/sync")
async def execute_api_test_sync(request: ExecuteAPITestRequest):
    """
    同步执行API测试

    等待测试完成后返回结果。适用于测试用例较少的场景。
    """
    try:
        # 获取测试用例
        if request.test_case_id:
            stored = case_store.get(request.test_case_id)
            if not stored:
                raise HTTPException(status_code=404, detail="测试用例不存在")
            test_cases = stored.get("test_cases", [])
            suite_name = stored.get("api_name", stored.get("module", "API测试"))
        elif request.test_cases:
            test_cases = request.test_cases
            suite_name = "临时测试"
        else:
            raise HTTPException(status_code=400, detail="请提供test_case_id或test_cases")

        with APITestExecutor(
            base_url=request.base_url,
            default_headers=request.headers,
            timeout=request.timeout,
        ) as executor:
            if request.variables:
                for name, value in request.variables.items():
                    executor.set_variable(name, value)

            result = executor.execute_suite(
                test_cases=test_cases,
                suite_name=suite_name,
                parallel=request.parallel,
            )

        # 保存结果
        result_id = result_store.save(result.to_dict())

        # 生成报告
        reporter = APITestReporter()
        report_path = reporter.save_report(result, format="html")

        return {
            "result_id": result_id,
            "suite_name": suite_name,
            "total": result.total,
            "passed": result.passed,
            "failed": result.failed,
            "pass_rate": result.pass_rate,
            "total_time_ms": result.total_time_ms,
            "report_path": report_path,
            "results": [r.to_dict() for r in result.results],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"执行API测试失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results/{result_id}")
async def get_test_result(result_id: str):
    """获取测试结果详情"""
    result = result_store.get(result_id)
    if not result:
        raise HTTPException(status_code=404, detail="测试结果不存在")
    return result


@router.get("/results")
async def list_test_results(
    page: int = 1,
    page_size: int = 20,
):
    """获取测试结果列表"""
    return result_store.list(page=page, page_size=page_size)
