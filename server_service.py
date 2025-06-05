"""
サーバ業務ロジック
"""
from typing import Dict, Any, Optional
import pandas as pd

from database import DatabaseManager
from history_manager import HistoryManager
from lock_manager import OptimisticLockManager


class ServerService:
    """サーバに関する業務ロジックを管理するクラス"""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.history_manager = HistoryManager()
        self.lock_manager = OptimisticLockManager()

    def get_all_servers(self) -> pd.DataFrame:
        """全サーバ情報の取得"""
        return self.db_manager.get_servers()

    def get_server_by_id(self, server_id: int) -> Optional[Dict[str, Any]]:
        """特定のサーバ情報を取得"""
        server = self.db_manager.get_server_by_id(server_id)
        return dict(server) if server else None

    def create_server(self, server_data: Dict[str, Any]) -> int:
        """新規サーバの作成"""
        # サーバ追加
        server_id = self.db_manager.add_server(server_data)

        # 履歴記録
        self.history_manager.record_server_creation(server_id, server_data['model'])

        return server_id

    def update_server(self, server_id: int, old_data: Dict[str, Any], new_data: Dict[str, Any]) -> tuple[bool, str]:
        """サーバ情報の更新（楽観的ロック）"""
        try:
            expected_version = old_data.get('version', 1)

            # 楽観的ロックによる更新
            success = self.db_manager.update_server(server_id, new_data, expected_version)

            if not success:
                # バージョン競合が発生
                conflict_info = self.lock_manager.get_conflict_info(server_id)
                if conflict_info:
                    return False, f"他のユーザー（{conflict_info['user_name']}）が先に更新しました。\n更新日時: {conflict_info['updated_at']}"
                else:
                    return False, "サーバが存在しないか、既に削除されています。"

            # 履歴記録
            self.history_manager.record_server_update(server_id, old_data, new_data)

            return True, "更新が完了しました。"

        except Exception as e:
            print(f"Error updating server: {e}")
            return False, "更新中にエラーが発生しました。"

    def delete_server(self, server_id: int, user_email: str) -> bool:
        """サーバの削除"""
        try:
            # サーバ削除
            model = self.db_manager.delete_server(server_id)

            # 履歴記録
            if model:
                self.history_manager.record_server_deletion(server_id, model)

            return True
        except Exception as e:
            print(f"Error deleting server: {e}")
            return False

    def search_servers(self, df: pd.DataFrame, search_term: str) -> pd.DataFrame:
        """サーバ検索"""
        if not search_term:
            return df

        mask = df.astype(str).apply(
            lambda x: x.str.contains(search_term, case=False, na=False)
        ).any(axis=1)
        return df[mask]

    def get_statistics(self) -> Dict[str, int]:
        """統計情報の取得"""
        return self.db_manager.get_statistics()

    def validate_server_data(self, server_data: Dict[str, Any]) -> tuple[bool, str]:
        """サーバデータのバリデーション"""
        if not server_data.get('model'):
            return False, "型番は必須項目です。"

        if not server_data.get('location'):
            return False, "設置場所は必須項目です。"

        return True, ""

    def check_version_conflict(self, server_id: int, expected_version: int) -> bool:
        """バージョン競合をチェック"""
        return self.lock_manager.check_version_conflict(server_id, expected_version)
