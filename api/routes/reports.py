# 测试报告相关路由

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

from reporters.api_reporter import APITestReporter
from reporters.ios_reporter import IOSTestReporter
from reporters.html_reporter import HTMLReporter
from storage.test_result_store import TestResultStore
from utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)
result_store = TestResultStore()


# ==================== 请求模型 ====================

class GenerateReportRequest(BaseModel):
    """生成报告请求"""
    result_id: str = Field(..., description="测试结果ID")
    format: str = Field("html", description="报告格式: html, markdown, json")
    include_ai_analysis: bool = Field(False, description="是否包含AI分析")


class DashboardRequest(BaseModel):
    """生成仪表板请求"""
    api_result_ids: Optional[List[str]] = Field(None, description="API测试结果ID列表")
    ios_result_ids: Optional[List[str]] = Field(None, description="iOS测试结果ID列表")
    title: str = Field("测试总览", description="仪表板标题")


# ==================== 路由处理 ====================

@router.post("/generate")
async def generate_report(request: GenerateReportRequest):
    """
    生成测试报告

    根据测试结果ID生成指定格式的报告。
    """
    try:
        # 获取测试结果
        result = result_store.get(request.result_id)
        if not result:
            raise HTTPException(status_code=404, detail="测试结果不存在")

        # 判断测试类型
        if "device_name" in result:
            # iOS测试结果
            from executors.ios_executor import IOSTestSuiteResult, IOSTestCaseResult, IOSTestStatus

            case_results = []
            for r in result.get("results", []):
                case_results.append(IOSTestCaseResult(
                    test_case_id=r.get("test_case_id", ""),
                    test_case_title=r.get("test_case_title", ""),
                    test_class=r.get("test_class", ""),
                    test_method=r.get("test_method", ""),
                    status=IOSTestStatus(r.get("status", "pending")),
                    duration_seconds=r.get("duration_seconds", 0),
                    error_message=r.get("error_message", ""),
                    failure_reason=r.get("failure_reason", ""),
                ))

            suite_result = IOSTestSuiteResult(
                suite_name=result.get("suite_name", ""),
                device_name=result.get("device_name", ""),
                device_udid=result.get("device_udid", ""),
                ios_version=result.get("ios_version", ""),
                app_bundle_id=result.get("app_bundle_id", ""),
                total=result.get("total", 0),
                passed=result.get("passed", 0),
                failed=result.get("failed", 0),
                skipped=result.get("skipped", 0),
                error=result.get("error", 0),
                pass_rate=result.get("pass_rate", 0),
                total_duration_seconds=result.get("total_duration_seconds", 0),
                results=case_results,
                result_bundle_path=result.get("result_bundle_path", ""),
                started_at=result.get("started_at", ""),
                finished_at=result.get("finished_at", ""),
            )

            reporter = IOSTestReporter()
            report_path = reporter.save_report(
                suite_result,
                format=request.format,
                include_ai_analysis=request.include_ai_analysis,
            )

        else:
            # API测试结果
            from executors.api_executor import APITestSuiteResult, APITestResult, TestStatus, AssertionResult

            case_results = []
            for r in result.get("results", []):
                assertions = [
                    AssertionResult(
                        assertion_type=a.get("assertion_type", ""),
                        path=a.get("path", ""),
                        expected=a.get("expected"),
                        actual=a.get("actual"),
                        passed=a.get("passed", False),
                        message=a.get("message", ""),
                    )
                    for a in r.get("assertions", [])
                ]

                case_results.append(APITestResult(
                    test_case_id=r.get("test_case_id", ""),
                    test_case_title=r.get("test_case_title", ""),
                    status=TestStatus(r.get("status", "pending")),
                    method=r.get("method", ""),
                    endpoint=r.get("endpoint", ""),
                    request_headers=r.get("request_headers", {}),
                    request_body=r.get("request_body"),
                    response_status=r.get("response_status", 0),
                    response_body=r.get("response_body"),
                    response_time_ms=r.get("response_time_ms", 0),
                    assertions=assertions,
                    error_message=r.get("error_message", ""),
                ))

            suite_result = APITestSuiteResult(
                suite_name=result.get("suite_name", ""),
                base_url=result.get("base_url", ""),
                total=result.get("total", 0),
                passed=result.get("passed", 0),
                failed=result.get("failed", 0),
                skipped=result.get("skipped", 0),
                error=result.get("error", 0),
                pass_rate=result.get("pass_rate", 0),
                total_time_ms=result.get("total_time_ms", 0),
                results=case_results,
                started_at=result.get("started_at", ""),
                finished_at=result.get("finished_at", ""),
            )

            reporter = APITestReporter()
            report_path = reporter.save_report(
                suite_result,
                format=request.format,
                include_ai_analysis=request.include_ai_analysis,
            )

        return {
            "result_id": request.result_id,
            "format": request.format,
            "report_path": report_path,
            "generated_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成报告失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dashboard")
async def generate_dashboard(request: DashboardRequest):
    """
    生成综合仪表板

    汇总多个测试结果生成可视化仪表板。
    """
    try:
        api_results = []
        ios_results = []

        # 获取API测试结果
        if request.api_result_ids:
            for result_id in request.api_result_ids:
                result = result_store.get(result_id)
                if result:
                    api_results.append(result)

        # 获取iOS测试结果
        if request.ios_result_ids:
            for result_id in request.ios_result_ids:
                result = result_store.get(result_id)
                if result:
                    ios_results.append(result)

        # 生成仪表板
        reporter = HTMLReporter()
        dashboard_path = reporter.save_dashboard(
            api_results=api_results,
            ios_results=ios_results,
        )

        return {
            "dashboard_path": dashboard_path,
            "api_results_count": len(api_results),
            "ios_results_count": len(ios_results),
            "generated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"生成仪表板失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/view/{report_name}")
async def view_report(report_name: str):
    """查看报告（HTML）"""
    reports_dir = Path("./reports")
    report_path = reports_dir / report_name

    if not report_path.exists():
        raise HTTPException(status_code=404, detail="报告不存在")

    if report_path.suffix == ".html":
        return FileResponse(report_path, media_type="text/html")
    elif report_path.suffix == ".md":
        content = report_path.read_text(encoding="utf-8")
        return HTMLResponse(content=f"<pre>{content}</pre>")
    else:
        return FileResponse(report_path)


@router.get("/download/{report_name}")
async def download_report(report_name: str):
    """下载报告"""
    reports_dir = Path("./reports")
    report_path = reports_dir / report_name

    if not report_path.exists():
        raise HTTPException(status_code=404, detail="报告不存在")

    return FileResponse(
        report_path,
        filename=report_name,
        media_type="application/octet-stream",
    )


@router.get("/list")
async def list_reports(
    page: int = 1,
    page_size: int = 20,
):
    """获取报告列表"""
    reports_dir = Path("./reports")
    reports_dir.mkdir(exist_ok=True)

    all_reports = []
    for report_path in reports_dir.glob("*"):
        if report_path.is_file():
            stat = report_path.stat()
            all_reports.append({
                "name": report_path.name,
                "size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })

    # 按修改时间排序
    all_reports.sort(key=lambda x: x["modified_at"], reverse=True)

    # 分页
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "total": len(all_reports),
        "page": page,
        "page_size": page_size,
        "reports": all_reports[start:end],
    }


@router.delete("/{report_name}")
async def delete_report(report_name: str):
    """删除报告"""
    reports_dir = Path("./reports")
    report_path = reports_dir / report_name

    if not report_path.exists():
        raise HTTPException(status_code=404, detail="报告不存在")

    report_path.unlink()

    return {"message": "删除成功"}
