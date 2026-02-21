# API测试报告生成器

import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from core.llm_client import LLMClient
from prompts.prompt_manager import PromptManager
from prompts.prompt_config import PromptType, get_prompt_config
from executors.api_executor import APITestSuiteResult, TestStatus


class APITestReporter:
    """API测试报告生成器"""

    def __init__(
        self,
        output_dir: str = "./reports",
        llm_client: Optional[LLMClient] = None,
    ):
        """
        初始化报告生成器

        Args:
            output_dir: 报告输出目录
            llm_client: LLM客户端（用于AI增强报告）
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.llm_client = llm_client

    def generate_report(
        self,
        result: APITestSuiteResult,
        format: str = "markdown",
        include_ai_analysis: bool = False,
    ) -> str:
        """
        生成测试报告

        Args:
            result: 测试套件结果
            format: 报告格式 (markdown, json, html)
            include_ai_analysis: 是否包含AI分析

        Returns:
            报告内容
        """
        if format == "json":
            return self._generate_json_report(result)
        elif format == "html":
            return self._generate_html_report(result, include_ai_analysis)
        else:
            return self._generate_markdown_report(result, include_ai_analysis)

    def _generate_markdown_report(
        self,
        result: APITestSuiteResult,
        include_ai_analysis: bool = False,
    ) -> str:
        """生成Markdown格式报告"""

        # 计算性能指标
        response_times = [r.response_time_ms for r in result.results if r.response_time_ms > 0]
        avg_time = sum(response_times) / len(response_times) if response_times else 0
        max_time = max(response_times) if response_times else 0
        min_time = min(response_times) if response_times else 0

        # 排序获取P95, P99
        sorted_times = sorted(response_times)
        p95_index = int(len(sorted_times) * 0.95)
        p99_index = int(len(sorted_times) * 0.99)
        p95_time = sorted_times[p95_index] if sorted_times else 0
        p99_time = sorted_times[p99_index] if sorted_times else 0

        report = f"""# API测试报告

## 概要信息

| 项目 | 值 |
|------|-----|
| **测试套件** | {result.suite_name} |
| **基础URL** | {result.base_url} |
| **开始时间** | {result.started_at} |
| **结束时间** | {result.finished_at} |
| **总用例数** | {result.total} |
| **通过数** | {result.passed} |
| **失败数** | {result.failed} |
| **错误数** | {result.error} |
| **跳过数** | {result.skipped} |
| **通过率** | {result.pass_rate}% |

## 测试结果概览

"""

        # 状态图标
        status_icons = {
            TestStatus.PASSED: "✅",
            TestStatus.FAILED: "❌",
            TestStatus.ERROR: "⚠️",
            TestStatus.SKIPPED: "⏭️",
        }

        report += "| 状态 | 用例ID | 用例名称 | 方法 | 端点 | 响应时间 |\n"
        report += "|------|--------|----------|------|------|----------|\n"

        for r in result.results:
            icon = status_icons.get(r.status, "❓")
            report += f"| {icon} | {r.test_case_id} | {r.test_case_title} | {r.method} | {r.endpoint} | {r.response_time_ms:.0f}ms |\n"

        # 失败用例详情
        failed_results = [r for r in result.results if r.status in [TestStatus.FAILED, TestStatus.ERROR]]
        if failed_results:
            report += "\n## 失败用例详情\n\n"

            for r in failed_results:
                report += f"""### {r.test_case_id}: {r.test_case_title}

- **API**: `{r.method} {r.endpoint}`
- **状态码**: 预期 vs 实际: {r.response_status}
- **响应时间**: {r.response_time_ms:.0f}ms

"""
                if r.error_message:
                    report += f"**错误信息**:\n```\n{r.error_message}\n```\n\n"

                if r.assertions:
                    report += "**断言结果**:\n"
                    for a in r.assertions:
                        status = "✅" if a.passed else "❌"
                        report += f"- {status} {a.assertion_type}: {a.message}\n"
                    report += "\n"

                report += f"""<details>
<summary>请求详情</summary>

**请求头**:
```json
{json.dumps(r.request_headers, indent=2, ensure_ascii=False)}
```

**请求体**:
```json
{json.dumps(r.request_body, indent=2, ensure_ascii=False) if r.request_body else "无"}
```

**响应体**:
```json
{json.dumps(r.response_body, indent=2, ensure_ascii=False) if r.response_body else "无"}
```
</details>

---

"""

        # 性能指标
        report += f"""## 性能指标

| 指标 | 值 |
|------|-----|
| **平均响应时间** | {avg_time:.0f}ms |
| **最小响应时间** | {min_time:.0f}ms |
| **最大响应时间** | {max_time:.0f}ms |
| **P95响应时间** | {p95_time:.0f}ms |
| **P99响应时间** | {p99_time:.0f}ms |
| **总执行时间** | {result.total_time_ms:.0f}ms |

"""

        # AI分析
        if include_ai_analysis and self.llm_client and failed_results:
            report += "\n## AI分析与建议\n\n"
            analysis = self._generate_ai_analysis(result)
            report += analysis

        report += f"""
