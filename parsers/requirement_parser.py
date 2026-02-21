# 需求文档解析器

import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class RequirementType(Enum):
    """需求类型"""
    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    BUSINESS_RULE = "business_rule"
    CONSTRAINT = "constraint"


@dataclass
class Requirement:
    """需求项"""
    id: str
    title: str
    description: str
    requirement_type: RequirementType
    priority: str  # P0-P3
    acceptance_criteria: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "type": self.requirement_type.value,
            "priority": self.priority,
            "acceptance_criteria": self.acceptance_criteria,
            "dependencies": self.dependencies,
            "tags": self.tags,
        }


@dataclass
class RequirementDocument:
    """需求文档"""
    title: str
    version: str
    description: str
    requirements: List[Requirement]
    glossary: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "version": self.version,
            "description": self.description,
            "requirements": [r.to_dict() for r in self.requirements],
            "glossary": self.glossary,
        }

    def to_prompt_format(self) -> str:
        """转换为Prompt格式"""
        lines = [
            f"# 需求文档: {self.title}",
            f"版本: {self.version}",
            "",
            f"## 概述",
            self.description,
            "",
            "## 需求列表",
            "",
        ]

        for req in self.requirements:
            lines.append(f"### [{req.id}] {req.title}")
            lines.append(f"**类型**: {req.requirement_type.value}")
            lines.append(f"**优先级**: {req.priority}")
            lines.append("")
            lines.append(f"**描述**: {req.description}")
            lines.append("")

            if req.acceptance_criteria:
                lines.append("**验收标准**:")
                for ac in req.acceptance_criteria:
                    lines.append(f"- {ac}")
                lines.append("")

            if req.dependencies:
                lines.append(f"**依赖**: {', '.join(req.dependencies)}")
                lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)


