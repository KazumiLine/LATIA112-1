# 智能電商平台 - Intelligent E-commerce Platform

基於 Python LlamaIndex 的智能電商平台，整合了 AI 客服、LINE Bot、現代化 Web 介面和完整的電商功能。

## 🚀 主要功能

### AI 智能客服 (LlamaIndex Agent)
- **產品查詢**: 使用 SQL 生成器查詢商品資料
- **訂單查詢**: 智能查詢訂單狀態和歷史
- **售後服務**: 基於本地文檔的智能問答
- **下單功能**: 自動處理訂單並存入資料庫
- **資訊補充**: 智能識別缺失資訊並要求補充
- **對話記憶**: 每位客戶的對話歷史持久化

### Web 管理後台
- **現代化 UI**: Bootstrap 5 + Vue.js 3 響應式設計
- **儀表板**: 即時統計、圖表、訂單摘要
- **商品管理**: 完整的 CRUD 操作
- **訂單管理**: 訂單狀態追蹤和處理
- **用戶管理**: 會員等級和權限管理
- **API 端點**: RESTful API 支援

### LINE Bot 整合
- **智能對話**: 連接 LlamaIndex Agent
- **快速回覆**: 預設問答和操作按鈕
- **商品展示**: 輪播圖商品展示
- **訂單查詢**: 透過 LINE 查詢訂單狀態
- **客服支援**: 24/7 自動客服服務

## 🛠️ 技術架構

- **後端**: Python 3.10+, Flask, SQLAlchemy
- **AI 引擎**: LlamaIndex, OpenAI (可選)
- **資料庫**: SQLite (預設), 支援 PostgreSQL/MySQL
- **前端**: Bootstrap 5, Vue.js 3, Chart.js
- **通訊**: LINE Bot SDK, RESTful API
- **部署**: 支援 Docker, 雲端部署

## 📋 系統需求

- Python 3.10 或更高版本
- 8GB RAM (建議)
- 2GB 磁碟空間
- 網路連接 (用於外部 API)

## 🚀 快速開始

### 1. 環境準備

```bash
# 檢查 Python 版本
python3 --version

# 建立虛擬環境 (可選)
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate     # Windows
```

### 2. 安裝依賴

```bash
# 安裝所有依賴
pip install -r requirements.txt

# 如果遇到權限問題，使用
pip install --user --break-system-packages -r requirements.txt
```

### 3. 環境配置

```bash
# 複製環境變數檔案
cp .env.example .env

# 編輯 .env 檔案，填入必要的 API 金鑰
nano .env
```

### 4. 初始化資料庫

```bash
# 初始化資料庫並建立預設資料
python -m app.run --init-db
```

### 5. 啟動服務

```bash
# 啟動 Web API (預設)
python -m app.run

# 啟動 LINE Bot
python -m app.run --service line

# 同時啟動兩個服務
python -m app.run --service both

# 檢查環境配置
python -m app.run --check-env
```

## 🌐 服務端點

### Web 介面
- **首頁**: http://localhost:5000
- **管理後台**: http://localhost:5000/admin
- **商品目錄**: http://localhost:5000/products

### API 端點
- **商品 API**: http://localhost:5000/api/products
- **訂單 API**: http://localhost:5000/api/orders
- **用戶 API**: http://localhost:5000/api/users
- **統計 API**: http://localhost:5000/api/stats

### LINE Bot
- **Webhook**: http://localhost:5001/callback
- **健康檢查**: http://localhost:5001/health

## 🔧 配置說明

### 環境變數

| 變數名稱 | 說明 | 必填 | 預設值 |
|---------|------|------|--------|
| `OPENAI_API_KEY` | OpenAI API 金鑰 | 否 | 使用 Mock LLM |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Bot 存取權杖 | 否 | 僅本地測試 |
| `LINE_CHANNEL_SECRET` | LINE Bot 密鑰 | 否 | 僅本地測試 |
| `DATABASE_URL` | 資料庫連線字串 | 否 | SQLite |
| `SECRET_KEY` | Flask 密鑰 | 是 | 隨機生成 |
| `APP_DB_PATH` | 資料庫檔案路徑 | 否 | storage/app.db |
| `APP_DOCS_DIR` | 文檔目錄 | 否 | docs/ |

### 資料庫配置

#### SQLite (預設)
```bash
DATABASE_URL=sqlite:///storage/app.db
```

#### PostgreSQL
```bash
DATABASE_URL=postgresql://user:password@localhost/dbname
```

#### MySQL
```bash
DATABASE_URL=mysql://user:password@localhost/dbname
```

