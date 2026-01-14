# AI Mock Interview

[English](./README.md) | [繁體中文](./README.zh-TW.md)

Use AI to do mock interviews while AI is taking away our jobs 👊😡.
(僅在 MacOS 中使用 Chrome 測試過)

## 功能：
* 聊天機器人風格的網頁介面，可以錄音回答問題，並收到來自 LLM 的語音回覆。
* 支援上傳你的履歷 (pdf)、設定面試偏好。
* 在面試過程中獲得文法修正或 AI 建議的回答。
* 取得由 LLM 產生的面試評估與診斷。

<img src="imgs/interview.png" width="600">

## 需求
* 💰 OpenAI API Key：比你想像中便宜。
* 🐳 Docker（如果沒有 Docker ，也可以用純 Python 環境執行）。

## 開始使用
### 1. 準備 Docker Image：
你可以直接下載映像檔，或者用原始碼自己 build。

#### 直接 pull image
```
docker pull ghcr.io/hyades910739/ai-mock-interview:latest
```

#### 自己 build:
先 clone 這個 repo。
```
git clone https://github.com/hyades910739/ai-mock-interview.git
```

build Docker image
```
docker build --no-cache -t ai-mock-interview .
```

### 2. 執行 Docker Image：
```
docker run -p 8000:8000 -e OPENAI_API_KEY="sk-***" ai-mock-interview
```

* 你可以在 `docker run` 時設定 `OPENAI_API_KEY`，或者之後在設定頁面中再設定。
* 請在瀏覽器中允許麥克風存取權限。
