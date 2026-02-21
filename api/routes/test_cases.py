# 测试用例相关路由

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

from core.llm_client import LLMClient
from core.test_case_service import TestCaseService
from parsers.swagger_parser import SwaggerParser
from parsers.openapi_parser import OpenAPIParser
from parsers.requirement_parser import RequirementParser
from storage.test_case_store import TestCaseStore
from utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)
store = TestCaseStore()


# ==================== 请求模型 ====================

class GenerateFromRequirementRequest(BaseModel):
    """从需求生成测试用例请求"""
    requirement: str = Field(..., description="需求描述")
    module_name: Optional[str] = Field(None, description="模块名称")

    class Config:
        json_schema_extra = {
            "example": {
                "requirement": "用户登录功能：支持手机号+密码登录，密码要求8-20位",
                "module_name": "用户模块"
            }
        }


class GenerateFromAPIRequest(BaseModel):
    """从API规范生成测试用例请求"""
    api_spec: str = Field(..., description="API规范（JSON或YAML格式）")
    spec_type: str = Field("openapi", description="规范类型: swagger, openapi")
    base_url: Optional[str] = Field(None, description="API基础URL")


class TestCaseResponse(BaseModel):
    """测试用例响应"""
    id: str
    module: str
    test_cases: List[Dict[str, Any]]
    generated_at: str
    total_count: int


# ==================== 路由处理 ====================

@router.post("/generate/requirement", response_model=TestCaseResponse)
async def generate_from_requirement(request: GenerateFromRequirementRequest):
    """
    从需求描述生成测试用例

    根据提供的需求文档或功能描述，使用AI自动生成完整的测试用例。

    - **requirement**: 需求描述文本
    - **module_name**: 可选的模块名称
    """
    try:
        logger.info(f"生成测试用例 - 模块: {request.module_name}")

        llm_client = LLMClient()
        service = TestCaseService(llm_client)

        result = service.generate_test_cases(
            requirement=request.requirement,
            module_name=request.module_name,
        )

        # 保存到存储
        case_id = store.save(result)

        service.close()

        return TestCaseResponse(
            id=case_id,
            module=result.get("module", "未指定"),
            test_cases=result.get("test_cases", []),
            generated_at=result.get("generated_at", datetime.now().isoformat()),
            total_count=len(result.get("test_cases", [])),
        )

    except Exception as e:
        logger.error(f"生成测试用例失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@router.post("/generate/api", response_model=TestCaseResponse)
async def generate_from_api(request: GenerateFromAPIRequest):
    """
    从API规范生成测试用例

    支持Swagger 2.0和OpenAPI 3.x格式的API文档。

    - **api_spec**: API规范文档（JSON或YAML）
    - **spec_type**: 规范类型（swagger或openapi）
    - **base_url**: 可选的API基础URL
    """
    try:
        logger.info(f"从{request.spec_type}生成API测试用例")

        # 解析API规范
        if request.spec_type == "swagger":
            parser = SwaggerParser()
        else:
            parser = OpenAPIParser()

        api_spec = parser.parse(request.api_spec)

        # 生成测试用例
        llm_client = LLMClient()
        service = TestCaseService(llm_client)

        result = service.generate_api_test_cases(
            api_spec=api_spec.to_prompt_format(),
            base_url=request.base_url or api_spec.base_url,
        )

        case_id = store.save(result)
        service.close()

        return TestCaseResponse(
            id=case_id,
            module=result.get("api_name", "API测试"),
            test_cases=result.get("test_cases", []),
            generated_at=result.get("generated_at", datetime.now().isoformat()),
            total_count=len(result.get("test_cases", [])),
        )

    except Exception as e:
        logger.error(f"生成API测试用例失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@router.post("/generate/upload")
async def generate_from_file(
    file: UploadFile = File(..., description="需求文档或API规范文件"),
    doc_type: str = Form("requirement", description="文档类型: requirement, swagger, openapi"),
):
    """
    上传文件生成测试用例

    支持上传Markdown需求文档或Swagger/OpenAPI规范文件。
    """
    try:
        content = await file.read()
        content_str = content.decode("utf-8")

        if doc_type == "requirement":
            parser = RequirementParser()
            req_doc = parser.parse(content_str, title=file.filename)

            llm_client = LLMClient()
            service = TestCaseService(llm_client)
            result = service.generate_test_cases(
                requirement=req_doc.to_prompt_format(),
                module_name=req_doc.title,
            )
            service.close()

        elif doc_type in ["swagger", "openapi"]:
            parser = SwaggerParser() if doc_type == "swagger" else OpenAPIParser()
            api_spec = parser.parse(content_str)

            llm_client = LLMClient()
            service = TestCaseService(llm_client)
            result = service.generate_api_test_cases(
                api_spec=api_spec.to_prompt_format(),
                base_url=api_spec.base_url,
            )
            service.close()

        else:
            raise HTTPException(status_code=400, detail=f"不支持的文档类型: {doc_type}")

        case_id = store.save(result)

        return {
            "id": case_id,
            "filename": file.filename,
            "doc_type": doc_type,
            "test_cases_count": len(result.get("test_cases", [])),
            "generated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"处理上传文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{case_id}")
async def get_test_case(case_id: str):
    """获取测试用例详情"""
    result = store.get(case_id)
    if not result:
        raise HTTPException(status_code=404, detail="测试用例不存在")
    return result


@router.get("/")
async def list_test_cases(
    page: int = 1,
    page_size: int = 20,
    module: Optional[str] = None,
):
    """获取测试用例列表"""
    return store.list(page=page, page_size=page_size, module=module)


@router.delete("/{case_id}")
async def delete_test_case(case_id: str):
    """删除测试用例"""
    success = store.delete(case_id)
    if not success:
        raise HTTPException(status_code=404, detail="测试用例不存在")
    return {"message": "删除成功"}


@router.post("/analyze")
async def analyze_requirement(request: GenerateFromRequirementRequest):
    """
    分析需求文档

    提取测试点、风险点和待澄清事项。
    """
    try:
        llm_client = LLMClient()
        service = TestCaseService(llm_client)

        result = service.analyze_requirement(request.requirement)
        service.close()

        return result

    except Exception as e:
        logger.error(f"分析需求失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
