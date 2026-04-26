# Hermes Agent向けコンテナ環境構築ガイド

このドキュメントは、PoCで必要なアプリ（`web` / `worker` / `db`）をまとめて起動しつつ、
Hermes Agentの実行権限をコンテナ内と許可ディレクトリへ限定するための手順です。

## 1. 事前準備

```bash
cp .env.example .env
mkdir -p .hermes/data/postgres .hermes/workspace
```

## 2. 起動方法

```bash
docker compose -f docker-compose.hermes.yml up --build
```

起動対象:
- `web`: FastAPI UI / API
- `worker`: 定期ジョブ（取り込み・分析）
- `db`: PostgreSQL


## 2-b. Docker導入とビルド確認

Ubuntu環境の例:

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2
```

ビルド確認:

```bash
docker version
docker compose version
docker compose -f docker-compose.hermes.yml build web worker
```

`docker compose ... build` が成功すれば、Hermes向けイメージのビルド確認は完了です。

## 3. 権限制限の方針

`docker-compose.hermes.yml` では、以下を適用しています。

- `read_only: true` によりコンテナのルートファイルシステムを読み取り専用化
- `cap_drop: [ALL]` でLinux Capabilityを全削除
- `security_opt: [no-new-privileges:true]` で権限昇格を禁止
- 書き込み可能先を `/.hermes/data` と `/.hermes/workspace` のマウント先に限定
- `/tmp` は `tmpfs` で一時領域のみ許可

## 4. 許可ディレクトリ

Hermes運用時に書き込み可能なディレクトリは次です。

- `./.hermes/data` → コンテナ内 `/data`
- `./.hermes/workspace` → コンテナ内 `/workspace`

アプリコード (`./app`) と `.env` は read-only マウントです。

## 5. 設定項目一覧

`docker-compose.hermes.yml` で利用する主な設定:

| 項目 | 既定値 | 用途 |
|---|---|---|
| `DATABASE_URL` | `sqlite:////data/app.db` | DB接続先。未指定時は許可ディレクトリ上のSQLiteを利用 |
| `POSTGRES_USER` | `app` | PostgreSQLユーザー |
| `POSTGRES_PASSWORD` | `app` | PostgreSQLパスワード |
| `POSTGRES_DB` | `jpstock` | PostgreSQLデータベース名 |
| `ports (web)` | `8000:8000` | Web UI/API公開ポート |
| `ports (db)` | `5432:5432` | DB公開ポート（必要に応じて閉塞可能） |

その他、アプリ固有設定は `.env.example` を参照してください。

## 6. 運用メモ

- PostgreSQLを使う場合は `.env` の `DATABASE_URL` をPostgreSQL DSNに設定
- 最小権限を優先し、追加マウントは必要最小限に限定
- 監査しやすいよう、Hermes専用設定は `docker-compose.hermes.yml` に集約
