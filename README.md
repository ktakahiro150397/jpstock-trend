# jpstock-trend MVP

日本株・米国株の長期トレンドを分析し、
「buy the dip」型のエントリー候補を週次でDiscord通知するMVPです。

## MVP機能

- Yahoo FinanceからOHLCVを取得（無料）
- 日足/週足/月足を使ったルールベース分析
- 分析結果をDBに永続化（PostgreSQL または SQLite）
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

### 2) Dockerで起動

```bash
docker compose up --build
```

- Web UI: http://localhost:8000
- `worker` が毎週日曜 09:00 (JST) に分析を実行

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

## API（主要）

- `GET /healthz` : ヘルスチェック
- `GET /login` : Google OAuth開始
- `GET /auth/callback` : OAuthコールバック
- `POST /jobs/analyze` : 手動分析実行（ログイン必須）
  - `as_of_date=YYYY-MM-DD` を渡すと指定日時点で再計算（バックテスト用途）

## 監視の最小構成（自宅サーバ向け）

- `/healthz` を Uptime Kuma 等で定期監視
- コンテナログ監視（web/worker）
- 失敗時はworkerログ確認（将来: 失敗時Discordアラート追加）

## 注意点

- Yahoo Financeの取得仕様変更・制限により、失敗する場合があります。
- 本MVPは投資助言を目的としません。最終判断は自己責任で行ってください。
