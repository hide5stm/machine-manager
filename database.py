"""
データベース操作モジュール
"""
import sqlite3
import streamlit as st
from contextlib import contextmanager
from typing import Optional, Dict, Any
import pandas as pd
from datetime import datetime

from config import DATABASE_PATH, LOCK_TIMEOUT_MINUTES


@st.cache_resource
def init_database():
    """データベースの初期化"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)

    # サーバテーブル
    conn.execute('''
        CREATE TABLE IF NOT EXISTS servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model TEXT NOT NULL,
            location TEXT NOT NULL,
            purchase_date DATE,
            warranty_status TEXT,
            ip_address TEXT,
            user_name TEXT,
            os TEXT,
            gpu_accessories TEXT,
            notes TEXT,
            version INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT,
            updated_by TEXT
        )
    ''')

    # 編集履歴テーブル
    conn.execute('''
        CREATE TABLE IF NOT EXISTS edit_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER,
            action TEXT NOT NULL,
            field_name TEXT,
            old_value TEXT,
            new_value TEXT,
            changed_by TEXT,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (server_id) REFERENCES servers (id)
        )
    ''')

    # ユーザーテーブル
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            picture_url TEXT,
            last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    return conn


@contextmanager
def get_db_connection():
    """データベース接続のコンテキストマネージャー"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


class DatabaseManager:
    """データベース操作を管理するクラス"""

    @staticmethod
    def get_servers() -> pd.DataFrame:
        """全サーバ情報の取得"""
        with get_db_connection() as conn:
            df = pd.read_sql_query('''
                SELECT
                    s.*,
                    u_created.name as created_by_name,
                    u_updated.name as updated_by_name
                FROM servers s
                LEFT JOIN users u_created ON s.created_by = u_created.email
                LEFT JOIN users u_updated ON s.updated_by = u_updated.email
                ORDER BY s.id DESC
            ''', conn)
            return df

    @staticmethod
    def get_server_by_id(server_id: int) -> Optional[sqlite3.Row]:
        """特定のサーバ情報を取得"""
        with get_db_connection() as conn:
            return conn.execute('SELECT * FROM servers WHERE id = ?', (server_id,)).fetchone()

    @staticmethod
    def add_server(server_data: Dict[str, Any]) -> int:
        """新規サーバの追加"""
        with get_db_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO servers (
                    model, location, purchase_date, warranty_status,
                    ip_address, user_name, os, gpu_accessories, notes,
                    created_by, updated_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                server_data['model'],
                server_data['location'],
                server_data['purchase_date'],
                server_data['warranty_status'],
                server_data['ip_address'],
                server_data['user_name'],
                server_data['os'],
                server_data['gpu_accessories'],
                server_data['notes'],
                st.session_state.user_email,
                st.session_state.user_email
            ))

            server_id = cursor.lastrowid
            conn.commit()
            return server_id

    @staticmethod
    def update_server(server_id: int, new_data: Dict[str, Any], expected_version: int) -> bool:
        """サーバ情報の更新（楽観的ロック）"""
        with get_db_connection() as conn:
            # バージョンチェックと更新を同時に実行
            cursor = conn.execute('''
                UPDATE servers SET
                    model = ?, location = ?, purchase_date = ?, warranty_status = ?,
                    ip_address = ?, user_name = ?, os = ?, gpu_accessories = ?, notes = ?,
                    version = version + 1,
                    updated_by = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND version = ?
            ''', (
                new_data['model'],
                new_data['location'],
                new_data['purchase_date'],
                new_data['warranty_status'],
                new_data['ip_address'],
                new_data['user_name'],
                new_data['os'],
                new_data['gpu_accessories'],
                new_data['notes'],
                st.session_state.user_email,
                server_id,
                expected_version
            ))

            # 更新された行数をチェック
            if cursor.rowcount == 0:
                # バージョンが一致しない（他のユーザーが先に更新した）
                return False

            conn.commit()
            return True

    @staticmethod
    def delete_server(server_id: int):
        """サーバの削除"""
        with get_db_connection() as conn:
            # サーバ情報取得（履歴用）
            server = conn.execute('SELECT model FROM servers WHERE id = ?', (server_id,)).fetchone()

            # 削除実行
            conn.execute('DELETE FROM servers WHERE id = ?', (server_id,))
            conn.commit()

            return server['model'] if server else None

    @staticmethod
    def get_statistics() -> Dict[str, int]:
        """統計情報の取得"""
        with get_db_connection() as conn:
            server_count = conn.execute('SELECT COUNT(*) as count FROM servers').fetchone()['count']
            history_count = conn.execute('SELECT COUNT(*) as count FROM edit_history').fetchone()['count']
            user_count = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']

            return {
                'servers': server_count,
                'history': history_count,
                'users': user_count
             }
