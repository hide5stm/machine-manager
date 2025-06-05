"""
認証管理モジュール
"""
import streamlit as st
from typing import Optional, Dict, Any
from datetime import datetime
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from config import GOOGLE_CLIENT_ID
from database import get_db_connection


class AuthManager:
    """認証を管理するクラス"""
    
    @staticmethod
    def verify_google_token(token: str) -> Optional[Dict[str, Any]]:
        """Google ID トークンの検証"""
        try:
            idinfo = id_token.verify_oauth2_token(
                token, google_requests.Request(), GOOGLE_CLIENT_ID
            )
            return idinfo
        except ValueError:
            return None
    
    @staticmethod
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
    
    @staticmethod
    def logout_user():
        """ログアウト処理"""
        for key in ['user_email', 'user_name', 'user_picture']:
            if key in st.session_state:
                del st.session_state[key]
    
    @staticmethod
    def is_authenticated() -> bool:
        """認証状態の確認"""
        return 'user_email' in st.session_state
    
    @staticmethod
    def get_current_user() -> Dict[str, str]:
        """現在のユーザー情報を取得"""
        return {
            'email': st.session_state.get('user_email', ''),
            'name': st.session_state.get('user_name', ''),
            'picture': st.session_state.get('user_picture', '')
        }
