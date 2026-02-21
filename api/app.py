# FastAPI 应用主入口

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from pathlib import Path

from .routes import test_cases, api_test, ios_test, android_test, reports
from config.settings import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("AI测试平台启动中...")
    settings = get_settings()
    logger.info(f"环境: {settings.environment}")

    yield

    # 关闭时
    logger.info("AI测试平台关闭")


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    settings = get_settings()

    app = FastAPI(
        title="AI测试平台",
        description="""
## AI测试平台 API

### 核心功能

1. **测试用例自动生成**
   - 根据需求文档自动生成测试用例
   - 支持API测试、iOS UI测试

2. **API测试自动化**
   - 解析Swagger/OpenAPI文档
   - 一键执行API测试
   - 自动生成测试报告

3. **iOS模拟器测试**
   - 生成XCUITest测试代码
   - 自动运行iOS测试
   - 生成测试报告

4. **Android模拟器测试**
   - 生成Espresso/UI Automator测试代码
   - 自动运行Android测试
   - 生成测试报告

### 使用说明
- 所有接口都支持JSON格式
- 需要认证的接口请在Header中携带 `Authorization: Bearer <token>`
        """,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(test_cases.router, prefix="/api/v1/test-cases", tags=["测试用例"])
    app.include_router(api_test.router, prefix="/api/v1/api-test", tags=["API测试"])
    app.include_router(ios_test.router, prefix="/api/v1/ios-test", tags=["iOS测试"])
    app.include_router(android_test.router, prefix="/api/v1/android-test", tags=["Android测试"])
    app.include_router(reports.router, prefix="/api/v1/reports", tags=["测试报告"])

    # 静态文件
    reports_dir = Path("./reports")
    reports_dir.mkdir(exist_ok=True)
    app.mount("/reports", StaticFiles(directory=str(reports_dir)), name="reports")

    # 前端静态文件
    static_dir = Path("./static")
    static_dir.mkdir(exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", tags=["系统"], include_in_schema=False)
    async def root():
        """首页 - 返回前端页面"""
        index_file = Path("./static/index.html")
        if index_file.exists():
            return FileResponse(index_file)
        return {
            "name": "AI测试平台",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs",
        }

    @app.get("/api", tags=["系统"])
    async def api_info():
        """API信息"""
        return {
            "name": "AI测试平台",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs",
        }

    @app.get("/health", tags=["系统"])
    async def health_check():
        """健康检查"""
        return {"status": "healthy"}

    return app


# 创建应用实例
app = create_app()
