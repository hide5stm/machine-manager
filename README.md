# サーバ在庫管理システム

Streamlitベースのサーバ在庫管理システムです。Google OAuth2認証、排他制御、編集履歴機能を備えています。

## 機能

- **サーバ管理**: サーバの追加、編集、削除
- **認証機能**: Google OAuth2認証
- **排他制御**: 複数ユーザーによる同時編集の防止
- **編集履歴**: 全ての変更履歴を記録
- **検索機能**: サーバ情報の検索・フィルタリング
- **データエクスポート**: CSV形式でのデータ出力

## プロジェクト構造

```
server_inventory/
├── main.py                 # メインアプリケーション
├── config.py              # 設定ファイル
├── database.py            # データベース操作
├── auth.py                # 認証管理
├── lock_manager.py        # 排他制御
├── history_manager.py     # 履歴管理
├── server_service.py      # サーバ業務ロジック
├── ui_components.py       # UI共通コンポーネント
├── pages.py               # ページ表示ロジック
├── requirements.txt       # 依存関係
└── README.md             # このファイル
```

## セットアップ

1. **依存関係のインストール**
   ```bash
   pip install -r requirements.txt
   ```

2. **環境変数の設定**
   ```bash
   export GOOGLE_CLIENT_ID="your_google_client_id"
   ```

3. **アプリケーションの起動**
   ```bash
   streamlit run main.py
   ```

## モジュール詳細

### config.py
- アプリケーション全体の設定を管理
- データベースパス、認証設定、フィールドマッピングなど

### database.py
- SQLiteデータベースの初期化と基本操作
- データベース接続の管理
- `DatabaseManager`クラスでCRUD操作を提供

### auth.py
- Google OAuth2認証の管理
- ユーザーセッション管理
- `AuthManager`クラスで認証状態を管理

### lock_manager.py
- 排他制御機能の実装
- サーバ編集時のロック管理
- `LockManager`クラスでロック操作を提供

### history_manager.py
- 編集履歴の記録と取得
- 変更内容の詳細な記録
- `HistoryManager`クラスで履歴操作を提供

### server_service.py
- サーバに関する業務ロジック
- データ操作と履歴記録の連携
- `ServerService`クラスで高レベルな操作を提供

### ui_components.py
- UI共通コンポーネント
- 再利用可能なUI部品
- `UIComponents`クラスで各種UI要素を提供

### pages.py
- 各ページの表示ロジック
- ページ固有の処理を管理
- `PageRenderer`クラスでページ表示を統合

### main.py
- アプリケーションのエントリーポイント
- 全体の流れを制御

## 使用方法

1. **ログイン**: Googleアカウントでログイン（開発環境では簡易ログイン）
2. **サーバ一覧**: 登録されているサーバの確認・検索
3. **サーバ追加**: 新規サーバの登録
4. **サーバ編集**: 既存サーバ情報の更新（排他制御付き）
5. **編集履歴**: 変更履歴の確認
6. **データ管理**: 統計情報の確認、CSVエクスポート

## 注意事項

- 開発環境では簡易ログインを使用していますが、本番環境では適切なGoogle OAuth2フローを実装してください
- データベースファイル（server_inventory.db）は自動的に作成されます
- 排他制御のタイムアウトは30分に設定されています

## 今後の拡張案

- ファイルアップロード機能
- より詳細な権限管理
- 通知機能
- レポート機能の強化
- REST API の提供
