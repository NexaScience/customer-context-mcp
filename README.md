# 商談準備MCP

営業 / CS チームが顧客との商談を準備するための、**MCP サーバー**兼 **iframe MCP App** です。
**Notion**・**Slack**・**Google Drive** から顧客に関するコンテキストを収集し、LLM で分析して、
証跡（エビデンス）付きの顧客ブリーフを iframe UI に描画します。


## プロジェクト構成

```
customer-context-mcp/
├── server/                          Python MCP サーバー + HTTP ブリッジ
│   ├── pyproject.toml
│   └── customer_context_mcp/
│       ├── server.py                MCP stdio サーバー
│       ├── api/app.py               FastAPI ブリッジ（iframe + ツールを配信）
│       ├── cli.py                   `customer-context-mcp {mcp,http}`
│       ├── tools/                   search / brief / ask / evidence / draft
│       ├── sources/                 Notion, Slack, Google Drive
│       └── llm.py                   Anthropic ベースの分析
├── app/                             iframe MCP App (Vite + React + Tailwind)
│   └── src/
│       ├── App.tsx
│       └── components/              Header / Risks / EvidenceDrawer / …
├── .env.example
└── customer_context_mcp_meeting_prep_requirements.md
```

## MCP ツール

| ツール | 役割 |
|---|---|
| `search_customer_context` | Notion + Slack + Google Drive を検索し、Evidence[] を返す |
| `generate_meeting_brief`  | 検索を実行し、LLM で商談ブリーフを構造化。JSON **と** MCP App（後述）を返す |
| `ask_meeting_brief`       | エビデンスに基づくフォローアップ Q&A |
| `get_evidence_detail`     | id を指定して 1 件の Evidence レコードを返す |
| `draft_customer_message`  | フォローアップメール / 社内 Slack 要約 / アジェンダを下書き |

## MCP Apps（インライン iframe）

`generate_meeting_brief` は **3 つ**のペイロードを返し、主要な MCP App 仕様の双方で同じブリーフを描画します。

| ペイロード | 利用するホスト | 形式 |
|---|---|---|
| `structured_content` | **ChatGPT Apps** — 実行時に `ui/notifications/tool-result` の postMessage で登録済み widget の iframe に届けられる | ブリーフ JSON |
| `content[0]`（`TextContent`） | プレーンな MCP クライアント（UI 描画なし） | ブリーフ JSON をテキストで |
| `content[1]`（`UIResource`） | インライン `ui://` リソースを描画する **mcp-ui 対応ホスト** | 自己完結した HTML ダッシュボード |


## セットアップ

### 1. 認証情報

```bash
cp .env.example .env
# GEMINI_API_KEY, NOTION_TOKEN, SLACK_BOT_TOKEN を記入
# Google Drive の OAuth クライアントを ./credentials.json に配置
```

必要なスコープ：

- **Notion**: インテグレーションを発行し、**対象ページ/データベースに共有**してください（••• → 接続/Connections から追加）。
  - インテグレーションに共有された**データベースは自動検出**され、`databases.query` で走査します。**タイトル＋全プロパティ**で顧客名を照合し、**各行の本文も取り込み**ます（環境変数の設定は不要）。
  - データベースに属さない通常ページは、既定の検索 API（**ページタイトル**のみにマッチ／本文は対象外）でフォールバック検索します。
- **Slack**: **ボットトークン（`xoxb-`）** を使用します（`SLACK_BOT_TOKEN`）。Bot がメンバーになっているチャンネルの履歴を走査して顧客名で絞り込むため、`channels:read` / `groups:read`（チャンネル一覧）と `channels:history` / `groups:history`（メッセージ読み取り）のスコープを付与し、対象チャンネルに Bot を招待してください（`/invite @your-bot`）。
- **Google Drive**: *デスクトップアプリ*タイプの OAuth 2.0 クライアント。初回実行時にブラウザで同意し、`token.json` が書き出されます。

### 2. サーバー

Python の依存関係は [uv](https://docs.astral.sh/uv/) で管理し、`server/uv.lock` に固定しています。
未インストールなら `curl -LsSf https://astral.sh/uv/install.sh | sh` で一度だけ導入してください。

```bash
cd server
uv sync            # .venv を作成し uv.lock からインストール
```

以降のコマンドは `uv run` を使うとプロジェクトの venv が自動で使われます。

```bash
uv run customer-context-mcp --help
```

venv を直接有効化したい場合は `source .venv/bin/activate`。

### 3. App（iframe）

```bash
cd app
npm install
npm run build           # app/dist に出力（HTTP ブリッジが配信）
```

## 起動

### HTTP ブリッジ（MCPJam / ブラウザ用）

```bash
cd server
uv run customer-context-mcp http --host 127.0.0.1 --port 8787   # → http://127.0.0.1:8787
# Doppler: doppler run -- uv run customer-context-mcp http --host 127.0.0.1 --port 8787
```

アプリの HMR 開発時は別ターミナルで `cd app && npm run dev`（:5173、`/api` を :8787 にプロキシ）。

### MCP Jam で widget を確認

ブラウザ上で MCP ツールと iframe MCP App を試せる [MCP Jam Inspector](https://github.com/mcpjam/inspector) を使う手順です。

```bash
# 1. HTTP ブリッジを起動（ターミナル①）
cd server
uv run customer-context-mcp http --host 127.0.0.1 --port 8787   # → http://127.0.0.1:8787

# 2. MCP Jam Inspector を起動（ターミナル②）
npx @mcpjam/inspector@latest                                    # → ブラウザが自動で開く（http://127.0.0.1:6274）
```

> ローカル接続は npx / デスクトップ版のみ対応（Web 版は不可）。

3. Inspector で **Add Server** → **HTTP** → URL に `http://127.0.0.1:8787/mcp/` を入力（**末尾スラッシュ必須**）
4. **Playground / App Builder** で `generate_meeting_brief` を実行（*Tools* ページでは widget が描画されない）

**補足**

- 2 カラム表示にするにはデバイスを **Desktop** に設定する。
- App の UI を編集しながら確認する場合は、別ターミナルで `cd app && npm run dev`（:5173、`/api` を :8787 にプロキシ）。
- 実データ取得と **Ask** には `GEMINI_API_KEY` が必要。Slack 検索には `xoxb-` のボットトークン（`SLACK_BOT_TOKEN`）が必要で、Bot を対象チャンネルに招待しておく必要があります。

### MCP stdio サーバー（Claude Desktop / Claude Code）

```jsonc
// ~/.config/claude/claude_desktop_config.json または settings.json
{
  "mcpServers": {
    "customer-context": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/customer-context-mcp/server",
        "run",
        "customer-context-mcp",
        "mcp"
      ]
    }
  }
}
```

## デモ用プロンプト

```text
A社との明日の商談に向けて、Notion、Slack、Google Driveの情報をもとに、
状況・懸念点・確認すべき質問・提案すべき内容を整理してください。
```

MCP ホストは `generate_meeting_brief({customer_name: "A社", ...})` を呼び出せます。同じデータが、上記 URL の
iframe MCP App ダッシュボードにも描画されます。
