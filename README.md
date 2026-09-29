# 小巷咖啡：LINE 點餐小幫手 Demo

一個用 Python（Flask + LINE Messaging API SDK v3）寫的 LINE 聊天機器人，用來示範 Juxta 如何處理聊天機器人專案：在 issue 裡用中文提出需求，Juxta 的 worker 修改機器人並補上測試，審查與簽核通過後合併。

- 線上試用（不需要 LINE 帳號）：https://devilbilly.github.io/LineBotDemo/

## 機器人會做什麼

| 使用者輸入 | 回覆 |
|---|---|
| 菜單 | 列出品項與價格 |
| 營業時間 | 每天 08:00–18:00 |
| 推薦 | 今日推薦：摩卡，搭配重乳酪蛋糕只要 NT$199 |
| 點 拿鐵 2（也可寫「2杯」「2個」） | 加入購物車並回報合計 |
| 點 摩卡 半糖少冰、無糖去冰（也可寫「點 摩卡 2 半糖少冰」，兩杯都半糖少冰） | 每杯各自的甜度（全糖、半糖、微糖、無糖）與冰量（正常冰、少冰、微冰、去冰）；購物車和結帳會列出每杯的甜度冰量 |
| 購物車 | 目前的品項與合計 |
| 清空 | 清空購物車 |
| 結帳 | 成立訂單、提醒取餐時間並清空購物車 |
| 其他 | 使用說明 |

回覆邏輯在 `bot/replies.py`（純函式，不需要 LINE 帳號就能測）；webhook 在 `app.py`，會驗證 `X-Line-Signature`。

## 在本機試用與測試

需要 Python 3.10 以上。

```sh
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q          # 測試不連網：簽章用測試用的 secret，回覆 API 以替身取代
printf '菜單\n點 拿鐵 2\n結帳\n' | .venv/bin/python -m bot.cli   # 不用 LINE 帳號的本機模擬
```

## 線上試用頁

`index.html` 是一個聊天頁面，在瀏覽器裡用 Pyodide 執行同一份 `bot/replies.py`，所以試用頁和真的機器人回覆完全一樣。它放在 GitHub Pages 上，任何人都能打開。

## 接上真的 LINE 頻道

部署到 Cloud Run 時，Google Cloud 的 buildpacks 會讀 `requirements.txt` 並用 `Procfile`（gunicorn，入口 `app:app_from_env()`）啟動服務；`LINE_CHANNEL_SECRET`、`LINE_CHANNEL_ACCESS_TOKEN` 以 Secret Manager 的環境變數提供。購物車存在記憶體裡，Demo 請把最大執行個體數設為 1。

1. 在 LINE Developers 建立 Messaging API channel，取得 Channel secret 與 Channel access token。
2. 以環境變數 `LINE_CHANNEL_SECRET`、`LINE_CHANNEL_ACCESS_TOKEN` 啟動 `python app.py`（預設 port 8080）。
3. 把可從外部連到的 HTTPS 網址 `https://<你的網域>/callback` 設為 Webhook URL（例如部署在 Cloud Run）。

## 提需求

直接開 issue，寫下想改什麼、改完要看到什麼。需要一字不差的回覆文字，請用「」或引號標出來，Juxta 會把原文寫進測試。