class RequirementParser:
    """需求文档解析器"""

    def __init__(self):
        self.requirement_counter = 0

    def parse(self, content: str, title: str = "需求文档") -> RequirementDocument:
        """
        解析需求文档

        Args:
            content: 文档内容
            title: 文档标题

        Returns:
            RequirementDocument对象
        """
        self.requirement_counter = 0

        # 提取需求项
        requirements = self._extract_requirements(content)

        # 提取术语表
        glossary = self._extract_glossary(content)

        # 提取概述
        description = self._extract_description(content)

        return RequirementDocument(
            title=title,
            version="1.0",
            description=description,
            requirements=requirements,
            glossary=glossary,
        )

    def _extract_requirements(self, content: str) -> List[Requirement]:
        """提取需求项"""
        requirements = []

        # 匹配标题模式
        # 支持多种格式:
        # - ## 1. 功能名称
        # - ### REQ-001: 功能名称
        # - **功能名称**
        # - 1. 功能名称

        patterns = [
            r'#{2,4}\s*(?:\d+\.)?\s*([^\n]+)',  # Markdown标题
            r'\*\*([^\*]+)\*\*',  # 粗体标题
            r'^\d+\.\s+([^\n]+)',  # 数字列表
        ]

        # 分段处理
        sections = self._split_into_sections(content)

        for section in sections:
            req = self._parse_section(section)
            if req:
                requirements.append(req)

        return requirements

    def _split_into_sections(self, content: str) -> List[str]:
        """将内容分割为段落"""
        # 按二级或三级标题分割
        sections = re.split(r'\n(?=#{2,3}\s)', content)
        return [s.strip() for s in sections if s.strip()]

    def _parse_section(self, section: str) -> Optional[Requirement]:
        """解析单个段落"""
        lines = section.split('\n')
        if not lines:
            return None

        # 提取标题
        title_line = lines[0].strip()
        title_match = re.match(r'#{2,4}\s*(?:\d+\.)?\s*(.+)', title_line)
        if not title_match:
            return None

        title = title_match.group(1).strip()

        # 跳过非功能性章节
        skip_titles = ['概述', '介绍', '目录', '修订记录', '术语', '附录']
        if any(skip in title for skip in skip_titles):
            return None

        # 生成ID
        self.requirement_counter += 1
        req_id = f"REQ_{self.requirement_counter:03d}"

        # 提取描述（剩余内容）
        description_lines = []
        acceptance_criteria = []
        in_acceptance = False

        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue

            # 检查验收标准
            if '验收' in line or 'AC' in line or '标准' in line:
                in_acceptance = True
                continue

            if in_acceptance:
                if line.startswith(('-', '*', '•')):
                    acceptance_criteria.append(line.lstrip('-*• '))
                elif re.match(r'^\d+\.', line):
                    acceptance_criteria.append(re.sub(r'^\d+\.\s*', '', line))
            else:
                description_lines.append(line)

        description = ' '.join(description_lines)

        # 推断优先级
        priority = self._infer_priority(title, description)

        # 推断类型
        req_type = self._infer_type(title, description)

        # 提取标签
        tags = self._extract_tags(title, description)

        return Requirement(
            id=req_id,
            title=title,
            description=description,
            requirement_type=req_type,
            priority=priority,
            acceptance_criteria=acceptance_criteria,
            dependencies=[],
            tags=tags,
        )

    def _infer_priority(self, title: str, description: str) -> str:
        """推断优先级"""
        text = f"{title} {description}".lower()

        if any(word in text for word in ['核心', '必须', '关键', '登录', '支付', '安全']):
            return "P0"
        elif any(word in text for word in ['重要', '主要', '常用']):
            return "P1"
        elif any(word in text for word in ['可选', '优化', '改进']):
            return "P3"
        else:
            return "P2"

    def _infer_type(self, title: str, description: str) -> RequirementType:
        """推断需求类型"""
        text = f"{title} {description}".lower()

        if any(word in text for word in ['性能', '并发', '响应时间', '可用性', '安全']):
            return RequirementType.NON_FUNCTIONAL
        elif any(word in text for word in ['规则', '约束', '限制', '校验']):
            return RequirementType.BUSINESS_RULE
        elif any(word in text for word in ['必须', '应该', '不能', '禁止']):
            return RequirementType.CONSTRAINT
        else:
            return RequirementType.FUNCTIONAL

    def _extract_tags(self, title: str, description: str) -> List[str]:
        """提取标签"""
        tags = []
        text = f"{title} {description}".lower()

        tag_keywords = {
            'login': ['登录', '认证', '授权'],
            'payment': ['支付', '订单', '交易'],
            'user': ['用户', '账户', '个人'],
            'search': ['搜索', '查询', '筛选'],
            'notification': ['通知', '消息', '推送'],
            'settings': ['设置', '配置', '偏好'],
        }

        for tag, keywords in tag_keywords.items():
            if any(kw in text for kw in keywords):
                tags.append(tag)

        return tags

    def _extract_glossary(self, content: str) -> Dict[str, str]:
        """提取术语表"""
        glossary = {}

        # 查找术语定义模式
        # 术语: 定义
        # **术语**: 定义
        patterns = [
            r'\*\*([^*]+)\*\*:\s*([^\n]+)',
            r'([^：:]+)[：:]\s*([^\n]+)',
        ]

        glossary_section = re.search(r'术语.*?(?=#{2,3}|\Z)', content, re.DOTALL)
        if glossary_section:
            section_text = glossary_section.group(0)
            for pattern in patterns:
                matches = re.findall(pattern, section_text)
                for term, definition in matches[:20]:  # 限制数量
                    term = term.strip()
                    definition = definition.strip()
                    if len(term) < 30 and len(definition) < 200:
                        glossary[term] = definition

        return glossary

    def _extract_description(self, content: str) -> str:
        """提取文档概述"""
        # 查找概述部分
        patterns = [
            r'概述[：:\s]*([^\n]+(?:\n(?!#{2,3})[^\n]+)*)',
            r'简介[：:\s]*([^\n]+(?:\n(?!#{2,3})[^\n]+)*)',
            r'^([^\n#]+(?:\n(?!#{2,3})[^\n]+)*)',
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.MULTILINE)
            if match:
                desc = match.group(1).strip()
                if len(desc) > 20:
                    return desc[:500]

        return "需求文档"

    def parse_user_story(self, story: str) -> Requirement:
        """
        解析用户故事

        格式: As a [user], I want [feature], so that [benefit]
        """
        self.requirement_counter += 1
        req_id = f"US_{self.requirement_counter:03d}"

        # 尝试解析用户故事格式
        pattern = r'[作为|As]\s*(?:一个|a)?\s*(.+?)[，,]\s*[我想要|I want]\s*(.+?)[，,]\s*[以便|so that]\s*(.+)'
        match = re.search(pattern, story, re.IGNORECASE)

        if match:
            user = match.group(1).strip()
            feature = match.group(2).strip()
            benefit = match.group(3).strip()
            title = feature
            description = f"作为{user}，我想要{feature}，以便{benefit}"
        else:
            title = story[:50] if len(story) > 50 else story
            description = story

        return Requirement(
            id=req_id,
            title=title,
            description=description,
            requirement_type=RequirementType.FUNCTIONAL,
            priority="P1",
            acceptance_criteria=[],
            dependencies=[],
            tags=[],
        )
