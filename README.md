# jpstock-trend MVP

日本株・米国株の長期トレンドを分析し、
「buy the dip」型のエントリー候補を週次でDiscord通知するMVPです。

## MVP機能

- Yahoo FinanceからOHLCVを取得（無料）
- 日足/週足/月足を使ったルールベース分析
- 分析結果をDBに永続化（PostgreSQL または SQLite）
- Yahoo OHLC生データをDBに永続化（`price_bars`、冪等Upsert）
- Google OAuthログイン（許可メールのみ）
- Web UIで候補銘柄と判定理由を確認
- 任意の日付(as_of_date)で再計算するバックテスト実行
- Discord通知（候補の有無を簡潔に通知）
- 通知の再送抑制（直近2単位）
  - 日足: 2日
  - 週足: 2週
  - 月足: 2か月

## シグナル判定ロジック（初期）

総合スコア100点で判定。`NOTIFY_THRESHOLD` 以上でエントリー候補。

- Trend（40点）
  - 週足/月足で `Close > MA200`
  - 週足/月足で `MA50 > MA200`
  - 週足の高値/安値構造
- Dip（35点）
  - 直近高値から3-15%調整
  - MA20-50付近での下げ止まり
  - RSI反転上昇
- Breakout（25点）
  - 直近高値まで3%以内
  - 5日高値更新
  - 反発時出来高増

## セットアップ

### 1) 環境変数

```bash
cp .env.example .env
```

`ALLOWED_EMAILS` に閲覧許可するGoogleアカウントをカンマ区切りで設定してください。
Google認証をテスト時にスキップしたい場合は、`.env`で以下を設定します。

```env
AUTH_SKIP_ENABLED=true
AUTH_SKIP_EMAIL=dev@example.com
AUTH_SKIP_NAME=Dev User
```

### 2) Dockerで起動

```bash
docker compose up --build
```

- Web UI: http://localhost:8000
- `worker` が毎週日曜 09:00 (JST) に分析を実行
- `worker` が毎日定時にYahooデータをバックグラウンド取込

## ローカル開発

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

別ターミナルでスケジューラ:

```bash
python -m app.scheduler
```

手動コマンド（テスト時）:

```bash
python -m app.cli ingest --as-of-date 2025-12-01
python -m app.cli analyze --as-of-date 2025-12-01
python -m app.cli test-generate --ticker TEST001 --start-date 2025-01-01 --end-date 2025-03-31 --seed 42
python -m app.cli test-delete --ticker TEST001
```

自動テスト:

```bash
pip install pytest
pytest
```

- `tests/test_test_data_service.py` で、synthetic生成/削除の安全性（非TEST保護、TEST限定削除）を検証します。
- GitHub Actions では push / pull_request 時に `pytest` を実行します（`.github/workflows/tests.yml`）。

Yahooレート制限対策（デフォルト値は `.env.example`）:
- `YAHOO_REQUEST_INTERVAL_SECONDS` : ティッカー間の待機秒数
- `YAHOO_MAX_RETRIES` : レート制限時の再試行回数
- `YAHOO_RATE_LIMIT_COOLDOWN_SECONDS` : レート制限時の待機秒数（再試行ごとに増加）

## API（主要）

- `GET /healthz` : ヘルスチェック
- `GET /login` : Google OAuth開始
- `GET /auth/callback` : OAuthコールバック
- `POST /jobs/analyze` : 手動分析実行（ログイン必須）
  - `as_of_date=YYYY-MM-DD` を渡すと指定日時点で再計算（バックテスト用途）
- `POST /jobs/ingest` : YahooデータをDBへ手動取込（ログイン必須）
  - `as_of_date=YYYY-MM-DD` を指定可能
- `POST /jobs/test-data/generate` : テスト用ランダムウォークデータを一括生成（ログイン必須）
  - `ticker`, `start_date`, `end_date` は必須
  - `start_price`, `drift`, `volatility`, `seed` は任意
- `POST /jobs/test-data/delete` : テスト用ティッカーの合成データを削除（ログイン必須）
  - `ticker` 必須

## 監視の最小構成（自宅サーバ向け）

- `/healthz` を Uptime Kuma 等で定期監視
- コンテナログ監視（web/worker）
- 失敗時はworkerログ確認（将来: 失敗時Discordアラート追加）

## 注意点

- Yahoo Financeの取得仕様変更・制限により、失敗する場合があります。
- 本MVPは投資助言を目的としません。最終判断は自己責任で行ってください。
