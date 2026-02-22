# OpenAPI 3.x 解析器

import json
import yaml
from typing import Dict, List, Any, Optional
from pathlib import Path

from .swagger_parser import APISpec, APIEndpoint, APIParameter


class OpenAPIParser:
    """OpenAPI 3.x 解析器"""

    def __init__(self):
        self.spec: Optional[Dict[str, Any]] = None

    def parse(self, source: str) -> APISpec:
        """
        解析OpenAPI 3.x文档

        Args:
            source: 文件路径或JSON/YAML字符串

        Returns:
            APISpec对象
        """
        self.spec = self._load_spec(source)

        # 验证版本
        openapi_version = self.spec.get("openapi", "")
        if not openapi_version.startswith("3."):
            raise ValueError(f"不支持的OpenAPI版本: {openapi_version}")

        # 解析基本信息
        info = self.spec.get("info", {})
        title = info.get("title", "Untitled API")
        version = info.get("version", "1.0.0")
        description = info.get("description", "")

        # 解析服务器URL
        servers = self.spec.get("servers", [])
        base_url = servers[0].get("url", "http://localhost") if servers else "http://localhost"

        # 解析端点
        endpoints = self._parse_endpoints()

        # 解析安全方案
        security_definitions = self.spec.get("components", {}).get("securitySchemes", {})

        # 解析数据模型
        schemas = self.spec.get("components", {}).get("schemas", {})

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

        for path, path_item in paths.items():
            # 处理路径级别的参数
            path_params = path_item.get("parameters", [])

            for method in ["get", "post", "put", "delete", "patch", "options", "head"]:
                if method in path_item:
                    operation = path_item[method]
                    endpoint = self._parse_operation(path, method, operation, path_params)
                    endpoints.append(endpoint)

        return endpoints

    def _parse_operation(
        self,
        path: str,
        method: str,
        operation: Dict[str, Any],
        path_params: List[Dict[str, Any]],
    ) -> APIEndpoint:
        """解析单个操作"""
        # 合并路径参数和操作参数
        all_params = path_params + operation.get("parameters", [])

        parameters = []
        for param in all_params:
            # 处理引用
            if "$ref" in param:
                param = self._resolve_ref(param["$ref"])

            parameters.append(APIParameter(
                name=param.get("name", ""),
                location=param.get("in", "query"),
                required=param.get("required", False),
                param_type=self._get_schema_type(param.get("schema", {})),
                description=param.get("description", ""),
                default=param.get("schema", {}).get("default"),
                enum=param.get("schema", {}).get("enum", []),
                example=param.get("example") or param.get("schema", {}).get("example"),
            ))

        # 解析请求体
        request_body = None
        if "requestBody" in operation:
            request_body = self._parse_request_body(operation["requestBody"])

        # 解析响应
        responses = {}
        for status, response in operation.get("responses", {}).items():
            if "$ref" in response:
                response = self._resolve_ref(response["$ref"])
            responses[status] = {
                "description": response.get("description", ""),
                "content": response.get("content", {}),
            }

        return APIEndpoint(
            path=path,
            method=method.upper(),
            summary=operation.get("summary", ""),
            description=operation.get("description", ""),
            operation_id=operation.get("operationId", ""),
            tags=operation.get("tags", []),
            parameters=parameters,
            request_body=request_body,
            responses=responses,
            security=operation.get("security", []),
        )

    def _parse_request_body(self, request_body: Dict[str, Any]) -> Dict[str, Any]:
        """解析请求体"""
        if "$ref" in request_body:
            request_body = self._resolve_ref(request_body["$ref"])

        content = request_body.get("content", {})
        result = {
            "required": request_body.get("required", False),
            "description": request_body.get("description", ""),
            "content": {},
        }

        for media_type, media_info in content.items():
            schema = media_info.get("schema", {})
            if "$ref" in schema:
                schema = self._resolve_ref(schema["$ref"])

            result["content"][media_type] = {
                "schema": schema,
                "example": media_info.get("example") or schema.get("example"),
            }

        return result

    def _get_schema_type(self, schema: Dict[str, Any]) -> str:
        """获取schema类型"""
        if "$ref" in schema:
            ref = schema["$ref"]
            return ref.split("/")[-1]
        return schema.get("type", "object")

    def _resolve_ref(self, ref: str) -> Dict[str, Any]:
        """解析引用"""
        parts = ref.lstrip("#/").split("/")
        result = self.spec
        for part in parts:
            result = result.get(part, {})
        return result

    def generate_example_request(self, endpoint: APIEndpoint) -> Dict[str, Any]:
        """为端点生成示例请求"""
        example = {
            "method": endpoint.method,
            "path": endpoint.path,
            "headers": {},
            "query_params": {},
            "path_params": {},
            "body": None,
        }

        for param in endpoint.parameters:
            if param.example:
                value = param.example
            elif param.default:
                value = param.default
            elif param.enum:
                value = param.enum[0]
            else:
                value = self._generate_example_value(param.param_type)

            if param.location == "query":
                example["query_params"][param.name] = value
            elif param.location == "path":
                example["path_params"][param.name] = value
            elif param.location == "header":
                example["headers"][param.name] = value

        if endpoint.request_body:
            content = endpoint.request_body.get("content", {})
            for media_type, media_info in content.items():
                if "application/json" in media_type:
                    example["body"] = media_info.get("example") or self._generate_example_from_schema(
                        media_info.get("schema", {})
                    )
                    break

        return example

    def _generate_example_value(self, type_name: str) -> Any:
        """生成示例值"""
        type_examples = {
            "string": "example_string",
            "integer": 1,
            "number": 1.0,
            "boolean": True,
            "array": [],
            "object": {},
        }
        return type_examples.get(type_name, "example")

    def _generate_example_from_schema(self, schema: Dict[str, Any]) -> Any:
        """从schema生成示例"""
        if "example" in schema:
            return schema["example"]

        schema_type = schema.get("type", "object")

        if schema_type == "object":
            result = {}
            properties = schema.get("properties", {})
            for prop_name, prop_schema in properties.items():
                if "$ref" in prop_schema:
                    prop_schema = self._resolve_ref(prop_schema["$ref"])
                result[prop_name] = self._generate_example_from_schema(prop_schema)
            return result
        elif schema_type == "array":
            items = schema.get("items", {})
            if "$ref" in items:
                items = self._resolve_ref(items["$ref"])
            return [self._generate_example_from_schema(items)]
        else:
            return self._generate_example_value(schema_type)
