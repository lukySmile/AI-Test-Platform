# AI测试平台 - 主入口

"""
AI测试平台 - 自动化测试解决方案

功能:
1. 测试用例自动生成 - 根据需求文档/API规范自动生成测试用例
2. API测试自动化 - 一键执行API测试，自动生成报告
3. iOS模拟器测试 - iOS UI自动化测试，自动生成测试代码和报告

使用示例:
    python main.py generate --type api --input api_spec.json
    python main.py execute --type api --cases test_cases.json
    python main.py report --input results.json --format html
"""

import argparse
import json
import sys
from pathlib import Path

from core.llm_client import LLMClient, LLMConfig, LLMProvider
from core.test_case_service import TestCaseService
from executors.api_executor import APITestExecutor
from executors.ios_executor import IOSTestExecutor
from reporters.api_reporter import APITestReporter
from reporters.ios_reporter import IOSTestReporter
from reporters.html_reporter import HTMLReporter


def create_llm_client() -> LLMClient:
    """创建LLM客户端"""
    return LLMClient()


def cmd_generate(args):
    """生成测试用例"""
    print(f"📝 正在生成 {args.type} 测试用例...")

    with open(args.input, "r", encoding="utf-8") as f:
        input_content = f.read()

    llm_client = create_llm_client()
    service = TestCaseService(llm_client)

    try:
        if args.type == "api":
            result = service.generate_api_test_cases(input_content)
        elif args.type == "ios":
            result = service.generate_ios_test_cases(input_content)
        else:
            result = service.generate_test_cases(input_content)

        # 保存结果
        output_path = args.output or f"test_cases_{args.type}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"✅ 测试用例已生成: {output_path}")
        print(f"   用例数量: {len(result.get('test_cases', []))}")

    finally:
        service.close()


def cmd_execute(args):
    """执行测试"""
    print(f"🚀 正在执行 {args.type} 测试...")

    with open(args.cases, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    if args.type == "api":
        base_url = args.base_url or test_cases.get("base_url", "http://localhost:8080")

        with APITestExecutor(base_url) as executor:
            # 设置认证token（如果提供）
            if args.token:
                executor.set_variable("token", args.token)

            result = executor.execute_suite(
                test_cases.get("test_cases", []),
                suite_name=test_cases.get("api_name", "API测试"),
                parallel=args.parallel,
            )

        # 生成报告
        reporter = APITestReporter(output_dir=args.output_dir)
        report_path = reporter.save_report(
            result,
            format=args.report_format,
            include_ai_analysis=args.ai_analysis,
        )

        print(f"✅ 测试完成!")
        print(f"   总用例: {result.total}")
        print(f"   通过: {result.passed}")
        print(f"   失败: {result.failed}")
        print(f"   通过率: {result.pass_rate}%")
        print(f"   报告: {report_path}")

    elif args.type == "ios":
        executor = IOSTestExecutor(
            project_path=args.project,
            scheme=args.scheme,
            output_dir=args.output_dir,
        )

        result = executor.execute_tests(
            device_name=args.device or "iPhone 15 Pro",
            ios_version=args.ios_version or "17.0",
        )

        reporter = IOSTestReporter(output_dir=args.output_dir)
        report_path = reporter.save_report(
            result,
            format=args.report_format,
            include_ai_analysis=args.ai_analysis,
        )

        print(f"✅ iOS测试完成!")
        print(f"   总用例: {result.total}")
        print(f"   通过: {result.passed}")
        print(f"   失败: {result.failed}")
        print(f"   通过率: {result.pass_rate}%")
        print(f"   报告: {report_path}")


def cmd_report(args):
    """生成报告"""
    print(f"📊 正在生成报告...")

    with open(args.input, "r", encoding="utf-8") as f:
        results = json.load(f)

    reporter = HTMLReporter(output_dir=args.output_dir)
    report_path = reporter.save_dashboard(
        api_results=results.get("api_results", []),
        ios_results=results.get("ios_results", []),
    )

    print(f"✅ 报告已生成: {report_path}")


def cmd_analyze(args):
    """分析需求文档"""
    print(f"🔍 正在分析需求文档...")

    with open(args.input, "r", encoding="utf-8") as f:
        requirement = f.read()

    llm_client = create_llm_client()
    service = TestCaseService(llm_client)

    try:
        result = service.analyze_requirement(requirement)

        output_path = args.output or "analysis_result.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"✅ 分析完成: {output_path}")
        print(f"   测试点数量: {len(result.get('test_points', []))}")
        print(f"   风险点数量: {len(result.get('risk_points', []))}")

    finally:
        service.close()


def main():
    parser = argparse.ArgumentParser(
        description="AI测试平台 - 自动化测试解决方案",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # generate 命令
    gen_parser = subparsers.add_parser("generate", help="生成测试用例")
    gen_parser.add_argument("--type", choices=["api", "ios", "general"], default="general", help="测试类型")
    gen_parser.add_argument("--input", "-i", required=True, help="输入文件路径")
    gen_parser.add_argument("--output", "-o", help="输出文件路径")
    gen_parser.set_defaults(func=cmd_generate)

    # execute 命令
    exec_parser = subparsers.add_parser("execute", help="执行测试")
    exec_parser.add_argument("--type", choices=["api", "ios"], required=True, help="测试类型")
    exec_parser.add_argument("--cases", "-c", required=True, help="测试用例文件")
    exec_parser.add_argument("--base-url", help="API基础URL")
    exec_parser.add_argument("--token", help="认证Token")
    exec_parser.add_argument("--parallel", action="store_true", help="并行执行")
    exec_parser.add_argument("--project", help="Xcode项目路径 (iOS)")
    exec_parser.add_argument("--scheme", help="测试Scheme (iOS)")
    exec_parser.add_argument("--device", help="模拟器设备名称 (iOS)")
    exec_parser.add_argument("--ios-version", help="iOS版本 (iOS)")
    exec_parser.add_argument("--output-dir", default="./reports", help="输出目录")
    exec_parser.add_argument("--report-format", choices=["markdown", "html", "json"], default="html", help="报告格式")
    exec_parser.add_argument("--ai-analysis", action="store_true", help="启用AI分析")
    exec_parser.set_defaults(func=cmd_execute)

    # report 命令
    report_parser = subparsers.add_parser("report", help="生成综合报告")
    report_parser.add_argument("--input", "-i", required=True, help="测试结果文件")
    report_parser.add_argument("--output-dir", default="./reports", help="输出目录")
    report_parser.set_defaults(func=cmd_report)

    # analyze 命令
    analyze_parser = subparsers.add_parser("analyze", help="分析需求文档")
    analyze_parser.add_argument("--input", "-i", required=True, help="需求文档路径")
    analyze_parser.add_argument("--output", "-o", help="输出文件路径")
    analyze_parser.set_defaults(func=cmd_analyze)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
