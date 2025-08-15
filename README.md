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

## 後台重新設計提案與進度追蹤

### 視覺與版型風格方案（至少三套）

1) 清爽卡片風（現代 Bootstrap 強化）
- 導航：固定頂欄 + 左側霧面漸層側邊欄（目前實作）
- 元件：圓角卡片、浮影、色彩標籤，滑過升起微動效
- 優點：學習成本低、上手快、資訊密度適中
- 適用：電商中小型後台，快速上線

2) 玻璃擬態（Glassmorphism）
- 導航：半透明毛玻璃側欄與工具列，背景淡色漸層
- 元件：卡片與表單皆半透明，強調圖表與重點 KPI
- 優點：視覺顯著、品牌感強
- 適用：需要較高識別度的品牌後台

3) 高對比專業深色系（Pro Dark）
- 導航：深色側欄 + 高對比品牌主色點綴
- 元件：高可讀字體、密度更高的資料表與工具列
- 優點：長時間使用舒適，資料密集頁面清晰
- 適用：營運分析、商品/訂單大量維運場景

若需切換主題：可在 `app/templates/base.html` 引入主題變數集（CSS 變數）與主題切換器，再加上 `data-theme` 動態切換。

### 本輪修復與新增功能

- 導航與風格
  - 修正後台左側側邊欄偶發「漂移」：改為固定高度與 `position-sticky` 並以 `top:72px` 對齊頂欄
  - 補上側邊欄連結：`優惠券`、`頁面管理`
- 後台頁面與路由
  - 新增 `GET /admin/users` 路由與頁面呈現（權限：Manager 以上）
  - 補強 `admin/orders.html`：每列提供狀態下拉＋儲存按鈕
  - 新增 `POST /admin/orders/<order_id>/status`（權限：Staff 以上），含狀態流轉驗證與付款/庫存同步
  - Raw Page 與 Coupons 頁面已可瀏覽與編輯（連結已在側欄顯示）

### 變更檔案

- `app/web_api.py`
  - 新增：`admin_users` 路由
  - 新增：`admin_order_update_status` 路由（訂單狀態編輯）
- `app/templates/base.html`
  - 修正側欄排版，新增 `優惠券`、`頁面管理` 連結
- `app/templates/admin/orders.html`
  - 新增每列「狀態編輯」表單

### 測試建議

- 啟動：`python -m app.run --service web --init-db`（首次可加 `--init-db`）
- 登入：`/login` 用任意帳密將自動建立測試帳號（或使用種子 `admin@example.com` 搭配 `admin123` 在 API 層驗證）
- 驗證：
  - 進入 `/admin` 檢視側欄穩定與指標卡片
  - 進入 `/admin/orders` 測試訂單狀態切換與訊息提醒
  - 進入 `/admin/users`、`/admin/coupons`、`/admin/raw-pages` 驗證瀏覽/編輯

### 待辦與分工（可依需求調整）

- UI 主題切換（我）：抽象 CSS 變數與主題切換器
- 權限細緻化（我）：以 `AdminLevel` 控制側欄項目與表單可編輯性
- 訂單詳情頁（我）：建立 `/admin/orders/<id>` 含出貨/付款細節與操作
- 可用性優化（你）：回饋優先的主題偏好、欄位與流程調整意見

### 時間軸

- 第 1 天：修復頁面與導覽、訂單編輯、撰寫文檔（已完成）
- 第 2 天：主題切換、訂單詳情頁
- 第 3 天：權限細緻化與表單校驗
