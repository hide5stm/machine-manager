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
