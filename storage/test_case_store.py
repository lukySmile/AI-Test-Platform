# 测试用例存储

import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import uuid


class TestCaseStore:
    """测试用例存储"""

    def __init__(self, storage_path: str = "./data/test_cases"):
        """
        初始化存储

        Args:
            storage_path: 存储路径
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _generate_id(self) -> str:
        """生成唯一ID"""
        return f"tc_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"

    def save(self, data: Dict[str, Any], case_id: Optional[str] = None) -> str:
        """
        保存测试用例

        Args:
            data: 测试用例数据
            case_id: 可选的用例ID

        Returns:
            用例ID
        """
        if not case_id:
            case_id = self._generate_id()

        data["id"] = case_id
        data["saved_at"] = datetime.now().isoformat()

        file_path = self.storage_path / f"{case_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return case_id

    def get(self, case_id: str) -> Optional[Dict[str, Any]]:
        """
        获取测试用例

        Args:
            case_id: 用例ID

        Returns:
            测试用例数据
        """
        file_path = self.storage_path / f"{case_id}.json"
        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def delete(self, case_id: str) -> bool:
        """
        删除测试用例

        Args:
            case_id: 用例ID

        Returns:
            是否成功
        """
        file_path = self.storage_path / f"{case_id}.json"
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def list(
        self,
        page: int = 1,
        page_size: int = 20,
        module: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取测试用例列表

        Args:
            page: 页码
            page_size: 每页数量
            module: 模块过滤

        Returns:
            分页结果
        """
        all_files = sorted(self.storage_path.glob("*.json"), reverse=True)

        items = []
        for file_path in all_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                    # 模块过滤
                    if module and data.get("module") != module:
                        continue

                    items.append({
                        "id": data.get("id"),
                        "module": data.get("module", data.get("api_name", "未指定")),
                        "test_cases_count": len(data.get("test_cases", [])),
                        "generated_at": data.get("generated_at"),
                        "saved_at": data.get("saved_at"),
                    })
            except (json.JSONDecodeError, IOError):
                continue

        # 分页
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        page_items = items[start:end]

        return {
            "items": page_items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    def search(self, keyword: str) -> List[Dict[str, Any]]:
        """
        搜索测试用例

        Args:
            keyword: 关键词

        Returns:
            匹配的用例列表
        """
        results = []
        for file_path in self.storage_path.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # 在模块名和测试用例标题中搜索
                module = data.get("module", data.get("api_name", ""))
                if keyword.lower() in module.lower():
                    results.append(data)
                    continue

                for tc in data.get("test_cases", []):
                    if keyword.lower() in tc.get("title", "").lower():
                        results.append(data)
                        break

            except (json.JSONDecodeError, IOError):
                continue

        return results