## 📱 LINE Bot 設定

### 1. 建立 LINE 官方帳號
1. 前往 [LINE Developers Console](https://developers.line.biz/)
2. 建立新的 Provider 和 Channel
3. 取得 Channel Access Token 和 Channel Secret

### 2. 設定 Webhook URL
```
https://your-domain.com/callback
```

### 3. 環境變數設定
```bash
LINE_CHANNEL_ACCESS_TOKEN=your-token-here
LINE_CHANNEL_SECRET=your-secret-here
```

## 🎯 使用範例

### AI 客服對話

```
用戶: 我想查詢 SKU-1002 的價格和庫存
AI: 根據資料庫查詢，SKU-1002 機械鍵盤的價格是 NT$ 89.50，目前庫存 80 件。

用戶: 幫我下單 SKU-1001 2個，寄給 alice@example.com
AI: 已為您建立訂單！訂單編號 #123，總金額 NT$ 59.98，包含運費 NT$ 0。我們會在 24 小時內發貨。

用戶: 如何退貨？
AI: 根據我們的退換貨政策，您享有七日鑑賞期（未拆封可退換）。退貨時請提供訂單編號和退貨原因，我們會安排取件。運費由買方負擔。
```

### LINE Bot 互動

```
用戶: 你好
Bot: 歡迎使用我們的智能客服！我可以幫助您查詢商品、查看訂單、了解購買流程等。

用戶: 我想查詢商品
Bot: [顯示商品分類選項] 請選擇您感興趣的商品類別，或直接告訴我您想了解什麼商品。
```

## 📊 管理後台功能

### 儀表板
- 即時統計數據
- 營收趨勢圖表
- 商品分類分布
- 訂單狀態摘要
- 系統健康狀態

### 商品管理
- 新增/編輯/刪除商品
- 商品分類管理
- 庫存追蹤
- 價格管理
- 商品狀態控制

### 訂單管理
- 訂單狀態追蹤
- 付款狀態管理
- 發貨處理
- 退換貨處理
- 訂單歷史查詢

### 用戶管理
- 會員資料管理
- 會員等級設定
- 實名認證管理
- 錢包餘額管理
- 推薦人系統

## 🔒 安全性

- **API 認證**: JWT Token 認證
- **資料加密**: 密碼雜湊加密
- **SQL 注入防護**: 參數化查詢
- **XSS 防護**: 輸入驗證和清理
- **CSRF 防護**: CSRF Token 驗證

## 🚀 部署指南

### Docker 部署

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000 5001

CMD ["python", "-m", "app.run", "--service", "both"]
```

### 雲端部署

#### Heroku
```bash
# 建立 Procfile
echo "web: python -m app.run --service web" > Procfile
echo "worker: python -m app.run --service line" >> Procfile

# 部署
git push heroku main
```

#### AWS/GCP/Azure
- 使用 App Engine 或 App Service
- 設定環境變數
- 配置資料庫連線
- 設定域名和 SSL

## 🧪 測試

### 單元測試
```bash
python -m pytest tests/
```

### 整合測試
```bash
python -m pytest tests/integration/
```

### API 測試
```bash
# 使用 curl 測試 API
curl http://localhost:5000/api/products
curl http://localhost:5000/api/stats
```

## 📈 監控和日誌

### 日誌配置
- 應用程式日誌: `logs/app.log`
- 錯誤日誌: `logs/error.log`
- 存取日誌: `logs/access.log`

### 監控指標
- API 回應時間
- 資料庫連線狀態
- 系統資源使用率
- 錯誤率和異常

## 🤝 貢獻指南

1. Fork 專案
2. 建立功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交變更 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟 Pull Request

## 📄 授權

本專案採用 MIT 授權條款 - 詳見 [LICENSE](LICENSE) 檔案

## 📞 支援

- **技術文件**: [Wiki](https://github.com/your-repo/wiki)
- **問題回報**: [Issues](https://github.com/your-repo/issues)
- **討論區**: [Discussions](https://github.com/your-repo/discussions)
- **聯絡信箱**: support@example.com

## 🙏 致謝

- [LlamaIndex](https://github.com/jerryjliu/llama_index) - AI 框架
- [Flask](https://flask.palletsprojects.com/) - Web 框架
- [Bootstrap](https://getbootstrap.com/) - UI 框架
- [Vue.js](https://vuejs.org/) - 前端框架
- [LINE Bot SDK](https://github.com/line/line-bot-sdk-python) - LINE 整合

---

⭐ 如果這個專案對您有幫助，請給我們一個星標！
