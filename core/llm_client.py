# LLM客户端 - 统一的大模型调用接口

import json
import os
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class LLMProvider(Enum):
    """支持的LLM提供商"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    GEMINI = "gemini"


@dataclass
class LLMConfig:
    """LLM配置"""
    provider: LLMProvider
    api_key: str
    model: str
    base_url: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 120


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

        self._openai_client = None
        self._anthropic_client = None
        self._gemini_client = None

    def _load_config_from_env(self) -> LLMConfig:
        """从环境变量加载配置"""
        provider_str = os.getenv("LLM_PROVIDER", "anthropic").lower()

        # 默认模型根据提供商设置
        default_models = {
            "openai": "gpt-4",
            "anthropic": "claude-sonnet-4-20250514",
            "azure_openai": "gpt-4",
            "gemini": "gemini-2.0-flash",
        }

        provider = LLMProvider(provider_str)
        default_model = default_models.get(provider_str, "claude-sonnet-4-20250514")

        # 根据提供商获取API Key
        api_key = os.getenv("LLM_API_KEY", "")
        if not api_key:
            if provider_str == "gemini":
                api_key = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
            elif provider_str == "anthropic":
                api_key = os.getenv("ANTHROPIC_API_KEY", "")
            elif provider_str == "openai":
                api_key = os.getenv("OPENAI_API_KEY", "")

        return LLMConfig(
            provider=provider,
            api_key=api_key,
            model=os.getenv("LLM_MODEL", default_model),
            base_url=os.getenv("LLM_BASE_URL"),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096")),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            timeout=int(os.getenv("LLM_TIMEOUT", "120")),
        )

    def _get_openai_client(self):
        """获取OpenAI客户端"""
        if self._openai_client is None:
            try:
                from openai import OpenAI
                self._openai_client = OpenAI(
                    api_key=self.config.api_key,
                    base_url=self.config.base_url,
                    timeout=self.config.timeout,
                )
            except ImportError:
                raise ImportError("请安装openai: pip install openai")
        return self._openai_client

    def _get_anthropic_client(self):
        """获取Anthropic客户端"""
        if self._anthropic_client is None:
            try:
                import anthropic
                self._anthropic_client = anthropic.Anthropic(
                    api_key=self.config.api_key,
                    base_url=self.config.base_url,
                    timeout=self.config.timeout,
                )
            except ImportError:
                raise ImportError("请安装anthropic: pip install anthropic")
        return self._anthropic_client

    def _get_gemini_client(self):
        """获取Gemini客户端"""
        if self._gemini_client is None:
            try:
                from google import genai
                self._gemini_client = genai.Client(api_key=self.config.api_key)
            except ImportError:
                raise ImportError("请安装google-genai: pip install google-genai")
        return self._gemini_client

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
            return self._call_anthropic(messages, max_tokens, temperature, response_format)
        elif self.config.provider == LLMProvider.AZURE_OPENAI:
            return self._call_azure_openai(messages, max_tokens, temperature, response_format)
        elif self.config.provider == LLMProvider.GEMINI:
            return self._call_gemini(messages, max_tokens, temperature, response_format)
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
        client = self._get_openai_client()

        kwargs = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature if temperature is not None else self.config.temperature,
        }

        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    def _call_anthropic(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int],
        temperature: Optional[float],
        response_format: Optional[str] = None,
    ) -> str:
        """调用Anthropic Claude API"""
        client = self._get_anthropic_client()

        # 分离system消息
        system_content = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_content += msg["content"] + "\n"
            else:
                chat_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        # 如果需要JSON输出，在system prompt中添加指示
        if response_format == "json":
            json_instruction = "\n\n重要：请确保你的响应是有效的JSON格式，不要包含任何其他文字说明。直接输出JSON对象，不要使用markdown代码块。"
            system_content += json_instruction

        kwargs = {
            "model": self.config.model,
            "messages": chat_messages,
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature if temperature is not None else self.config.temperature,
        }

        if system_content.strip():
            kwargs["system"] = system_content.strip()

        response = client.messages.create(**kwargs)
        return response.content[0].text

    def _call_azure_openai(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int],
        temperature: Optional[float],
        response_format: Optional[str],
    ) -> str:
        """调用Azure OpenAI API"""
        try:
            from openai import AzureOpenAI
        except ImportError:
            raise ImportError("请安装openai: pip install openai")

        if not self.config.base_url:
            raise ValueError("Azure OpenAI需要配置base_url (Azure endpoint)")

        # 从环境变量获取Azure特定配置
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

        client = AzureOpenAI(
            api_key=self.config.api_key,
            api_version=api_version,
            azure_endpoint=self.config.base_url,
            timeout=self.config.timeout,
        )

        kwargs = {
            "model": self.config.model,  # 在Azure中这是deployment名称
            "messages": messages,
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature if temperature is not None else self.config.temperature,
        }

        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    def _call_gemini(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int],
        temperature: Optional[float],
        response_format: Optional[str] = None,
    ) -> str:
        """调用Google Gemini API"""
        from google import genai
        from google.genai import types

        client = self._get_gemini_client()

        # 分离system消息和构建内容
        system_instruction = ""
        contents = []

        for msg in messages:
            if msg["role"] == "system":
                system_instruction += msg["content"] + "\n"
            elif msg["role"] == "user":
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=msg["content"])]
                ))
            elif msg["role"] == "assistant":
                contents.append(types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=msg["content"])]
                ))

        # 如果需要JSON输出，在system instruction中添加指示
        if response_format == "json":
            json_instruction = "\n\n重要：请确保你的响应是有效的JSON格式，不要包含任何其他文字说明。直接输出JSON对象，不要使用markdown代码块。"
            system_instruction += json_instruction

        # 构建生成配置
        generation_config = types.GenerateContentConfig(
            max_output_tokens=max_tokens or self.config.max_tokens,
            temperature=temperature if temperature is not None else self.config.temperature,
        )

        if system_instruction.strip():
            generation_config.system_instruction = system_instruction.strip()

        # 如果需要JSON输出，设置response_mime_type
        if response_format == "json":
            generation_config.response_mime_type = "application/json"

        response = client.models.generate_content(
            model=self.config.model,
            contents=contents,
            config=generation_config,
        )

        return response.text

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
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
            if json_match:
                return json.loads(json_match.group(1))

            # 尝试找到JSON对象的开始和结束
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group(0))

            raise ValueError(f"无法解析JSON响应: {response[:500]}...")

    def close(self):
        """关闭客户端"""
        # SDK客户端通常不需要显式关闭
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 便捷函数
def get_llm_client() -> LLMClient:
    """获取LLM客户端实例"""
    return LLMClient()
