# iOS测试报告生成器

import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from core.llm_client import LLMClient
from prompts.prompt_manager import PromptManager
from prompts.prompt_config import PromptType, get_prompt_config
from executors.ios_executor import IOSTestSuiteResult, IOSTestStatus


class IOSTestReporter:
    """iOS测试报告生成器"""

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
        result: IOSTestSuiteResult,
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
        result: IOSTestSuiteResult,
        include_ai_analysis: bool = False,
    ) -> str:
        """生成Markdown格式报告"""

        # 计算执行时间
        durations = [r.duration_seconds for r in result.results if r.duration_seconds > 0]
        avg_duration = sum(durations) / len(durations) if durations else 0
        max_duration = max(durations) if durations else 0

        report = f"""# iOS自动化测试报告

## 测试概览

| 项目 | 值 |
|------|-----|
| **测试套件** | {result.suite_name} |
| **测试设备** | {result.device_name} |
| **设备UDID** | {result.device_udid} |
| **iOS版本** | {result.ios_version} |
| **应用Bundle ID** | {result.app_bundle_id or "N/A"} |
| **开始时间** | {result.started_at} |
| **结束时间** | {result.finished_at} |

## 测试结果统计

| 指标 | 数量 | 百分比 |
|------|------|--------|
| ✅ 通过 | {result.passed} | {result.passed/result.total*100:.1f}% |
| ❌ 失败 | {result.failed} | {result.failed/result.total*100:.1f}% |
| ⚠️ 错误 | {result.error} | {result.error/result.total*100:.1f}% |
| ⏭️ 跳过 | {result.skipped} | {result.skipped/result.total*100:.1f}% |
| **总计** | **{result.total}** | **{result.pass_rate}% 通过率** |

## 测试用例详情

"""

        # 状态图标
        status_icons = {
            IOSTestStatus.PASSED: "✅",
            IOSTestStatus.FAILED: "❌",
            IOSTestStatus.ERROR: "⚠️",
            IOSTestStatus.SKIPPED: "⏭️",
        }

        report += "| 状态 | 测试类 | 测试方法 | 执行时间 |\n"
        report += "|------|--------|----------|----------|\n"

        for r in result.results:
            icon = status_icons.get(r.status, "❓")
            report += f"| {icon} | {r.test_class} | {r.test_method} | {r.duration_seconds:.2f}s |\n"

        # 失败用例详情
        failed_results = [r for r in result.results if r.status in [IOSTestStatus.FAILED, IOSTestStatus.ERROR]]
        if failed_results:
            report += "\n## 失败用例分析\n\n"

            for r in failed_results:
                report += f"""### ❌ {r.test_class}.{r.test_method}

- **测试用例ID**: {r.test_case_id}
- **测试标题**: {r.test_case_title}
- **执行时间**: {r.duration_seconds:.2f}s
- **失败类型**: {"断言失败" if r.status == IOSTestStatus.FAILED else "执行错误"}

"""
                if r.failure_reason:
                    report += f"""**失败原因**:
```
{r.failure_reason}
```

"""

                if r.error_message:
                    report += f"""**错误信息**:
```
{r.error_message}
```

"""

                if r.screenshot_path:
                    report += f"**截图**: ![screenshot]({r.screenshot_path})\n\n"

                report += "---\n\n"

        # 性能统计
        report += f"""## 性能指标

| 指标 | 值 |
|------|-----|
| **总执行时间** | {result.total_duration_seconds:.2f}s |
| **平均用例时间** | {avg_duration:.2f}s |
| **最长用例时间** | {max_duration:.2f}s |

## 测试产物

- **结果包路径**: `{result.result_bundle_path}`

"""

        # AI分析
        if include_ai_analysis and self.llm_client and failed_results:
            report += "\n## AI智能分析\n\n"
            analysis = self._generate_ai_analysis(result)
            report += analysis

        # 按测试类统计
        class_stats: Dict[str, Dict[str, int]] = {}
        for r in result.results:
            if r.test_class not in class_stats:
                class_stats[r.test_class] = {"total": 0, "passed": 0, "failed": 0}
            class_stats[r.test_class]["total"] += 1
            if r.status == IOSTestStatus.PASSED:
                class_stats[r.test_class]["passed"] += 1
            elif r.status in [IOSTestStatus.FAILED, IOSTestStatus.ERROR]:
                class_stats[r.test_class]["failed"] += 1

        report += "\n## 按测试类统计\n\n"
        report += "| 测试类 | 总数 | 通过 | 失败 | 通过率 |\n"
        report += "|--------|------|------|------|--------|\n"
        for class_name, stats in class_stats.items():
            pass_rate = stats["passed"] / stats["total"] * 100 if stats["total"] > 0 else 0
            report += f"| {class_name} | {stats['total']} | {stats['passed']} | {stats['failed']} | {pass_rate:.1f}% |\n"

        report += f"""
---
*报告生成时间: {datetime.now().isoformat()}*
*Generated by AI Test Platform*
"""

        return report

    def _generate_json_report(self, result: IOSTestSuiteResult) -> str:
        """生成JSON格式报告"""
        return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)

    def _generate_html_report(
        self,
        result: IOSTestSuiteResult,
        include_ai_analysis: bool = False,
    ) -> str:
        """生成HTML格式报告"""

        passed_pct = result.passed / result.total * 100 if result.total > 0 else 0
        failed_pct = (result.failed + result.error) / result.total * 100 if result.total > 0 else 0

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>iOS测试报告 - {result.suite_name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .card {{ background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; color: white; margin-bottom: 30px; }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; text-shadow: 0 2px 4px rgba(0,0,0,0.2); }}
        .header p {{ opacity: 0.9; }}
        .device-info {{ display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; margin-top: 15px; }}
        .device-badge {{ background: rgba(255,255,255,0.2); padding: 8px 16px; border-radius: 20px; font-size: 14px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .stat-item {{ text-align: center; padding: 20px; background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%); border-radius: 12px; }}
        .stat-value {{ font-size: 36px; font-weight: bold; }}
        .stat-label {{ color: #666; font-size: 13px; margin-top: 5px; }}
        .stat-item.passed .stat-value {{ color: #10b981; }}
        .stat-item.failed .stat-value {{ color: #ef4444; }}
        .stat-item.rate .stat-value {{ color: #6366f1; }}
        .progress-ring {{ display: flex; justify-content: center; margin: 20px 0; }}
        .progress-ring svg {{ width: 150px; height: 150px; }}
        .progress-ring circle {{ fill: none; stroke-width: 10; }}
        .progress-ring .bg {{ stroke: #e5e7eb; }}
        .progress-ring .progress {{ stroke: #10b981; stroke-linecap: round; transform: rotate(-90deg); transform-origin: 50% 50%; }}
        .progress-text {{ font-size: 24px; font-weight: bold; fill: #333; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 14px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #f8fafc; font-weight: 600; color: #475569; }}
        tr:hover {{ background: #f8fafc; }}
        .status {{ display: inline-flex; align-items: center; gap: 6px; }}
        .status-dot {{ width: 10px; height: 10px; border-radius: 50%; }}
        .status-passed .status-dot {{ background: #10b981; }}
        .status-failed .status-dot {{ background: #ef4444; }}
        .status-error .status-dot {{ background: #f59e0b; }}
        .failure-card {{ border-left: 4px solid #ef4444; padding-left: 16px; margin: 16px 0; }}
        .failure-card h4 {{ color: #ef4444; margin-bottom: 8px; }}
        .failure-card pre {{ background: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 6px; overflow-x: auto; font-size: 13px; }}
        .footer {{ text-align: center; color: rgba(255,255,255,0.7); padding: 20px; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🍎 iOS测试报告</h1>
            <p>{result.suite_name}</p>
            <div class="device-info">
                <span class="device-badge">📱 {result.device_name}</span>
                <span class="device-badge">iOS {result.ios_version}</span>
                <span class="device-badge">⏱️ {result.total_duration_seconds:.1f}s</span>
            </div>
        </div>

        <div class="card">
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
                <div class="stat-item rate">
                    <div class="stat-value">{result.pass_rate}%</div>
                    <div class="stat-label">通过率</div>
                </div>
            </div>

            <div class="progress-ring">
                <svg viewBox="0 0 100 100">
                    <circle class="bg" cx="50" cy="50" r="40"/>
                    <circle class="progress" cx="50" cy="50" r="40"
                        stroke-dasharray="{passed_pct * 2.51} 251"
                        stroke-dashoffset="0"/>
                    <text x="50" y="55" text-anchor="middle" class="progress-text">{result.pass_rate}%</text>
                </svg>
            </div>
        </div>

        <div class="card">
            <h3 style="margin-bottom: 16px; color: #334155;">📋 测试详情</h3>
            <table>
                <thead>
                    <tr>
                        <th>状态</th>
                        <th>测试类</th>
                        <th>测试方法</th>
                        <th>执行时间</th>
                    </tr>
                </thead>
                <tbody>
"""

        for r in result.results:
            status_class = f"status-{r.status.value}"
            status_text = "通过" if r.status == IOSTestStatus.PASSED else "失败" if r.status == IOSTestStatus.FAILED else "错误"

            html += f"""
                    <tr>
                        <td><span class="status {status_class}"><span class="status-dot"></span>{status_text}</span></td>
                        <td>{r.test_class}</td>
                        <td><code>{r.test_method}</code></td>
                        <td>{r.duration_seconds:.2f}s</td>
                    </tr>
"""

        html += """
                </tbody>
            </table>
        </div>
"""

        # 失败用例详情
        failed_results = [r for r in result.results if r.status in [IOSTestStatus.FAILED, IOSTestStatus.ERROR]]
        if failed_results:
            html += """
        <div class="card">
            <h3 style="margin-bottom: 16px; color: #ef4444;">⚠️ 失败用例详情</h3>
"""
            for r in failed_results:
                html += f"""
            <div class="failure-card">
                <h4>{r.test_class}.{r.test_method}</h4>
                <p style="color: #64748b; margin-bottom: 8px;">执行时间: {r.duration_seconds:.2f}s</p>
"""
                if r.failure_reason or r.error_message:
                    error_text = r.failure_reason or r.error_message
                    html += f"""
                <pre>{error_text}</pre>
"""
                html += """
            </div>
"""
            html += """
        </div>
"""

        html += f"""
        <div class="footer">
            Generated by AI Test Platform | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>
"""

        return html

    def _generate_ai_analysis(self, result: IOSTestSuiteResult) -> str:
        """使用AI生成分析报告"""
        if not self.llm_client:
            return ""

        config = get_prompt_config(PromptType.IOS_TEST_REPORT)

        # 准备测试结果摘要
        summary = {
            "suite_name": result.suite_name,
            "device": f"{result.device_name} (iOS {result.ios_version})",
            "total": result.total,
            "passed": result.passed,
            "failed": result.failed,
            "pass_rate": result.pass_rate,
            "failed_cases": [
                {
                    "class": r.test_class,
                    "method": r.test_method,
                    "duration": r.duration_seconds,
                    "failure_reason": r.failure_reason,
                    "error_message": r.error_message,
                }
                for r in result.results
                if r.status in [IOSTestStatus.FAILED, IOSTestStatus.ERROR]
            ]
        }

        messages = PromptManager.build_messages(
            prompt_type=PromptType.ERROR_ANALYSIS,
            user_input="请分析以下iOS测试失败原因并给出改进建议",
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
        result: IOSTestSuiteResult,
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
            filename = f"ios_report_{timestamp}"

        ext_map = {"markdown": ".md", "json": ".json", "html": ".html"}
        ext = ext_map.get(format, ".md")

        filepath = self.output_dir / f"{filename}{ext}"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return str(filepath)
