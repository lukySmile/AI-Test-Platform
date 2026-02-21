# 测试结果存储

import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import uuid


class TestResultStore:
    """测试结果存储"""

    def __init__(self, storage_path: str = "./data/test_results"):
        """
        初始化存储

        Args:
            storage_path: 存储路径
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _generate_id(self) -> str:
        """生成唯一ID"""
        return f"result_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"

    def save(self, data: Dict[str, Any], result_id: Optional[str] = None) -> str:
        """
        保存测试结果

        Args:
            data: 测试结果数据
            result_id: 可选的结果ID

        Returns:
            结果ID
        """
        if not result_id:
            result_id = self._generate_id()

        data["id"] = result_id
        data["saved_at"] = datetime.now().isoformat()

        file_path = self.storage_path / f"{result_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return result_id

    def get(self, result_id: str) -> Optional[Dict[str, Any]]:
        """
        获取测试结果

        Args:
            result_id: 结果ID

        Returns:
            测试结果数据
        """
        file_path = self.storage_path / f"{result_id}.json"
        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def delete(self, result_id: str) -> bool:
        """
        删除测试结果

        Args:
            result_id: 结果ID

        Returns:
            是否成功
        """
        file_path = self.storage_path / f"{result_id}.json"
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def list(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取测试结果列表

        Args:
            page: 页码
            page_size: 每页数量
            status: 状态过滤 (passed, failed)

        Returns:
            分页结果
        """
        all_files = sorted(self.storage_path.glob("*.json"), reverse=True)

        items = []
        for file_path in all_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                    # 判断整体状态
                    pass_rate = data.get("pass_rate", 0)
                    result_status = "passed" if pass_rate == 100 else "failed"

                    # 状态过滤
                    if status and result_status != status:
                        continue

                    items.append({
                        "id": data.get("id"),
                        "suite_name": data.get("suite_name", "未命名"),
                        "total": data.get("total", 0),
                        "passed": data.get("passed", 0),
                        "failed": data.get("failed", 0),
                        "pass_rate": pass_rate,
                        "total_time_ms": data.get("total_time_ms", 0),
                        "started_at": data.get("started_at"),
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

    def get_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        获取统计数据

        Args:
            days: 统计天数

        Returns:
            统计结果
        """
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)
        total_runs = 0
        total_passed = 0
        total_failed = 0
        pass_rates = []

        for file_path in self.storage_path.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # 检查时间
                saved_at = data.get("saved_at", data.get("started_at"))
                if saved_at:
                    saved_time = datetime.fromisoformat(saved_at.replace("Z", "+00:00").split("+")[0])
                    if saved_time < cutoff:
                        continue

                total_runs += 1
                total_passed += data.get("passed", 0)
                total_failed += data.get("failed", 0)
                pass_rates.append(data.get("pass_rate", 0))

            except (json.JSONDecodeError, IOError, ValueError):
                continue

        avg_pass_rate = sum(pass_rates) / len(pass_rates) if pass_rates else 0

        return {
            "period_days": days,
            "total_runs": total_runs,
            "total_test_cases": total_passed + total_failed,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "average_pass_rate": round(avg_pass_rate, 2),
        }
