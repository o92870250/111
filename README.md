# LINE 私人 AI 管家（FastAPI / Python）

這是一個可直接部署的最小範例：
- 接收 LINE Webhook
- 驗證 `X-Line-Signature`
- 將文字訊息送到 OpenAI Responses API
- 回覆到 LINE 聊天室
- 使用 SQLite 保存每位使用者最近對話記憶

## 1. 建立 LINE Messaging API Channel

到 LINE Developers 建立：
1. Provider
2. Messaging API channel
3. 取得：
   - `Channel secret`
   - `Channel access token`

官方文件：
- Messaging API 概覽：<https://developers.line.biz/en/services/messaging-api/>
- 接收 webhook 與驗簽：<https://developers.line.biz/en/docs/messaging-api/receiving-messages/>
- Reply message：<https://developers.line.biz/en/docs/messaging-api/sending-messages/>

## 2. 準備 OpenAI API Key

建立 OpenAI API key，填入環境變數 `OPENAI_API_KEY`。
本專案呼叫的是 OpenAI 的 Responses API。
官方參考：<https://platform.openai.com/docs/api-reference/responses>

## 3. 本機執行

```bash
python -m venv .venv
source .venv/bin/activate   # Windows 請改用 .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python main.py
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
   - `OPENAI_API_KEY`
5. 部署完成後，把 Render 網址設成 LINE Webhook URL

## 6. 指令

- 直接輸入文字：正常聊天
- `/help`：顯示說明
- `/reset`：清除該使用者最近對話記憶

## 7. 專案結構

```text
.
├── main.py
├── requirements.txt
├── .env.example
├── render.yaml
└── README.md
```

## 8. 安全與實務建議

### 不要忽略 webhook 驗簽
LINE 官方建議在收到 webhook 時，驗證 `X-Line-Signature`，確認請求未被竄改。

### 不要把長期記憶直接塞在 prompt
現在範例只存近期對話。真正要做私人 AI 管家，建議把：
- 待辦
- 提醒
- 客製偏好
- 家庭資訊
- 工作專案資訊

拆成獨立資料表或外部資料庫，不要全丟在對話歷史裡。

### 加上白名單或使用者綁定
若這是你的私人管家，建議至少加：
- 僅允許特定 LINE userId
- 帳號綁定
- 管理員模式

### 回覆時間
LINE reply token 有效期有限，若未來流程會變長，建議：
- webhook 先快速回 200
- 背景工作處理
- 再改用 push message 回覆

## 9. 下一步建議

你可以在這份最小範例上再加：
- Google Calendar 行程查詢
- Gmail 摘要
- Notion / Google Sheets 記帳
- 定時提醒
- 圖文選單（Rich Menu）
- Flex Message 卡片介面

## 10. 常見錯誤

### `Invalid signature`
通常是：
- `LINE_CHANNEL_SECRET` 錯了
- 你在驗簽前改動了原始 request body

### `401 Unauthorized`（回 LINE 失敗）
通常是：
- `LINE_CHANNEL_ACCESS_TOKEN` 錯了
- Token 過期或貼錯 channel

### OpenAI 回覆失敗
通常是：
- `OPENAI_API_KEY` 錯誤
- 模型名稱不可用
- 帳戶配額或權限問題

---

這個範例刻意保持精簡，方便你先部署成功，再逐步加功能。
