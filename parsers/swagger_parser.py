# Swagger/OpenAPI 文档解析器

import json
import yaml
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class APIParameter:
    """API参数"""
    name: str
    location: str  # query, path, header, body
    required: bool
    param_type: str
    description: str = ""
    default: Any = None
    enum: List[Any] = field(default_factory=list)
    example: Any = None


@dataclass
class APIEndpoint:
    """API端点"""
    path: str
    method: str
    summary: str
    description: str
    operation_id: str
    tags: List[str]
    parameters: List[APIParameter]
    request_body: Optional[Dict[str, Any]]
    responses: Dict[str, Any]
    security: List[Dict[str, List[str]]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "method": self.method,
            "summary": self.summary,
            "description": self.description,
            "operation_id": self.operation_id,
            "tags": self.tags,
            "parameters": [
                {
                    "name": p.name,
                    "in": p.location,
                    "required": p.required,
                    "type": p.param_type,
                    "description": p.description,
                    "default": p.default,
                    "enum": p.enum,
                    "example": p.example,
                }
                for p in self.parameters
            ],
            "request_body": self.request_body,
            "responses": self.responses,
            "security": self.security,
        }


@dataclass
class APISpec:
    """API规范"""
    title: str
    version: str
    description: str
    base_url: str
    endpoints: List[APIEndpoint]
    security_definitions: Dict[str, Any]
    schemas: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "version": self.version,
            "description": self.description,
            "base_url": self.base_url,
            "endpoints": [e.to_dict() for e in self.endpoints],
            "security_definitions": self.security_definitions,
            "schemas": self.schemas,
        }

    def to_prompt_format(self) -> str:
        """转换为Prompt可用的格式"""
        lines = [
            f"# API文档: {self.title}",
            f"版本: {self.version}",
            f"基础URL: {self.base_url}",
            f"描述: {self.description}",
            "",
            "## 接口列表",
            "",
        ]

        for endpoint in self.endpoints:
            lines.append(f"### {endpoint.method.upper()} {endpoint.path}")
            lines.append(f"**{endpoint.summary}**")
            if endpoint.description:
                lines.append(f"{endpoint.description}")
            lines.append("")

            if endpoint.parameters:
                lines.append("**参数:**")
                for param in endpoint.parameters:
                    required = "必填" if param.required else "可选"
                    lines.append(f"- {param.name} ({param.location}, {param.param_type}, {required}): {param.description}")
                lines.append("")

            if endpoint.request_body:
                lines.append("**请求体:**")
                lines.append(f"```json")
                lines.append(json.dumps(endpoint.request_body, indent=2, ensure_ascii=False))
                lines.append("```")
                lines.append("")

            if endpoint.responses:
                lines.append("**响应:**")
                for status, response in endpoint.responses.items():
                    desc = response.get("description", "")
                    lines.append(f"- {status}: {desc}")
                lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)


