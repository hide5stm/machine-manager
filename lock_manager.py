"""
楽観的ロック管理モジュール
"""
from typing import Optional, Dict, Any
from datetime import datetime

from database import get_db_connection


class OptimisticLockManager:
    """楽観的ロックを管理するクラス"""

    @staticmethod
    def get_server_version(server_id: int) -> Optional[int]:
        """サーバの現在のバージョンを取得"""
        with get_db_connection() as conn:
            result = conn.execute(
                'SELECT version FROM servers WHERE id = ?',
                (server_id,)
            ).fetchone()

            return result['version'] if result else None

    @staticmethod
    def check_version_conflict(server_id: int, expected_version: int) -> bool:
        """バージョン競合をチェック"""
        current_version = OptimisticLockManager.get_server_version(server_id)
        return current_version != expected_version

    @staticmethod
    def get_conflict_info(server_id: int) -> Optional[Dict[str, Any]]:
        """競合情報の取得"""
        with get_db_connection() as conn:
            result = conn.execute('''
                SELECT s.updated_by, s.updated_at, u.name, s.version
                FROM servers s
                LEFT JOIN users u ON s.updated_by = u.email
                WHERE s.id = ?
            ''', (server_id,)).fetchone()

            if result:
                return {
                    'updated_by': result['updated_by'],
                    'updated_at': result['updated_at'],
                    'user_name': result['name'] or result['updated_by'],
                    'version': result['version']
                }
                return None
