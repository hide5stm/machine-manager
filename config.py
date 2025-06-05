"""
アプリケーション設定
"""
import os

# データベース設定
DATABASE_PATH = "server_inventory.db"

# 認証設定
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

# 排他制御設定
LOCK_TIMEOUT_MINUTES = 30

# ページ設定
PAGE_CONFIG = {
    "page_title": "サーバ在庫管理システム",
    "page_icon": "🖥️",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# フィールドマッピング
FIELD_MAPPING = {
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

# 選択肢
WARRANTY_STATUS_OPTIONS = ["有効", "期限切れ", "なし"]
