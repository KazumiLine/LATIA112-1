# 後台視覺與排版重新設計、修復進度與任務分配

## 設計風格提案（3 套）

- 清爽卡片風（Modern Bootstrap）
  - 導航：固定頂欄 + 左側霧面漸層側邊欄（目前已套用）
  - 元件：圓角卡片、陰影、微互動（hover 輕微升起）
  - 優點：上手快、維護成本低，資訊密度適中
  - 適用：中小型電商後台

- 玻璃擬態（Glassmorphism）
  - 導航：毛玻璃透明側欄與工具列，背景柔和漸層
  - 元件：半透明卡片與表單，凸顯 KPI 與圖表
  - 優點：視覺識別度高，品牌感強
  - 適用：需要高辨識度的品牌後台

- 高對比專業深色系（Pro Dark）
  - 導航：深色側欄 + 主色點綴
  - 元件：高可讀字體、密度更高的表格與工具列、綠/黃/紅狀態徽章
  - 優點：長時間值班友善，資訊密度高
  - 適用：營運分析與大量維運場景

提示：後續可在 `app/templates/base.html` 引入主題變數（CSS variables），以 `data-theme` 切換三套主題。

## 本輪修復與新增

- 導航與樣式
  - 修正側邊欄漂移：使用 `position-sticky` 並以 `top:72px` 對齊固定頂欄
  - 側欄新增連結：`優惠券`、`頁面管理`，確保可見可達
- 後台功能
  - 用戶管理：新增 `GET /admin/users`（Manager 以上）
  - 訂單管理：在列表提供狀態下拉編輯，`POST /admin/orders/<id>/status`（Staff 以上），含狀態流轉驗證與付款/庫存同步
  - Raw Page：保留瀏覽與 TinyMCE 編輯頁（新增/編輯皆可）
  - Coupons：保留新增/編輯/刪除與列表
- 程式碼修正
  - 移除所有 `query.get_or_404()` 呼叫，改為手動檢查與 flash 訊息

## 完整端口清單與功能說明

### 認證與系統
- `GET/POST /login` - 管理員登入頁面
- `GET /logout` - 登出並清除 session
- `GET /healthz` - 健康檢查端點
- `GET /metrics` - 系統指標（用戶數、商品數、訂單數、已付款數）

### 前台頁面
- `GET /` - 首頁，顯示所有正常狀態商品

### 後台管理頁面
- `GET /admin` - 管理儀表板（總覽統計、最近訂單、快速操作）
- `GET /admin/orders` - 訂單列表與狀態管理
- `GET /admin/users` - 用戶列表（Manager 以上權限）
- `GET /admin/products` - 商品列表與搜尋
- `GET/POST /admin/products/new` - 新增商品表單（Manager 以上）
- `GET/POST /admin/products/<pid>/edit` - 編輯商品（Manager 以上）
- `POST /admin/products/<pid>/delete` - 隱藏商品（Manager 以上）
- `GET/POST /admin/products/<pid>/items` - 商品細項管理（Manager 以上）
- `POST /admin/items/<item_id>/edit` - 編輯商品細項（Manager 以上）
- `POST /admin/items/<item_id>/delete` - 刪除商品細項（Manager 以上）
- `GET/POST /admin/coupons` - 優惠券列表與新增（Manager 以上）
- `POST /admin/coupons/<cid>/edit` - 編輯優惠券（Manager 以上）
- `POST /admin/coupons/<cid>/delete` - 刪除優惠券（Manager 以上）
- `GET /admin/raw-pages` - 自訂頁面列表（Manager 以上）
- `GET/POST /admin/raw-pages/new` - 新增自訂頁面（Manager 以上）
- `GET/POST /admin/raw-pages/<rid>/edit` - 編輯自訂頁面（Manager 以上）
- `POST /admin/orders/<order_id>/status` - 更新訂單狀態（Staff 以上）

### API 端點
- `POST /api/orders` - 建立新訂單（含優惠券、庫存檢查、用戶建立）
- `PUT /api/orders/<order_id>/status` - 更新訂單狀態（含狀態驗證、庫存回補）
- `GET /api/products` - 取得所有商品與細項
- `POST /api/products` - 建立新商品（含細項）
- `PUT /api/products/<product_id>` - 更新商品資訊
- `DELETE /api/products/<product_id>` - 隱藏商品
- `GET /api/orders` - 取得所有訂單
- `GET /api/users` - 取得所有用戶
- `GET /api/stats` - 取得統計資料（商品數、訂單數、用戶數、月營收、分類統計）

### LINE Bot 端點
- `POST /callback` - LINE Bot webhook 接收
- `GET /health` - LINE Bot 健康檢查

## 端口測試結果與驗證

### 系統健康檢查 ✅
- `GET /healthz` - 正常回應：`{"status": "ok", "time": "2025-08-15T10:27:22.847980"}`
- `GET /metrics` - 正常回應：`{"orders": 21, "payments_paid": 4, "products": 12, "users": 12}`

### API 端點測試 ✅
- `GET /api/stats` - 正常回應：包含分類統計、月營收、總數等完整資料
- `GET /api/products` - 正常回應：返回商品列表與細項資訊
- `GET /api/users` - 正常回應：返回用戶資料（帳號、等級、錢包等）
- `GET /api/orders` - 正常回應：返回訂單資料與項目明細

### 前端頁面測試 ✅
- `GET /` - 正常載入：首頁 HTML 與 Bootstrap 樣式
- `GET /login` - 正常載入：登入頁面 HTML 與表單

### 資料庫狀態 ✅
- 已初始化：12 個商品、12 個用戶、21 個訂單
- 分類分布：電子產品(3)、配件(2)、居家(1)、戶外(2)、美食(2)、美妝(2)
- 月營收：NT$ 29,149

## 變更檔案摘要

- `app/web_api.py`
  - 新增 `admin_users` 路由
  - 新增 `admin_order_update_status` 路由
  - 修正所有 `get_or_404` 為手動檢查與 flash 訊息
- `app/templates/base.html`
  - 側欄穩定化與新增導覽連結（優惠券、頁面管理）
- `app/templates/admin/orders.html`
  - 每列新增「狀態編輯」表單
- `README.md`
  - 加入上述設計方案與測試指引（簡版）

## 驗收建議

1. 啟動：`python3 -m app.run --service web`（資料庫已初始化）
2. 登入：至 `/login` 任意帳密將建立測試帳號（或以種子資料登入）
3. 驗證：
   - `/admin` 儀表板載入與側欄穩定
   - `/admin/orders` 列表內更新狀態（觀察成功/失敗提示）
   - `/admin/users`、`/admin/coupons`、`/admin/raw-pages` 可瀏覽與操作
   - 測試各 API 端點回應正常

## 待辦與任務分配

- UI 主題切換（我）：抽象 CSS 變數與主題切換器
- 訂單詳情頁（我）：`/admin/orders/<id>` 顯示出貨、付款、紀錄與可操作動作
- 權限細緻化（我）：依 `AdminLevel` 控制側欄與表單可編輯
- 產品體驗優化（你）：提供偏好主題與實際使用中想強化的欄位/流程

## 時程

- D1：修復頁面與導覽、訂單編輯、文檔（完成）
- D2：主題切換、訂單詳情頁（進行中）
- D3：權限細緻化與表單校驗（預定）