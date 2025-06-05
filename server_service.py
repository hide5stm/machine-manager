"""
サーバ業務ロジック
"""
from typing import Dict, Any, Optional
import pandas as pd

from database import DatabaseManager
from history_manager import HistoryManager
from lock_manager import LockManager


class ServerService:
    """サーバに関する業務ロジックを管理するクラス"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.history_manager = HistoryManager()
        self.lock_manager = LockManager()
    
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
    
    def update_server(self, server_id: int, old_data: Dict[str, Any], new_data: Dict[str, Any]) -> bool:
        """サーバ情報の更新"""
        try:
            # サーバ更新
            self.db_manager.update_server(server_id, new_data)
            
            # 履歴記録
            self.history_manager.record_server_update(server_id, old_data, new_data)
            
            return True
        except Exception as e:
            print(f"Error updating server: {e}")
            return False
    
    def delete_server(self, server_id: int, user_email: str) -> bool:
        """サーバの削除"""
        try:
            # ロック取得
            if not self.lock_manager.acquire_lock(server_id, user_email):
                return False
            
            # サーバ削除
            model = self.db_manager.delete_server(server_id)
            
            # 履歴記録
            if model:
                self.history_manager.record_server_deletion(server_id, model)
            
            # ロック解除
            self.lock_manager.release_lock(server_id, user_email)
            
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
    
    def can_edit_server(self, server_id: int, user_email: str) -> bool:
        """サーバ編集可能かチェック"""
        return not self.lock_manager.is_locked_by_others(server_id, user_email)
    
    def acquire_edit_lock(self, server_id: int, user_email: str) -> bool:
        """編集ロックの取得"""
        return self.lock_manager.acquire_lock(server_id, user_email)
    
    def release_edit_lock(self, server_id: int, user_email: str):
        """編集ロックの解除"""
        self.lock_manager.release_lock(server_id, user_email)
    
    def get_lock_info(self, server_id: int) -> Optional[Dict[str, Any]]:
        """ロック情報の取得"""
        return self.lock_manager.get_lock_info(server_id)
    
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