---
*报告生成时间: {datetime.now().isoformat()}*
*Generated by AI Test Platform*
"""

        return report

    def _generate_json_report(self, result: APITestSuiteResult) -> str:
        """生成JSON格式报告"""
        return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)

    def _generate_html_report(
        self,
        result: APITestSuiteResult,
        include_ai_analysis: bool = False,
    ) -> str:
        """生成HTML格式报告"""
        # 先生成Markdown，然后可以用其他库转换
        # 这里提供基础HTML结构

        passed_pct = result.passed / result.total * 100 if result.total > 0 else 0
        failed_pct = result.failed / result.total * 100 if result.total > 0 else 0

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API测试报告 - {result.suite_name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .card {{ background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .header h1 {{ color: #333; margin-bottom: 10px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; }}
        .stat-item {{ text-align: center; padding: 15px; background: #f8f9fa; border-radius: 8px; }}
        .stat-value {{ font-size: 32px; font-weight: bold; color: #333; }}
        .stat-label {{ color: #666; font-size: 14px; }}
        .stat-item.passed .stat-value {{ color: #28a745; }}
        .stat-item.failed .stat-value {{ color: #dc3545; }}
        .progress-bar {{ height: 24px; background: #e9ecef; border-radius: 12px; overflow: hidden; margin: 20px 0; }}
        .progress-fill {{ height: 100%; display: flex; }}
        .progress-passed {{ background: #28a745; }}
        .progress-failed {{ background: #dc3545; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #f8f9fa; font-weight: 600; }}
        .status-passed {{ color: #28a745; }}
        .status-failed {{ color: #dc3545; }}
        .status-error {{ color: #ffc107; }}
        .badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }}
        .badge-get {{ background: #61affe; color: white; }}
        .badge-post {{ background: #49cc90; color: white; }}
        .badge-put {{ background: #fca130; color: white; }}
        .badge-delete {{ background: #f93e3e; color: white; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="card header">
            <h1>API测试报告</h1>
            <p>{result.suite_name} | {result.base_url}</p>
            <p style="color: #666; font-size: 14px;">{result.started_at}</p>
        </div>

        <div class="card">
            <h2 style="margin-bottom: 15px;">测试概览</h2>
            <div class="stats">
                <div class="stat-item">
                    <div class="stat-value">{result.total}</div>
                    <div class="stat-label">总用例</div>
                </div>
                <div class="stat-item passed">
                    <div class="stat-value">{result.passed}</div>
                    <div class="stat-label">通过</div>
                </div>
                <div class="stat-item failed">
                    <div class="stat-value">{result.failed}</div>
                    <div class="stat-label">失败</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{result.pass_rate}%</div>
                    <div class="stat-label">通过率</div>
                </div>
            </div>
            <div class="progress-bar">
                <div class="progress-fill">
                    <div class="progress-passed" style="width: {passed_pct}%"></div>
                    <div class="progress-failed" style="width: {failed_pct}%"></div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2 style="margin-bottom: 15px;">测试详情</h2>
            <table>
                <thead>
                    <tr>
                        <th>状态</th>
                        <th>用例</th>
                        <th>方法</th>
                        <th>端点</th>
                        <th>响应时间</th>
                    </tr>
                </thead>
                <tbody>
"""

        for r in result.results:
            status_class = f"status-{r.status.value}"
            status_icon = "✅" if r.status == TestStatus.PASSED else "❌" if r.status == TestStatus.FAILED else "⚠️"
            method_class = f"badge-{r.method.lower()}"

            html += f"""
                    <tr>
                        <td class="{status_class}">{status_icon}</td>
                        <td><strong>{r.test_case_id}</strong><br><small>{r.test_case_title}</small></td>
                        <td><span class="badge {method_class}">{r.method}</span></td>
                        <td><code>{r.endpoint}</code></td>
                        <td>{r.response_time_ms:.0f}ms</td>
                    </tr>
"""

        html += f"""
                </tbody>
            </table>
        </div>

        <div class="card" style="text-align: center; color: #666;">
            <p>Generated by AI Test Platform | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
"""

        return html

    def _generate_ai_analysis(self, result: APITestSuiteResult) -> str:
        """使用AI生成分析报告"""
        if not self.llm_client:
            return ""

        config = get_prompt_config(PromptType.API_TEST_REPORT)

        # 准备测试结果摘要
        summary = {
            "suite_name": result.suite_name,
            "total": result.total,
            "passed": result.passed,
            "failed": result.failed,
            "pass_rate": result.pass_rate,
            "failed_cases": [
                {
                    "id": r.test_case_id,
                    "title": r.test_case_title,
                    "method": r.method,
                    "endpoint": r.endpoint,
                    "error": r.error_message,
                    "assertions": [
                        {"type": a.assertion_type, "message": a.message, "passed": a.passed}
                        for a in r.assertions
                    ]
                }
                for r in result.results
                if r.status in [TestStatus.FAILED, TestStatus.ERROR]
            ]
        }

        messages = PromptManager.build_messages(
            prompt_type=PromptType.ERROR_ANALYSIS,
            user_input="请分析以下API测试失败原因并给出改进建议",
            variables={"error_details": json.dumps(summary, ensure_ascii=False, indent=2)}
        )

        try:
            analysis = self.llm_client.chat(
                messages,
                max_tokens=config.max_tokens,
                temperature=config.temperature
            )
            return analysis
        except Exception as e:
            return f"*AI分析生成失败: {str(e)}*"

    def save_report(
        self,
        result: APITestSuiteResult,
        format: str = "markdown",
        filename: Optional[str] = None,
        include_ai_analysis: bool = False,
    ) -> str:
        """
        保存测试报告到文件

        Args:
            result: 测试套件结果
            format: 报告格式
            filename: 文件名（不含扩展名）
            include_ai_analysis: 是否包含AI分析

        Returns:
            保存的文件路径
        """
        content = self.generate_report(result, format, include_ai_analysis)

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"api_report_{timestamp}"

        ext_map = {"markdown": ".md", "json": ".json", "html": ".html"}
        ext = ext_map.get(format, ".md")

        filepath = self.output_dir / f"{filename}{ext}"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return str(filepath)
