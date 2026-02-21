# LLM客户端 - 统一的大模型调用接口

import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import httpx


class LLMProvider(Enum):
    """支持的LLM提供商"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    LOCAL = "local"  # 本地模型


@dataclass
class LLMConfig:
    """LLM配置"""
    provider: LLMProvider
    api_key: str
    model: str
    base_url: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 60


class LLMClient:
    """统一的LLM客户端"""

    def __init__(self, config: Optional[LLMConfig] = None):
        """
        初始化LLM客户端

        Args:
            config: LLM配置，如果为None则从环境变量读取
        """
        if config:
            self.config = config
        else:
            self.config = self._load_config_from_env()

        self._client = httpx.Client(timeout=self.config.timeout)

    def _load_config_from_env(self) -> LLMConfig:
        """从环境变量加载配置"""
        provider = LLMProvider(os.getenv("LLM_PROVIDER", "openai"))
        return LLMConfig(
            provider=provider,
            api_key=os.getenv("LLM_API_KEY", ""),
            model=os.getenv("LLM_MODEL", "gpt-4"),
            base_url=os.getenv("LLM_BASE_URL"),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096")),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
        )

    def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        response_format: Optional[str] = None,
    ) -> str:
        """
        发送聊天请求

        Args:
            messages: 消息列表
            max_tokens: 最大token数
            temperature: 温度参数
            response_format: 响应格式 ("json" 或 None)

        Returns:
            模型响应文本
        """
        if self.config.provider == LLMProvider.OPENAI:
            return self._call_openai(messages, max_tokens, temperature, response_format)
        elif self.config.provider == LLMProvider.ANTHROPIC:
            return self._call_anthropic(messages, max_tokens, temperature)
        elif self.config.provider == LLMProvider.AZURE_OPENAI:
            return self._call_azure_openai(messages, max_tokens, temperature, response_format)
        else:
            raise ValueError(f"不支持的LLM提供商: {self.config.provider}")

    def _call_openai(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int],
        temperature: Optional[float],
        response_format: Optional[str],
    ) -> str:
        """调用OpenAI API"""
        url = self.config.base_url or "https://api.openai.com/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature if temperature is not None else self.config.temperature,
        }

        if response_format == "json":
            payload["response_format"] = {"type": "json_object"}

        response = self._client.post(url, headers=headers, json=payload)
        response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"]

    def _call_anthropic(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int],
        temperature: Optional[float],
    ) -> str:
        """调用Anthropic API"""
        url = self.config.base_url or "https://api.anthropic.com/v1/messages"

        # 分离system消息
        system_content = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                chat_messages.append(msg)

        headers = {
            "x-api-key": self.config.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        payload = {
            "model": self.config.model,
            "messages": chat_messages,
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature if temperature is not None else self.config.temperature,
        }

        if system_content:
            payload["system"] = system_content

        response = self._client.post(url, headers=headers, json=payload)
        response.raise_for_status()

        data = response.json()
        return data["content"][0]["text"]

    def _call_azure_openai(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int],
        temperature: Optional[float],
        response_format: Optional[str],
    ) -> str:
        """调用Azure OpenAI API"""
        if not self.config.base_url:
            raise ValueError("Azure OpenAI需要配置base_url")

        url = f"{self.config.base_url}/openai/deployments/{self.config.model}/chat/completions?api-version=2024-02-15-preview"

        headers = {
            "api-key": self.config.api_key,
            "Content-Type": "application/json",
        }

        payload = {
            "messages": messages,
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature if temperature is not None else self.config.temperature,
        }

        if response_format == "json":
            payload["response_format"] = {"type": "json_object"}

        response = self._client.post(url, headers=headers, json=payload)
        response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"]

    def generate_json(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        生成JSON响应

        Args:
            messages: 消息列表
            max_tokens: 最大token数
            temperature: 温度参数

        Returns:
            解析后的JSON对象
        """
        response = self.chat(
            messages,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format="json"
        )

        # 尝试从响应中提取JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # 尝试提取代码块中的JSON
            import re
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
            if json_match:
                return json.loads(json_match.group(1))
            raise ValueError(f"无法解析JSON响应: {response[:200]}...")

    def close(self):
        """关闭客户端"""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
