# Streamlit サーバ在庫管理システム
# Google OAuth2認証・排他制御・編集履歴機能付き

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import json
import hashlib
import time
from typing import Optional, Dict, Any
import requests
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import os
from contextlib import contextmanager

# 設定
DATABASE_PATH = "server_inventory.db"
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")  # 環境変数で設定
LOCK_TIMEOUT_MINUTES = 30

# ページ設定
st.set_page_config(
    page_title="サーバ在庫管理システム",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# データベース初期化
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
    
    # ロックテーブル（排他制御用）
    conn.execute('''
        CREATE TABLE IF NOT EXISTS edit_locks (
            server_id INTEGER PRIMARY KEY,
            locked_by TEXT NOT NULL,
            locked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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

# 認証関連
def verify_google_token(token: str) -> Optional[Dict[str, Any]]:
    """Google ID トークンの検証"""
    try:
        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request(), GOOGLE_CLIENT_ID
        )
        return idinfo
    except ValueError:
        return None

def login_user(user_info: Dict[str, Any]):
    """ユーザー情報の登録・更新とセッション設定"""
    with get_db_connection() as conn:
        conn.execute('''
            INSERT OR REPLACE INTO users (email, name, picture_url, last_login)
            VALUES (?, ?, ?, ?)
        ''', (
            user_info['email'],
            user_info['name'],
            user_info.get('picture', ''),
            datetime.now()
        ))
        conn.commit()
    
    st.session_state.user_email = user_info['email']
    st.session_state.user_name = user_info['name']
    st.session_state.user_picture = user_info.get('picture', '')

def logout_user():
    """ログアウト処理"""
    for key in ['user_email', 'user_name', 'user_picture']:
        if key in st.session_state:
            del st.session_state[key]

def is_authenticated() -> bool:
    """認証状態の確認"""
    return 'user_email' in st.session_state

# 排他制御
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

def release_lock(server_id: int, user_email: str):
    """サーバ編集ロックの解除"""
    with get_db_connection() as conn:
        conn.execute('''
            DELETE FROM edit_locks 
            WHERE server_id = ? AND locked_by = ?
        ''', (server_id, user_email))
        conn.commit()

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

# 履歴管理
def add_history_record(server_id: int, action: str, field_name: str = None, 
                      old_value: str = None, new_value: str = None):
    """編集履歴の追加"""
    with get_db_connection() as conn:
        conn.execute('''
            INSERT INTO edit_history (server_id, action, field_name, old_value, new_value, changed_by)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (server_id, action, field_name, old_value, new_value, st.session_state.user_email))
        conn.commit()

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

# サーバデータ操作
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
        
        # 履歴記録
        add_history_record(server_id, 'CREATE', 'server', None, f"サーバ '{server_data['model']}' を作成")
        
        return server_id

def update_server(server_id: int, old_data: Dict[str, Any], new_data: Dict[str, Any]):
    """サーバ情報の更新"""
    with get_db_connection() as conn:
        conn.execute('''
            UPDATE servers SET
                model = ?, location = ?, purchase_date = ?, warranty_status = ?,
                ip_address = ?, user_name = ?, os = ?, gpu_accessories = ?, notes = ?,
                updated_by = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
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
            server_id
        ))
        conn.commit()
        
        # 変更された項目の履歴記録
        field_mapping = {
            'model': '型番',
            'location': '設置場所',
            'purchase_date': '購入日',
            'warranty_status': '保守契約状態',
            'ip_address': 'IPアドレス',
            'user_name': '利用者名',
            'os': 'OS',
            'gpu_accessories': 'GPU・付属品',
            'notes': '備考'
        }
        
        for field, label in field_mapping.items():
            if old_data.get(field) != new_data.get(field):
                add_history_record(
                    server_id, 'UPDATE', label,
                    str(old_data.get(field, '')),
                    str(new_data.get(field, ''))
                )

def delete_server(server_id: int):
    """サーバの削除"""
    with get_db_connection() as conn:
        # サーバ情報取得（履歴用）
        server = conn.execute('SELECT model FROM servers WHERE id = ?', (server_id,)).fetchone()
        
        # 削除実行
        conn.execute('DELETE FROM servers WHERE id = ?', (server_id,))
        conn.execute('DELETE FROM edit_locks WHERE server_id = ?', (server_id,))
        conn.commit()
        
        # 履歴記録
        if server:
            add_history_record(server_id, 'DELETE', 'server', f"サーバ '{server['model']}'", "削除済み")

# UI コンポーネント
def render_login_page():
    """ログインページの表示"""
    st.title("🖥️ サーバ在庫管理システム")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Googleアカウントでログイン")
        st.markdown("このシステムを利用するには、Googleアカウントでのログインが必要です。")
        
        # 簡易的なGoogle認証フォーム（実際の実装では適切なOAuth2フローを使用）
        with st.form("login_form"):
            st.markdown("**開発用ログイン**")
            email = st.text_input("メールアドレス", placeholder="user@example.com")
            name = st.text_input("表示名", placeholder="山田太郎")
            
            if st.form_submit_button("ログイン", use_container_width=True):
                if email and name:
                    # 開発用の簡易ログイン
                    user_info = {
                        'email': email,
                        'name': name,
                        'picture': ''
                    }
                    login_user(user_info)
                    st.rerun()
                else:
                    st.error("メールアドレスと表示名を入力してください。")
        
        st.markdown("---")
        st.markdown("💡 **本番環境では**、適切なGoogle OAuth2認証を実装してください。")

def render_sidebar():
    """サイドバーの表示"""
    with st.sidebar:
        st.markdown(f"### 👤 ログイン中")
        st.write(f"**{st.session_state.user_name}**")
        st.write(f"{st.session_state.user_email}")
        
        if st.button("ログアウト", use_container_width=True):
            logout_user()
            st.rerun()
        
        st.markdown("---")
        
        # ナビゲーション
        page = st.radio(
            "ページ選択",
            ["サーバ一覧", "サーバ追加", "編集履歴", "データ管理"],
            key="navigation"
        )
        
        return page

def render_server_list():
    """サーバ一覧ページ"""
    st.title("📋 サーバ一覧")
    
    # 検索機能
    search_term = st.text_input("🔍 検索", placeholder="型番、設置場所、利用者名、IPアドレスなど")
    
    # サーバデータ取得
    df = get_servers()
    
    if df.empty:
        st.info("登録されているサーバはありません。")
        return
    
    # 検索フィルタ
    if search_term:
        mask = df.astype(str).apply(
            lambda x: x.str.contains(search_term, case=False, na=False)
        ).any(axis=1)
        df = df[mask]
    
    # サーバカード表示
    for _, server in df.iterrows():
        with st.container():
            col1, col2, col3 = st.columns([6, 2, 2])
            
            with col1:
                st.markdown(f"### 🖥️ {server['model']}")
                
                info_cols = st.columns(4)
                with info_cols[0]:
                    st.markdown(f"**設置場所:** {server['location'] or '-'}")
                    st.markdown(f"**利用者:** {server['user_name'] or '-'}")
                with info_cols[1]:
                    st.markdown(f"**IPアドレス:** {server['ip_address'] or '-'}")
                    st.markdown(f"**OS:** {server['os'] or '-'}")
                with info_cols[2]:
                    warranty_color = "🟢" if server['warranty_status'] == "有効" else "🔴"
                    st.markdown(f"**保守契約:** {warranty_color} {server['warranty_status'] or '-'}")
                    st.markdown(f"**GPU・付属品:** {server['gpu_accessories'] or '-'}")
                with info_cols[3]:
                    st.markdown(f"**購入日:** {server['purchase_date'] or '-'}")
                    st.markdown(f"**更新者:** {server['updated_by_name'] or server['updated_by'] or '-'}")
                
                if server['notes']:
                    st.markdown(f"**備考:** {server['notes']}")
            
            with col2:
                # ロック状態確認
                lock_info = get_lock_info(server['id'])
                if lock_info and lock_info['locked_by'] != st.session_state.user_email:
                    st.warning(f"編集中: {lock_info['user_name']}")
                    st.button("編集", disabled=True, key=f"edit_disabled_{server['id']}")
                else:
                    if st.button("✏️ 編集", key=f"edit_{server['id']}", use_container_width=True):
                        st.session_state.edit_server_id = server['id']
                        st.session_state.navigation = "サーバ追加"
                        st.rerun()
            
            with col3:
                if st.button("🗑️ 削除", key=f"delete_{server['id']}", use_container_width=True):
                    if acquire_lock(server['id'], st.session_state.user_email):
                        delete_server(server['id'])
                        release_lock(server['id'], st.session_state.user_email)
                        st.success("サーバを削除しました。")
                        st.rerun()
                    else:
                        st.error("他のユーザーが編集中のため削除できません。")
        
        st.markdown("---")

def render_server_form():
    """サーバ追加・編集フォーム"""
    # 編集モードの確認
    edit_mode = 'edit_server_id' in st.session_state
    
    if edit_mode:
        st.title("✏️ サーバ編集")
        server_id = st.session_state.edit_server_id
        
        # ロック取得
        if not acquire_lock(server_id, st.session_state.user_email):
            lock_info = get_lock_info(server_id)
            st.error(f"このサーバは {lock_info['user_name']} が編集中です。")
            if st.button("一覧に戻る"):
                del st.session_state.edit_server_id
                st.session_state.navigation = "サーバ一覧"
                st.rerun()
            return
        
        # 既存データ取得
        with get_db_connection() as conn:
            server_data = conn.execute('SELECT * FROM servers WHERE id = ?', (server_id,)).fetchone()
        
        if not server_data:
            st.error("サーバが見つかりません。")
            return
    else:
        st.title("➕ サーバ追加")
        server_data = {}
    
    # フォーム
    with st.form("server_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            model = st.text_input(
                "型番 *",
                value=server_data.get('model', '') if edit_mode else '',
                help="必須項目"
            )
            location = st.text_input(
                "設置場所 *",
                value=server_data.get('location', '') if edit_mode else '',
                help="必須項目"
            )
            purchase_date = st.date_input(
                "購入日",
                value=datetime.strptime(server_data['purchase_date'], '%Y-%m-%d').date() 
                if edit_mode and server_data.get('purchase_date') else None
            )
            warranty_status = st.selectbox(
                "保守契約状態",
                ["有効", "期限切れ", "なし"],
                index=["有効", "期限切れ", "なし"].index(server_data.get('warranty_status', '有効')) 
                if edit_mode else 0
            )
        
        with col2:
            ip_address = st.text_input(
                "IPアドレス",
                value=server_data.get('ip_address', '') if edit_mode else '',
                help="例: 192.168.1.100"
            )
            user_name = st.text_input(
                "利用者名",
                value=server_data.get('user_name', '') if edit_mode else ''
            )
            os = st.text_input(
                "OS",
                value=server_data.get('os', '') if edit_mode else '',
                help="例: Ubuntu 22.04, Windows Server 2022"
            )
            gpu_accessories = st.text_input(
                "GPU・付属品",
                value=server_data.get('gpu_accessories', '') if edit_mode else '',
                help="例: NVIDIA RTX 4090, 追加メモリ32GB"
            )
        
        notes = st.text_area(
            "備考",
            value=server_data.get('notes', '') if edit_mode else '',
            help="その他の情報があれば記入してください"
        )
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            submitted = st.form_submit_button(
                "更新" if edit_mode else "追加",
                use_container_width=True
            )
        
        with col2:
            if edit_mode:
                if st.form_submit_button("キャンセル", use_container_width=True):
                    release_lock(server_id, st.session_state.user_email)
                    del st.session_state.edit_server_id
                    st.session_state.navigation = "サーバ一覧"
                    st.rerun()
    
    if submitted:
        if not model or not location:
            st.error("型番と設置場所は必須項目です。")
            return
        
        new_data = {
            'model': model,
            'location': location,
            'purchase_date': purchase_date.strftime('%Y-%m-%d') if purchase_date else '',
            'warranty_status': warranty_status,
            'ip_address': ip_address,
            'user_name': user_name,
            'os': os,
            'gpu_accessories': gpu_accessories,
            'notes': notes
        }
        
        if edit_mode:
            # 更新
            old_data = dict(server_data)
            update_server(server_id, old_data, new_data)
            release_lock(server_id, st.session_state.user_email)
            del st.session_state.edit_server_id
            st.success("サーバ情報を更新しました。")
        else:
            # 新規追加
            server_id = add_server(new_data)
            st.success(f"サーバ「{model}」を追加しました。")
        
        st.session_state.navigation = "サーバ一覧"
        st.rerun()

def render_history():
    """編集履歴ページ"""
    st.title("📊 編集履歴")
    
    # フィルタ
    col1, col2 = st.columns([2, 1])
    
    with col1:
        search_term = st.text_input("🔍 検索", placeholder="サーバ型番、変更者名、フィールド名など")
    
    with col2:
        # サーバ選択
        servers_df = get_servers()
        server_options = ["全て"] + [f"{row['model']} (ID: {row['id']})" for _, row in servers_df.iterrows()]
        selected_server = st.selectbox("サーバ選択", server_options)
    
    # 履歴データ取得
    server_id = None
    if selected_server != "全て":
        server_id = int(selected_server.split("ID: ")[1].split(")")[0])
    
    history_df = get_server_history(server_id)
    
    if history_df.empty:
        st.info("履歴がありません。")
        return
    
    # 検索フィルタ
    if search_term:
        mask = history_df.astype(str).apply(
            lambda x: x.str.contains(search_term, case=False, na=False)
        ).any(axis=1)
        history_df = history_df[mask]
    
    # 履歴表示
    st.markdown(f"**{len(history_df)}件の履歴**")
    
    for _, record in history_df.iterrows():
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 1, 2, 2])
            
            with col1:
                st.markdown(f"**{record['server_model']}** (ID: {record['server_id']})")
            
            with col2:
                action_icon = {"CREATE": "➕", "UPDATE": "✏️", "DELETE": "🗑️"}.get(record['action'], "📝")
                st.markdown(f"{action_icon} {record['action']}")
            
            with col3:
                if record['field_name'] and record['action'] == 'UPDATE':
                    st.markdown(f"**{record['field_name']}**")
                    st.markdown(f"🔄 `{record['old_value']}` → `{record['new_value']}`")
                else:
                    st.markdown(record['new_value'] or record['old_value'] or '')
            
            with col4:
                st.markdown(f"👤 {record['changed_by_name'] or record['changed_by']}")
                st.markdown(f"🕒 {record['changed_at']}")
        
        st.markdown("---")

def render_data_management():
    """データ管理ページ"""
    st.title("🔧 データ管理")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📤 エクスポート")
        
        if st.button("サーバデータをCSV出力", use_container_width=True):
            df = get_servers()
            csv = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="ダウンロード",
                data=csv,
                file_name=f"servers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        if st.button("履歴データをCSV出力", use_container_width=True):
            df = get_server_history()
            csv = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="ダウンロード",
                data=csv,
                file_name=f"history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    with col2:
        st.markdown("### 📊 統計情報")
        
        with get_db_connection() as conn:
            server_count = conn.execute('SELECT COUNT(*) as count FROM servers').fetchone()['count']
            history_count = conn.execute('SELECT COUNT(*) as count FROM edit_history').fetchone()['count']
            user_count = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']
        
        st.metric("登録サーバ数", server_count)
        st.metric("編集履歴数", history_count)
        st.metric("利用ユーザー数", user_count)

def main():
    """メイン関数"""
    # データベース初期化
    init_database()
    
    # 認証チェック
    if not is_authenticated():
        render_login_page()
        return
    
    # メインUI
    page = render_sidebar()
    
    if page == "サーバ一覧":
        render_server_list()
    elif page == "サーバ追加":
        render_server_form()
    elif page == "編集履歴":
        render_history()
    elif page == "データ管理":
        render_data_management()

if __name__ == "__main__":
    main()
