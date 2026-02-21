# 通用HTML报告生成器

from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import json


class HTMLReporter:
    """通用HTML报告生成器"""

    def __init__(self, output_dir: str = "./reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_dashboard(
        self,
        api_results: Optional[List[Dict[str, Any]]] = None,
        ios_results: Optional[List[Dict[str, Any]]] = None,
        title: str = "测试总览仪表板",
    ) -> str:
        """
        生成综合仪表板

        Args:
            api_results: API测试结果列表
            ios_results: iOS测试结果列表
            title: 仪表板标题

        Returns:
            HTML内容
        """
        api_results = api_results or []
        ios_results = ios_results or []

        # 计算统计数据
        api_total = sum(r.get("total", 0) for r in api_results)
        api_passed = sum(r.get("passed", 0) for r in api_results)
        ios_total = sum(r.get("total", 0) for r in ios_results)
        ios_passed = sum(r.get("passed", 0) for r in ios_results)

        total_cases = api_total + ios_total
        total_passed = api_passed + ios_passed
        overall_pass_rate = (total_passed / total_cases * 100) if total_cases > 0 else 0

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            min-height: 100vh;
        }}
        .navbar {{
            background: #1e293b;
            padding: 16px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #334155;
        }}
        .navbar h1 {{ font-size: 1.5em; }}
        .navbar .time {{ color: #94a3b8; font-size: 14px; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 24px; }}
        .grid {{ display: grid; gap: 24px; }}
        .grid-4 {{ grid-template-columns: repeat(4, 1fr); }}
        .grid-2 {{ grid-template-columns: repeat(2, 1fr); }}
        .card {{
            background: #1e293b;
            border-radius: 12px;
            padding: 24px;
            border: 1px solid #334155;
        }}
        .stat-card {{
            text-align: center;
        }}
        .stat-card .value {{
            font-size: 48px;
            font-weight: bold;
            background: linear-gradient(135deg, #3b82f6, #8b5cf6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .stat-card .label {{
            color: #94a3b8;
            font-size: 14px;
            margin-top: 8px;
        }}
        .stat-card.success .value {{ background: linear-gradient(135deg, #10b981, #34d399); -webkit-background-clip: text; }}
        .stat-card.danger .value {{ background: linear-gradient(135deg, #ef4444, #f87171); -webkit-background-clip: text; }}
        .stat-card.warning .value {{ background: linear-gradient(135deg, #f59e0b, #fbbf24); -webkit-background-clip: text; }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}
        .card-header h3 {{
            font-size: 18px;
            font-weight: 600;
        }}
        .badge {{
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }}
        .badge-api {{ background: #3b82f6; }}
        .badge-ios {{ background: #8b5cf6; }}
        .chart-container {{
            position: relative;
            height: 300px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #334155;
        }}
        th {{
            color: #94a3b8;
            font-weight: 500;
            font-size: 13px;
            text-transform: uppercase;
        }}
        .progress-bar {{
            height: 8px;
            background: #334155;
            border-radius: 4px;
            overflow: hidden;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #10b981, #34d399);
            border-radius: 4px;
        }}
        .status-indicator {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
        }}
        .status-passed {{ background: #10b981; }}
        .status-failed {{ background: #ef4444; }}
        @media (max-width: 1024px) {{
            .grid-4 {{ grid-template-columns: repeat(2, 1fr); }}
            .grid-2 {{ grid-template-columns: 1fr; }}
        }}
        @media (max-width: 640px) {{
            .grid-4 {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <nav class="navbar">
        <h1>🧪 AI测试平台</h1>
        <span class="time">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
    </nav>

    <div class="container">
        <div class="grid grid-4" style="margin-bottom: 24px;">
            <div class="card stat-card">
                <div class="value">{total_cases}</div>
                <div class="label">总用例数</div>
            </div>
            <div class="card stat-card success">
                <div class="value">{total_passed}</div>
                <div class="label">通过数</div>
            </div>
            <div class="card stat-card danger">
                <div class="value">{total_cases - total_passed}</div>
                <div class="label">失败数</div>
            </div>
            <div class="card stat-card">
                <div class="value">{overall_pass_rate:.1f}%</div>
                <div class="label">通过率</div>
            </div>
        </div>

        <div class="grid grid-2">
            <div class="card">
                <div class="card-header">
                    <h3>测试类型分布</h3>
                </div>
                <div class="chart-container">
                    <canvas id="typeChart"></canvas>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <h3>通过率趋势</h3>
                </div>
                <div class="chart-container">
                    <canvas id="trendChart"></canvas>
                </div>
            </div>
        </div>

        <div class="grid grid-2" style="margin-top: 24px;">
            <div class="card">
                <div class="card-header">
                    <h3>API测试结果</h3>
                    <span class="badge badge-api">API</span>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>套件</th>
                            <th>用例数</th>
                            <th>通过率</th>
                            <th>状态</th>
                        </tr>
                    </thead>
                    <tbody>
"""

        for r in api_results:
            pass_rate = r.get("pass_rate", 0)
            status_class = "status-passed" if pass_rate >= 80 else "status-failed"
            html += f"""
                        <tr>
                            <td>{r.get("suite_name", "N/A")}</td>
                            <td>{r.get("total", 0)}</td>
                            <td>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: {pass_rate}%"></div>
                                </div>
                                <span style="font-size: 12px; color: #94a3b8;">{pass_rate}%</span>
                            </td>
                            <td><span class="status-indicator {status_class}"></span></td>
                        </tr>
"""

        if not api_results:
            html += """
                        <tr>
                            <td colspan="4" style="text-align: center; color: #64748b;">暂无数据</td>
                        </tr>
"""

        html += """
                    </tbody>
                </table>
            </div>

            <div class="card">
                <div class="card-header">
                    <h3>iOS测试结果</h3>
                    <span class="badge badge-ios">iOS</span>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>套件</th>
                            <th>设备</th>
                            <th>通过率</th>
                            <th>状态</th>
                        </tr>
                    </thead>
                    <tbody>
"""

        for r in ios_results:
            pass_rate = r.get("pass_rate", 0)
            status_class = "status-passed" if pass_rate >= 80 else "status-failed"
            html += f"""
                        <tr>
                            <td>{r.get("suite_name", "N/A")}</td>
                            <td>{r.get("device_name", "N/A")}</td>
                            <td>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: {pass_rate}%"></div>
                                </div>
                                <span style="font-size: 12px; color: #94a3b8;">{pass_rate}%</span>
                            </td>
                            <td><span class="status-indicator {status_class}"></span></td>
                        </tr>
"""

        if not ios_results:
            html += """
                        <tr>
                            <td colspan="4" style="text-align: center; color: #64748b;">暂无数据</td>
                        </tr>
"""

        html += f"""
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        // 测试类型分布图
        new Chart(document.getElementById('typeChart'), {{
            type: 'doughnut',
            data: {{
                labels: ['API测试', 'iOS测试'],
                datasets: [{{
                    data: [{api_total}, {ios_total}],
                    backgroundColor: ['#3b82f6', '#8b5cf6'],
                    borderWidth: 0
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels: {{ color: '#94a3b8' }}
                    }}
                }}
            }}
        }});

        // 通过率趋势图（示例数据）
        new Chart(document.getElementById('trendChart'), {{
            type: 'line',
            data: {{
                labels: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
                datasets: [{{
                    label: 'API',
                    data: [85, 88, 82, 90, 87, 92, {api_passed/api_total*100 if api_total > 0 else 0:.0f}],
                    borderColor: '#3b82f6',
                    tension: 0.4,
                    fill: false
                }}, {{
                    label: 'iOS',
                    data: [78, 82, 85, 80, 88, 85, {ios_passed/ios_total*100 if ios_total > 0 else 0:.0f}],
                    borderColor: '#8b5cf6',
                    tension: 0.4,
                    fill: false
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 100,
                        grid: {{ color: '#334155' }},
                        ticks: {{ color: '#94a3b8' }}
                    }},
                    x: {{
                        grid: {{ color: '#334155' }},
                        ticks: {{ color: '#94a3b8' }}
                    }}
                }},
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels: {{ color: '#94a3b8' }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""

        return html

    def save_dashboard(
        self,
        api_results: Optional[List[Dict[str, Any]]] = None,
        ios_results: Optional[List[Dict[str, Any]]] = None,
        filename: str = "dashboard",
    ) -> str:
        """保存仪表板到文件"""
        html = self.generate_dashboard(api_results, ios_results)
        filepath = self.output_dir / f"{filename}.html"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        return str(filepath)
