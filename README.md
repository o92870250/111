# LINE 私人 AI 管家（Gemini 免費版 / FastAPI / Python）

這是一個可直接部署的最小範例：
- 接收 LINE Webhook
- 驗證 `X-Line-Signature`
- 將文字訊息送到 Gemini API
- 回覆到 LINE 聊天室
- 使用 SQLite 保存每位使用者最近對話記憶

## 1. 你要準備的東西

1. LINE Developers 的：
   - `Channel secret`
   - `Channel access token`
2. Google AI Studio 的 API key

## 2. 環境變數

把 `.env.example` 複製成 `.env`，然後填入：

```env
LINE_CHANNEL_SECRET=你的_LINE_CHANNEL_SECRET
LINE_CHANNEL_ACCESS_TOKEN=你的_LINE_CHANNEL_ACCESS_TOKEN
GEMINI_API_KEY=你的_Google_AI_Studio_API_KEY
GEMINI_MODEL=gemini-3-flash-preview
```

## 3. 本機執行

```bash
python -m venv .venv
source .venv/bin/activate   # Windows 請改用 .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --host 0.0.0.0 --port 8000
```

啟動後可測試：
- `GET /`
- `GET /healthz`

## 4. 用 ngrok 對外測試

```bash
ngrok http 8000
```

把公開網址填到 LINE Developers Console 的 Webhook URL：

```text
https://你的網域/webhook
```

並啟用 webhook。

## 5. 部署到 Render

本專案已附 `render.yaml`。

步驟：
1. 把專案推到 GitHub
2. 在 Render 建新服務，連到該 repo
3. Render 會讀取 `render.yaml`
4. 在 Render 後台填入：
   - `LINE_CHANNEL_SECRET`
   - `LINE_CHANNEL_ACCESS_TOKEN`
   - `GEMINI_API_KEY`
5. 部署完成後，把 Render 網址設成 LINE Webhook URL

## 6. 指令

- 直接輸入文字：正常聊天
- `/help`：顯示說明
- `/reset`：清除該使用者最近對話記憶

## 7. 你最需要改的地方

如果你是從 OpenAI 版改過來，請確認：
- Render 裡面已經沒有舊的 `OPENAI_API_KEY`
- 新增的是 `GEMINI_API_KEY`
- 模型名稱是 `gemini-3-flash-preview`

## 8. 常見錯誤

### `Invalid signature`
通常是：
- `LINE_CHANNEL_SECRET` 錯了
- 你在驗簽前改動了原始 request body

### `401 Unauthorized`（回 LINE 失敗）
通常是：
- `LINE_CHANNEL_ACCESS_TOKEN` 錯了
- Token 過期或貼錯 channel

### Gemini 回覆失敗
通常是：
- `GEMINI_API_KEY` 錯誤
- 模型名稱不可用
- 你的 Google AI Studio key 沒貼完整

這個版本刻意保持精簡，方便你先部署成功，再逐步加功能。
