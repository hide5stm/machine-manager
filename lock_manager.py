"""
排他制御管理モジュール
"""
from typing import Optional, Dict, Any
from datetime import datetime

from config import LOCK_TIMEOUT_MINUTES
from database import get_db_connection


class LockManager:
    """排他制御を管理するクラス"""
    
    @staticmethod
    def acquire_lock(server_id: int, user_email: str) -> bool:
        """サーバ編集ロックの取得"""
        with get_db_connection() as conn:
            # 古いロックを削除
            conn.execute('''
                DELETE FROM edit_locks 
                WHERE locked_at < datetime('now', '-{} minutes')
            '''.format(LOCK_TIMEOUT_MINUTES))
            
            # 既存のロックを確認
            existing_lock = conn.execute(
                'SELECT locked_by FROM edit_locks WHERE server_id = ?',
                (server_id,)
            ).fetchone()
            
            if existing_lock and existing_lock['locked_by'] != user_email:
                return False
            
            # ロックを取得
            conn.execute('''
                INSERT OR REPLACE INTO edit_locks (server_id, locked_by, locked_at)
                VALUES (?, ?, ?)
            ''', (server_id, user_email, datetime.now()))
            conn.commit()
            return True
    
    @staticmethod
    def release_lock(server_id: int, user_email: str):
        """サーバ編集ロックの解除"""
        with get_db_connection() as conn:
            conn.execute('''
                DELETE FROM edit_locks 
                WHERE server_id = ? AND locked_by = ?
            ''', (server_id, user_email))
            conn.commit()
    
    @staticmethod
    def get_lock_info(server_id: int) -> Optional[Dict[str, Any]]:
        """ロック情報の取得"""
        with get_db_connection() as conn:
            lock = conn.execute('''
                SELECT el.locked_by, el.locked_at, u.name
                FROM edit_locks el
                LEFT JOIN users u ON el.locked_by = u.email
                WHERE el.server_id = ? AND el.locked_at > datetime('now', '-{} minutes')
            '''.format(LOCK_TIMEOUT_MINUTES), (server_id,)).fetchone()
            
            if lock:
                return {
                    'locked_by': lock['locked_by'],
                    'locked_at': lock['locked_at'],
                    'user_name': lock['name'] or lock['locked_by']
                }
            return None
    
    @staticmethod
    def is_locked_by_others(server_id: int, user_email: str) -> bool:
        """他のユーザーによってロックされているかチェック"""
        lock_info = LockManager.get_lock_info(server_id)
        return lock_info is not None and lock_info['locked_by'] != user_email
