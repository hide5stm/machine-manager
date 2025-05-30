# Ubuntu 24.04 でのセットアップ手順

## 1. requirements.txt
streamlit>=1.28.0
pandas>=2.0.0
google-auth>=2.17.0
google-auth-oauthlib>=1.0.0
google-auth-httplib2>=0.1.0
requests>=2.28.0

## 2. セットアップスクリプト (setup.sh)
#!/bin/bash

# Python環境のセットアップ
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nginx

# プロジェクトディレクトリ作成
mkdir -p /opt/server-inventory
cd /opt/server-inventory

# 仮想環境作成
python3 -m venv venv
source venv/bin/activate

# 依存関係インストール
pip install -r requirements.txt

# データベースディレクトリ作成
mkdir -p data
chmod 755 data

echo "セットアップ完了!"

## 3. systemdサービス設定 (server-inventory.service)
[Unit]
Description=Server Inventory Management System
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/server-inventory
Environment=PATH=/opt/server-inventory/venv/bin
Environment=GOOGLE_CLIENT_ID=your_google_client_id_here
ExecStart=/opt/server-inventory/venv/bin/streamlit run app.py --server.port=8501 --server.address=127.0.0.1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target

## 4. Nginx設定 (nginx.conf)
server {
    listen 80;
    server_name your-domain.com;  # 実際のドメインに変更
    
    # HTTPSリダイレクト (SSL設定後に有効化)
    # return 301 https://$server_name$request_uri;
    
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}

# HTTPS設定 (Let's Encrypt使用)
# server {
#     listen 443 ssl http2;
#     server_name your-domain.com;
#     
#     ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
#     ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
#     
#     location / {
#         proxy_pass http://127.0.0.1:8501;
#         proxy_http_version 1.1;
#         proxy_set_header Upgrade $http_upgrade;
#         proxy_set_header Connection "upgrade";
#         proxy_set_header Host $host;
#         proxy_set_header X-Real-IP $remote_addr;
#         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
#         proxy_set_header X-Forwarded-Proto $scheme;
#         proxy_cache_bypass $http_upgrade;
#     }
# }

## 5. Google OAuth2設定手順

### 5.1 Google Cloud Console設定
1. https://console.cloud.google.com/ にアクセス
2. 新しいプロジェクトを作成または既存プロジェクトを選択
3. 「APIとサービス」→「認証情報」
4. 「認証情報を作成」→「OAuth 2.0 クライアントID」
5. アプリケーションの種類：「ウェブアプリケーション」
6. 承認済みリダイレクトURI: https://your-domain.com
7. クライアントIDをコピー

### 5.2 環境変数設定
echo 'export GOOGLE_CLIENT_ID="your_client_id_here"' >> /etc/environment
source /etc/environment

## 6. デプロイスクリプト (deploy.sh)
#!/bin/bash

set -e

# プロジェクトディレクトリに移動
cd /opt/server-inventory

# Gitから最新版取得 (任意)
# git pull origin main

# 仮想環境アクティベート
source venv/bin/activate

# 依存関係更新
pip install -r requirements.txt

# サービス再起動
sudo systemctl restart server-inventory
sudo systemctl reload nginx

echo "デプロイ完了!"

## 7. バックアップスクリプト (backup.sh)
#!/bin/bash

BACKUP_DIR="/var/backups/server-inventory"
DATE=$(date +%Y%m%d_%H%M%S)

# バックアップディレクトリ作成
mkdir -p $BACKUP_DIR

# データベースバックアップ
cp /opt/server-inventory/server_inventory.db $BACKUP_DIR/server_inventory_$DATE.db

# 30日以上古いバックアップを削除
find $BACKUP_DIR -name "server_inventory_*.db" -mtime +30 -delete

echo "バックアップ完了: $BACKUP_DIR/server_inventory_$DATE.db"

## 8. 完全セットアップコマンド
# 以下のコマンドを順番に実行してください

# 1. ファイル配置
sudo mkdir -p /opt/server-inventory
cd /opt/server-inventory

# app.py, requirements.txt をここに配置

# 2. セットアップ実行
chmod +x setup.sh
sudo ./setup.sh

# 3. サービス設定
sudo cp server-inventory.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable server-inventory

# 4. Nginx設定
sudo cp nginx.conf /etc/nginx/sites-available/server-inventory
sudo ln -s /etc/nginx/sites-available/server-inventory /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# 5. 環境変数設定 (Google Client IDを設定)
sudo nano /etc/environment
# GOOGLE_CLIENT_ID="your_actual_client_id" を追加

# 6. サービス開始
sudo systemctl start server-inventory
sudo systemctl status server-inventory

# 7. バックアップスクリプト設定
sudo cp backup.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/backup.sh

# 8. 日次バックアップcron設定
echo "0 2 * * * /usr/local/bin/backup.sh" | sudo crontab -

## 9. SSL/HTTPS設定 (Let's Encrypt)
# Certbotインストール
sudo apt install certbot python3-certbot-nginx

# SSL証明書取得
sudo certbot --nginx -d your-domain.com

# 自動更新設定
sudo crontab -e
# 以下を追加: 0 12 * * * /usr/bin/certbot renew --quiet

## 10. ファイアウォール設定
sudo ufw allow 'Nginx Full'
sudo ufw allow ssh
sudo ufw enable

## 11. 監視・ログ設定
# ログローテーション
sudo nano /etc/logrotate.d/server-inventory

# /opt/server-inventory/logs/*.log {
#     daily
#     missingok
#     rotate 52
#     compress
#     delaycompress
#     notifempty
#     copytruncate
# }

## 12. トラブルシューティング

### サービス状態確認
sudo systemctl status server-inventory
sudo journalctl -u server-inventory -f

### Nginx設定確認
sudo nginx -t
sudo systemctl status nginx

### ポート確認
sudo netstat -tlnp | grep :8501
sudo netstat -tlnp | grep :80

### ログ確認
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

### データベース確認
sqlite3 /opt/server-inventory/server_inventory.db ".tables"

## 13. セキュリティ推奨事項

1. 定期的なシステム更新
   sudo apt update && sudo apt upgrade

2. ファイル権限設定
   sudo chown -R www-data:www-data /opt/server-inventory
   sudo chmod 644 /opt/server-inventory/server_inventory.db

3. バックアップの暗号化
   gpg --symmetric /var/backups/server-inventory/server_inventory_*.db

4. ログ監視
   fail2ban でアクセス制限

5. データベース暗号化 (オプション)
   SQLCipher の使用を検討

## 14. パフォーマンス最適化

1. Nginx設定
   gzip圧縮、キャッシュ設定

2. Streamlit設定
   --server.maxUploadSize=200
   --server.maxMessageSize=200

3. データベース最適化
   定期的なVACUUM実行

## 15. 運用手順

### 日次作業
- バックアップ確認
- ログ確認
- サービス状態確認

### 週次作業
- システム更新確認
- ディスク使用量確認

### 月次作業
- SSL証明書期限確認
- バックアップ復元テスト
