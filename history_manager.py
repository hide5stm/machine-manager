"""
履歴管理モジュール
"""
import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any

from config import FIELD_MAPPING
from database import get_db_connection


class HistoryManager:
    """編集履歴を管理するクラス"""

    @staticmethod
    def add_history_record(server_id: int, action: str, field_name: str = None,
                          old_value: str = None, new_value: str = None):
        """編集履歴の追加"""
        with get_db_connection() as conn:
            conn.execute('''
                INSERT INTO edit_history (server_id, action, field_name, old_value, new_value, changed_by)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (server_id, action, field_name, old_value, new_value, st.session_state.user_email))
            conn.commit()

    @staticmethod
    def get_server_history(server_id: int = None) -> pd.DataFrame:
        """編集履歴の取得"""
        with get_db_connection() as conn:
            query = '''
                SELECT
                    eh.id,
                    eh.server_id,
                    s.model as server_model,
                    eh.action,
                    eh.field_name,
                    eh.old_value,
                    eh.new_value,
                    u.name as changed_by_name,
                    eh.changed_by,
                    eh.changed_at
                FROM edit_history eh
                LEFT JOIN servers s ON eh.server_id = s.id
                LEFT JOIN users u ON eh.changed_by = u.email
            '''

            params = []
            if server_id:
                query += ' WHERE eh.server_id = ?'
                params.append(server_id)

            query += ' ORDER BY eh.changed_at DESC'

            df = pd.read_sql_query(query, conn, params=params)
            return df

    @staticmethod
    def record_server_creation(server_id: int, model: str):
        """サーバ作成履歴の記録"""
        HistoryManager.add_history_record(
            server_id, 'CREATE', 'server', None, f"サーバ '{model}' を作成"
        )

    @staticmethod
    def record_server_update(server_id: int, old_data: Dict[str, Any], new_data: Dict[str, Any]):
        """サーバ更新履歴の記録"""
        for field, label in FIELD_MAPPING.items():
            if old_data.get(field) != new_data.get(field):
                HistoryManager.add_history_record(
                    server_id, 'UPDATE', label,
                    str(old_data.get(field, '')),
                    str(new_data.get(field, ''))
                )

    @staticmethod
    def record_server_deletion(server_id: int, model: str):
        """サーバ削除履歴の記録"""
        HistoryManager.add_history_record(
            server_id, 'DELETE', 'server', f"サーバ '{model}'", "削除済み"
        )
