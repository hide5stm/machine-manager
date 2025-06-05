"""
UI共通コンポーネント
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional

from auth import AuthManager
from server_service import ServerService
from history_manager import HistoryManager
from config import WARRANTY_STATUS_OPTIONS


class UIComponents:
    """UI共通コンポーネントクラス"""
    
    @staticmethod
    def render_sidebar() -> str:
        """サイドバーの表示"""
        with st.sidebar:
            st.markdown(f"### 👤 ログイン中")
            st.write(f"**{st.session_state.user_name}**")
            st.write(f"{st.session_state.user_email}")
            
            if st.button("ログアウト", use_container_width=True):
                AuthManager.logout_user()
                st.rerun()
            
            st.markdown("---")
            
            # ナビゲーション
            page = st.radio(
                "ページ選択",
                ["サーバ一覧", "サーバ追加", "編集履歴", "データ管理"],
                key="navigation"
            )
            
            return page
    
    @staticmethod
    def render_login_form():
        """ログインフォームの表示"""
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
                        AuthManager.login_user(user_info)
                        st.rerun()
                    else:
                        st.error("メールアドレスと表示名を入力してください。")
            
            st.markdown("---")
            st.markdown("💡 **本番環境では**、適切なGoogle OAuth2認証を実装してください。")
    
    @staticmethod
    def render_server_card(server: pd.Series, server_service: ServerService):
        """サーバカードの表示"""
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
                lock_info = server_service.get_lock_info(server['id'])
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
                    if server_service.delete_server(server['id'], st.session_state.user_email):
                        st.success("サーバを削除しました。")
                        st.rerun()
                    else:
                        st.error("他のユーザーが編集中のため削除できません。")
        
        st.markdown("---")
    
    @staticmethod
    def render_server_form(server_service: ServerService, edit_mode: bool = False, server_data: Dict[str, Any] = None):
        """サーバフォームの表示"""
        if edit_mode and server_data:
            st.title("✏️ サーバ編集")
            server_id = st.session_state.edit_server_id
            
            # ロック取得
            if not server_service.acquire_edit_lock(server_id, st.session_state.user_email):
                lock_info = server_service.get_lock_info(server_id)
                st.error(f"このサーバは {lock_info['user_name']} が編集中です。")
                if st.button("一覧に戻る"):
                    del st.session_state.edit_server_id
                    st.session_state.navigation = "サーバ一覧"
                    st.rerun()
                return
        else:
            st.title("➕ サーバ追加")
            server_data = server_data or {}
        
        # フォーム
        with st.form("server_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                model = st.text_input(
                    "型番 *",
                    value=server_data.get('model', ''),
                    help="必須項目"
                )
                location = st.text_input(
                    "設置場所 *",
                    value=server_data.get('location', ''),
                    help="必須項目"
                )
                purchase_date = st.date_input(
                    "購入日",
                    value=datetime.strptime(server_data['purchase_date'], '%Y-%m-%d').date() 
                    if server_data.get('purchase_date') else None
                )
                warranty_status = st.selectbox(
                    "保守契約状態",
                    WARRANTY_STATUS_OPTIONS,
                    index=WARRANTY_STATUS_OPTIONS.index(server_data.get('warranty_status', '有効')) 
                    if server_data.get('warranty_status') in WARRANTY_STATUS_OPTIONS else 0
                )
            
            with col2:
                ip_address = st.text_input(
                    "IPアドレス",
                    value=server_data.get('ip_address', ''),
                    help="例: 192.168.1.100"
                )
                user_name = st.text_input(
                    "利用者名",
                    value=server_data.get('user_name', '')
                )
                os = st.text_input(
                    "OS",
                    value=server_data.get('os', ''),
                    help="例: Ubuntu 22.04, Windows Server 2022"
                )
                gpu_accessories = st.text_input(
                    "GPU・付属品",
                    value=server_data.get('gpu_accessories', ''),
                    help="例: NVIDIA RTX 4090, 追加メモリ32GB"
                )
            
            notes = st.text_area(
                "備考",
                value=server_data.get('notes', ''),
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
                        server_service.release_edit_lock(server_id, st.session_state.user_email)
                        del st.session_state.edit_server_id
                        st.session_state.navigation = "サーバ一覧"
                        st.rerun()
        
        return submitted, {
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
    
    @staticmethod
    def render_history_record(record: pd.Series):
        """履歴レコードの表示"""
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
    
    @staticmethod
    def render_statistics(stats: Dict[str, int]):
        """統計情報の表示"""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("登録サーバ数", stats['servers'])
        with col2:
            st.metric("編集履歴数", stats['history'])
        with col3:
            st.metric("利用ユーザー数", stats['users'])
    
    @staticmethod
    def create_csv_download_button(df: pd.DataFrame, filename_prefix: str, label: str):
        """CSV ダウンロードボタンの作成"""
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        return st.download_button(
            label=label,
            data=csv,
            file_name=f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
