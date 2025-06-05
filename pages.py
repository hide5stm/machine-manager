"""
ページ表示ロジック
"""
import streamlit as st
import pandas as pd
from datetime import datetime

from server_service import ServerService
from history_manager import HistoryManager
from ui_components import UIComponents


class PageRenderer:
    """ページ表示を管理するクラス"""

    def __init__(self):
        self.server_service = ServerService()
        self.history_manager = HistoryManager()
        self.ui_components = UIComponents()

    def render_server_list(self):
        """サーバ一覧ページ"""
        st.title("📋 サーバ一覧")

        # 検索機能
        search_term = st.text_input("🔍 検索", placeholder="型番、設置場所、利用者名、IPアドレスなど")

        # サーバデータ取得
        df = self.server_service.get_all_servers()

        if df.empty:
            st.info("登録されているサーバはありません。")
            return

        # 検索フィルタ
        df = self.server_service.search_servers(df, search_term)

        if df.empty:
            st.info("検索条件に一致するサーバが見つかりません。")
            return

        # サーバカード表示
        for _, server in df.iterrows():
            self.ui_components.render_server_card(server, self.server_service)

    def render_server_form(self):
        """サーバ追加・編集フォーム"""
        # 編集モードの確認
        edit_mode = 'edit_server_id' in st.session_state
        server_data = None

        if edit_mode:
            server_id = st.session_state.edit_server_id
            server_data = self.server_service.get_server_by_id(server_id)

            if not server_data:
                st.error("サーバが見つかりません。")
                return

        # フォーム表示
        submitted, form_data = self.ui_components.render_server_form(
            self.server_service, edit_mode, server_data
        )

        if submitted:
            # バリデーション
            is_valid, error_message = self.server_service.validate_server_data(form_data)
            if not is_valid:
                st.error(error_message)
                return

            if edit_mode:
                # 更新処理（楽観的ロック）
                server_id = st.session_state.edit_server_id
                success, message = self.server_service.update_server(server_id, server_data, form_data)

                if success:
                    del st.session_state.edit_server_id
                    st.success(message)
                    st.session_state.navigation = "サーバ一覧"
                    st.rerun()
                else:
                    st.error(message)
                    if "先に更新しました" in message:
                        st.info("最新のデータを表示しています。変更内容を確認して再度更新してください。")
                        # 最新データを再取得してフォームを更新
                        st.rerun()
            else:
                # 新規追加処理
                server_id = self.server_service.create_server(form_data)
                st.success(f"サーバ「{form_data['model']}」を追加しました。")
                st.session_state.navigation = "サーバ一覧"
                st.rerun()

    def render_history(self):
        """編集履歴ページ"""
        st.title("📊 編集履歴")

        # フィルタ
        col1, col2 = st.columns([2, 1])

        with col1:
            search_term = st.text_input("🔍 検索", placeholder="サーバ型番、変更者名、フィールド名など")

        with col2:
            # サーバ選択
            servers_df = self.server_service.get_all_servers()
            server_options = ["全て"] + [f"{row['model']} (ID: {row['id']})" for _, row in servers_df.iterrows()]
            selected_server = st.selectbox("サーバ選択", server_options)

        # 履歴データ取得
        server_id = None
        if selected_server != "全て":
            server_id = int(selected_server.split("ID: ")[1].split(")")[0])

        history_df = self.history_manager.get_server_history(server_id)

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
            self.ui_components.render_history_record(record)

    def render_data_management(self):
        """データ管理ページ"""
        st.title("🔧 データ管理")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 📤 エクスポート")

            if st.button("サーバデータをCSV出力", use_container_width=True):
                df = self.server_service.get_all_servers()
                self.ui_components.create_csv_download_button(df, "servers", "ダウンロード")

            if st.button("履歴データをCSV出力", use_container_width=True):
                df = self.history_manager.get_server_history()
                self.ui_components.create_csv_download_button(df, "history", "ダウンロード")

        with col2:
            st.markdown("### 📊 統計情報")
            stats = self.server_service.get_statistics()
            self.ui_components.render_statistics(stats)
