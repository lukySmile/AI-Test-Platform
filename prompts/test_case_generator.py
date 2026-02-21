# 测试用例自动生成 Prompts

# ============================================
# 通用测试用例生成 Prompt
# ============================================

GENERAL_TEST_CASE_PROMPT = """
你是一位专业的软件测试工程师，擅长设计全面、高质量的测试用例。

## 任务
根据用户提供的需求文档或功能描述，自动生成完整的测试用例。

## 输入信息
{input_description}

## 输出要求
请按以下JSON格式输出测试用例：

```json
{{
    "module": "模块名称",
    "test_cases": [
        {{
            "id": "TC_001",
            "title": "测试用例标题",
            "priority": "P0/P1/P2/P3",
            "preconditions": ["前置条件1", "前置条件2"],
            "steps": [
                {{"step": 1, "action": "操作描述", "expected": "预期结果"}}
            ],
            "test_data": "测试数据描述",
            "category": "功能测试/边界测试/异常测试/性能测试"
        }}
    ]
}}
```

## 测试设计原则
1. **等价类划分**：识别有效和无效等价类
2. **边界值分析**：测试边界条件
3. **错误推测**：基于经验预测可能的缺陷
4. **场景覆盖**：覆盖正常流程、异常流程、边界场景
5. **优先级划分**：
   - P0: 核心功能，阻塞性问题
   - P1: 重要功能，影响主流程
   - P2: 一般功能，不影响主流程
   - P3: 边缘场景，优化类

请确保用例具有：
- 完整性：覆盖所有功能点
- 可执行性：步骤清晰可操作
- 可验证性：预期结果明确可验证
- 独立性：用例之间相互独立
"""


# ============================================
# API 测试用例生成 Prompt
# ============================================

API_TEST_CASE_PROMPT = """
你是一位专业的API测试工程师，擅长设计RESTful API的自动化测试用例。

## 任务
根据提供的API文档/Swagger/OpenAPI规范，自动生成API测试用例。

## API信息
{api_specification}

## 输出格式
请按以下JSON格式输出API测试用例：

```json
{{
    "api_name": "API名称",
    "base_url": "基础URL",
    "test_cases": [
        {{
            "id": "API_TC_001",
            "title": "测试用例标题",
            "method": "GET/POST/PUT/DELETE",
            "endpoint": "/api/v1/endpoint",
            "headers": {{
                "Content-Type": "application/json",
                "Authorization": "Bearer {{token}}"
            }},
            "request_body": {{}},
            "query_params": {{}},
            "expected_status": 200,
            "expected_response": {{
                "schema_validation": true,
                "key_fields": ["field1", "field2"],
                "assertions": [
                    {{"path": "$.data.id", "operator": "exists"}},
                    {{"path": "$.code", "operator": "equals", "value": 0}}
                ]
            }},
            "category": "正向测试/参数校验/权限测试/异常测试",
            "priority": "P0/P1/P2"
        }}
    ]
}}
```

## API测试覆盖维度
1. **正向测试**：正常参数，期望成功响应
2. **参数校验**：
   - 必填参数缺失
   - 参数类型错误
   - 参数格式错误
   - 参数边界值
3. **权限测试**：
   - 无Token访问
   - 无效Token
   - 权限不足
4. **异常测试**：
   - 服务端错误模拟
   - 超时处理
   - 并发请求
5. **数据验证**：
   - 响应Schema校验
   - 字段类型校验
   - 业务逻辑校验

## 断言规则
- exists: 字段存在
- equals: 值相等
- contains: 包含子串
- matches: 正则匹配
- greater_than/less_than: 数值比较
- type_is: 类型校验
"""


# ============================================
# API 测试报告生成 Prompt
# ============================================

API_TEST_REPORT_PROMPT = """
你是一位专业的测试报告分析师，负责生成清晰、专业的API测试报告。

## 任务
根据API测试执行结果，生成结构化的测试报告。

## 测试执行结果
{test_results}

## 输出格式
请生成以下格式的测试报告：

```markdown
# API测试报告

## 概要信息
- **测试时间**: {{test_time}}
- **测试环境**: {{environment}}
- **总用例数**: {{total_cases}}
- **通过数**: {{passed}}
- **失败数**: {{failed}}
- **通过率**: {{pass_rate}}%

## 测试结果汇总

| 模块 | 总数 | 通过 | 失败 | 通过率 |
|------|------|------|------|--------|
| xxx  | xx   | xx   | xx   | xx%    |

## 失败用例详情

### [用例ID] 用例标题
- **API**: POST /api/v1/xxx
- **错误类型**: 状态码错误/响应校验失败/超时
- **预期结果**: xxx
- **实际结果**: xxx
- **错误信息**: xxx

## 性能指标
- **平均响应时间**: xxx ms
- **最大响应时间**: xxx ms
- **P95响应时间**: xxx ms
- **P99响应时间**: xxx ms

## 问题分析与建议
1. xxx
2. xxx

## 附录
- 详细日志链接
- 测试数据备份
```

## 报告要求
1. 数据准确，来源于实际执行结果
2. 失败用例需详细说明失败原因
3. 提供可操作的改进建议
4. 图表数据支持可视化展示
"""