class SwaggerParser:
    """Swagger 2.0 解析器"""

    def __init__(self):
        self.spec: Optional[Dict[str, Any]] = None

    def parse(self, source: str) -> APISpec:
        """
        解析Swagger文档

        Args:
            source: 文件路径或JSON/YAML字符串

        Returns:
            APISpec对象
        """
        # 加载文档
        self.spec = self._load_spec(source)

        # 解析基本信息
        info = self.spec.get("info", {})
        title = info.get("title", "Untitled API")
        version = info.get("version", "1.0.0")
        description = info.get("description", "")

        # 解析基础URL
        host = self.spec.get("host", "localhost")
        base_path = self.spec.get("basePath", "/")
        schemes = self.spec.get("schemes", ["https"])
        base_url = f"{schemes[0]}://{host}{base_path}"

        # 解析端点
        endpoints = self._parse_endpoints()

        # 解析安全定义
        security_definitions = self.spec.get("securityDefinitions", {})

        # 解析数据模型
        schemas = self.spec.get("definitions", {})

        return APISpec(
            title=title,
            version=version,
            description=description,
            base_url=base_url,
            endpoints=endpoints,
            security_definitions=security_definitions,
            schemas=schemas,
        )

    def _load_spec(self, source: str) -> Dict[str, Any]:
        """加载规范文档"""
        # 首先尝试作为JSON/YAML字符串解析
        try:
            return json.loads(source)
        except json.JSONDecodeError:
            pass

        try:
            result = yaml.safe_load(source)
            if isinstance(result, dict):
                return result
        except yaml.YAMLError:
            pass

        # 如果是短字符串，尝试作为文件路径
        if len(source) < 500:
            path = Path(source)
            try:
                if path.exists():
                    content = path.read_text(encoding="utf-8")
                    if path.suffix in [".yaml", ".yml"]:
                        return yaml.safe_load(content)
                    else:
                        return json.loads(content)
            except OSError:
                pass

        raise ValueError("无法解析输入，请提供有效的JSON/YAML格式或文件路径")

    def _parse_endpoints(self) -> List[APIEndpoint]:
        """解析所有端点"""
        endpoints = []
        paths = self.spec.get("paths", {})

        for path, methods in paths.items():
            for method, operation in methods.items():
                if method.lower() in ["get", "post", "put", "delete", "patch", "options", "head"]:
                    endpoint = self._parse_operation(path, method, operation)
                    endpoints.append(endpoint)

        return endpoints

    def _parse_operation(self, path: str, method: str, operation: Dict[str, Any]) -> APIEndpoint:
        """解析单个操作"""
        # 解析参数
        parameters = []
        for param in operation.get("parameters", []):
            # 处理引用
            if "$ref" in param:
                param = self._resolve_ref(param["$ref"])

            parameters.append(APIParameter(
                name=param.get("name", ""),
                location=param.get("in", "query"),
                required=param.get("required", False),
                param_type=self._get_param_type(param),
                description=param.get("description", ""),
                default=param.get("default"),
                enum=param.get("enum", []),
                example=param.get("example"),
            ))

        # 解析请求体（Swagger 2.0中在parameters里）
        request_body = None
        for param in operation.get("parameters", []):
            if param.get("in") == "body":
                request_body = self._parse_schema(param.get("schema", {}))
                break

        return APIEndpoint(
            path=path,
            method=method.upper(),
            summary=operation.get("summary", ""),
            description=operation.get("description", ""),
            operation_id=operation.get("operationId", ""),
            tags=operation.get("tags", []),
            parameters=parameters,
            request_body=request_body,
            responses=operation.get("responses", {}),
            security=operation.get("security", []),
        )

    def _get_param_type(self, param: Dict[str, Any]) -> str:
        """获取参数类型"""
        if "type" in param:
            return param["type"]
        if "schema" in param:
            schema = param["schema"]
            if "$ref" in schema:
                ref = schema["$ref"]
                return ref.split("/")[-1]
            return schema.get("type", "object")
        return "string"

    def _parse_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """解析schema"""
        if "$ref" in schema:
            return self._resolve_ref(schema["$ref"])
        return schema

    def _resolve_ref(self, ref: str) -> Dict[str, Any]:
        """解析引用"""
        parts = ref.lstrip("#/").split("/")
        result = self.spec
        for part in parts:
            result = result.get(part, {})
        return result

    def generate_test_spec(self) -> str:
        """生成用于测试的规范描述"""
        if not self.spec:
            raise ValueError("请先调用parse()方法解析文档")

        api_spec = self.parse_from_loaded()
        return api_spec.to_prompt_format()

    def parse_from_loaded(self) -> APISpec:
        """从已加载的spec解析"""
        info = self.spec.get("info", {})
        host = self.spec.get("host", "localhost")
        base_path = self.spec.get("basePath", "/")
        schemes = self.spec.get("schemes", ["https"])

        return APISpec(
            title=info.get("title", ""),
            version=info.get("version", ""),
            description=info.get("description", ""),
            base_url=f"{schemes[0]}://{host}{base_path}",
            endpoints=self._parse_endpoints(),
            security_definitions=self.spec.get("securityDefinitions", {}),
            schemas=self.spec.get("definitions", {}),
        )
