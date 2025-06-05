"""
メインアプリケーション
"""
import streamlit as st

from config import PAGE_CONFIG
from database import init_database
from auth import AuthManager
from ui_components import UIComponents
from pages import PageRenderer


def main():
    """メイン関数"""
    # ページ設定
    st.set_page_config(**PAGE_CONFIG)
    
    # データベース初期化
    init_database()
    
    # 認証チェック
    if not AuthManager.is_authenticated():
        UIComponents.render_login_form()
        return
    
    # ページレンダラー初期化
    page_renderer = PageRenderer()
    ui_components = UIComponents()
    
    # サイドバー表示
    page = ui_components.render_sidebar()
    
    # ページ表示
    if page == "サーバ一覧":
        page_renderer.render_server_list()
    elif page == "サーバ追加":
        page_renderer.render_server_form()
    elif page == "編集履歴":
        page_renderer.render_history()
    elif page == "データ管理":
        page_renderer.render_data_management()


if __name__ == "__main__":
    main()
