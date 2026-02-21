# 应用配置

import os
from typing import List, Optional
from dataclasses import dataclass, field
from functools import lru_cache


@dataclass
class Settings:
    """应用配置"""

    # 环境
    environment: str = "development"
    debug: bool = True

    # API配置
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # CORS配置
    cors_origins: List[str] = field(default_factory=lambda: ["*"])

    # LLM配置
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_model: str = "gpt-4"
    llm_base_url: Optional[str] = None
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.7

    # 存储配置
    storage_type: str = "file"  # file, redis, database
    storage_path: str = "./data"

    # Redis配置（如果使用Redis）
    redis_url: str = "redis://localhost:6379"

    # 报告配置
    reports_dir: str = "./reports"

    # 日志配置
    log_level: str = "INFO"
    log_file: Optional[str] = None

    @classmethod
    def from_env(cls) -> "Settings":
        """从环境变量加载配置"""
        return cls(
            environment=os.getenv("ENVIRONMENT", "development"),
            debug=os.getenv("DEBUG", "true").lower() == "true",
            api_host=os.getenv("API_HOST", "0.0.0.0"),
            api_port=int(os.getenv("API_PORT", "8000")),
            cors_origins=os.getenv("CORS_ORIGINS", "*").split(","),
            llm_provider=os.getenv("LLM_PROVIDER", "openai"),
            llm_api_key=os.getenv("LLM_API_KEY", ""),
            llm_model=os.getenv("LLM_MODEL", "gpt-4"),
            llm_base_url=os.getenv("LLM_BASE_URL"),
            llm_max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096")),
            llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            storage_type=os.getenv("STORAGE_TYPE", "file"),
            storage_path=os.getenv("STORAGE_PATH", "./data"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
            reports_dir=os.getenv("REPORTS_DIR", "./reports"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=os.getenv("LOG_FILE"),
        )


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings.from_env()
