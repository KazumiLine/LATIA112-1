# 後台視覺與排版重新設計、修復進度與任務分配

## 設計風格提案（3 套）✅ 已完成

- **清爽卡片風（Modern Bootstrap）** - 預設主題
  - 導航：固定頂欄 + 左側霧面漸層側邊欄
  - 元件：圓角卡片、陰影、微互動（hover 輕微升起）
  - 優點：上手快、維護成本低，資訊密度適中
  - 適用：中小型電商後台

- **玻璃擬態（Glassmorphism）** - 可切換主題
  - 導航：毛玻璃透明側欄與工具列，背景柔和漸層
  - 元件：半透明卡片與表單，凸顯 KPI 與圖表
  - 優點：視覺識別度高，品牌感強
  - 適用：需要高辨識度的品牌後台

- **高對比專業深色系（Pro Dark）** - 可切換主題
  - 導航：深色側欄 + 主色點綴
  - 元件：高可讀字體、密度更高的表格與工具列、綠/黃/紅狀態徽章
  - 優點：長時間值班友善，資訊密度高
  - 適用：營運分析與大量維運場景

## 本輪修復與新增 ✅ 已完成

### 導航與樣式
- ✅ 修正側邊欄漂移：使用 `position-sticky` 並以 `top: 60px` 對齊固定頂欄
- ✅ 側欄新增連結：`優惠券`、`頁面管理`，確保可見可達
- ✅ 修正 Navbar 高度與左側 Navbar 空白問題
- ✅ 實現三套主題切換：現代、玻璃擬態、專業深色

### 後台功能
- ✅ 用戶管理：新增 `GET/POST /admin/users`（Manager 以上）
- ✅ 訂單管理：在列表提供狀態下拉編輯，`POST /admin/orders/<id>/status`（Staff 以上）
- ✅ 訂單詳情頁：`/admin/orders/<id>` 顯示出貨、付款、紀錄與可操作動作
- ✅ Raw Page：保留瀏覽與 Quill.js 編輯頁（新增/編輯皆可）
- ✅ Coupons：保留新增/編輯/刪除與列表
- ✅ 權限細緻化：依 `AdminLevel` 控制側欄與表單可編輯

### 程式碼修正
- ✅ 移除所有 `query.get_or_404()` 呼叫，改為手動檢查與 flash 訊息
- ✅ 支援多商店管理：所有商品操作都帶上 `store_id`

### UI/UX 改進
- ✅ 所有編輯操作改為彈出視窗（Modal）方式
- ✅ 支援 RWD：優化手機上的觀看體驗，支援任意長寬比的畫面
- ✅ 主題切換器：右上角固定位置，可即時切換三套主題
- ✅ 響應式設計：側邊欄在手機上可收合，主內容區域自適應

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
- `GET /admin/orders/<id>` - 訂單詳情頁（含物流、付款、紀錄）
- `POST /admin/orders/<id>/status` - 更新訂單狀態
- `POST /admin/orders/<id>/delivery` - 更新物流資訊
- `POST /admin/orders/<id>/payment` - 更新付款資訊
- `GET /admin/users` - 用戶列表（Manager 以上權限）
- `POST /admin/users` - 新增用戶
- `POST /admin/users/<id>/edit` - 編輯用戶
- `GET /admin/users/<id>/details` - 用戶詳情 API
- `GET /admin/products` - 商品列表與搜尋（支援商店篩選）
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

## 端口測試結果與驗證 ✅ 已完成

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

### 核心功能更新
- `app/web_api.py`
  - ✅ 新增 `admin_users_add`、`admin_users_edit`、`admin_users_details` 路由
  - ✅ 新增 `admin_order_detail`、`admin_order_update_delivery`、`admin_order_update_payment` 路由
  - ✅ 修正所有 `get_or_404` 為手動檢查與 flash 訊息
  - ✅ 支援多商店管理：商品 CRUD 都帶上 `store_id`
  - ✅ 改進商品搜尋：支援狀態篩選

### 模板更新
- `app/templates/base.html`
  - ✅ 實現三套主題切換（CSS variables + JavaScript）
  - ✅ 修正側邊欄定位與 RWD 支援
  - ✅ 新增主題切換器與響應式設計
  - ✅ 優化手機體驗：側邊欄收合、主內容自適應

- `app/templates/admin/products.html`
  - ✅ 改為彈出視窗編輯
  - ✅ 支援商店篩選與狀態篩選
  - ✅ 改進商品顯示：圖片、狀態徽章、操作按鈕

- `app/templates/admin/product_items.html`
  - ✅ 改為彈出視窗編輯
  - ✅ 改進商品資訊顯示
  - ✅ 新增/編輯/刪除操作

- `app/templates/admin/coupons.html`
  - ✅ 改為彈出視窗編輯
  - ✅ 改進優惠券顯示與操作

- `app/templates/admin/users.html`
  - ✅ 改為彈出視窗編輯
  - ✅ 新增用戶功能
  - ✅ 用戶詳情查看

- `app/templates/admin/orders.html`
  - ✅ 改進訂單顯示：客戶資訊、商品列表、狀態徽章
  - ✅ 新增篩選功能與詳情連結
  - ✅ 狀態編輯改為彈出視窗

- `app/templates/admin/order_detail.html` ⭐ 新檔案
  - ✅ 完整的訂單詳情頁面
  - ✅ 客戶資訊、商品項目、訂單紀錄
  - ✅ 物流資訊編輯、付款資訊編輯
  - ✅ 狀態更新與操作記錄

- `app/templates/admin/raw_page_form.html`
  - ✅ 替換 TinyMCE 為免費的 Quill.js 編輯器
  - ✅ 改進表單佈局與驗證

## 驗收建議

1. **啟動服務**：`python3 -m app.run --service web`（資料庫已初始化）
2. **登入測試**：至 `/login` 測試後台功能
3. **主題切換**：右上角主題切換器測試三套設計風格
4. **彈出視窗**：測試所有新增/編輯操作的彈出視窗
5. **RWD 測試**：調整瀏覽器視窗大小，測試手機版側邊欄收合
6. **多商店**：測試商品管理的商店篩選功能
7. **訂單詳情**：點擊訂單列表的查看詳情，測試完整訂單頁面

## 技術特色

### 主題系統
- CSS Variables 實現主題切換
- 三套完整設計風格
- 即時切換，無需重新載入

### 響應式設計
- Bootstrap 5 網格系統
- 手機版側邊欄收合
- 自適應表格與表單

### 彈出視窗系統
- Bootstrap Modal 組件
- 統一的 JavaScript 輔助函數
- 自動隱藏與表單驗證

### 多商店支援
- 所有商品操作都帶上 `store_id`
- 商店篩選與管理
- 資料隔離與權限控制

## 待辦與任務分配

- ✅ UI 主題切換：抽象 CSS 變數與主題切換器（已完成）
- ✅ 訂單詳情頁：`/admin/orders/<id>` 顯示出貨、付款、紀錄與可操作動作（已完成）
- ✅ 權限細緻化：依 `AdminLevel` 控制側欄與表單可編輯（已完成）
- ✅ 多商店管理：支援 `store_id` 的商品管理（已完成）
- ✅ 彈出視窗：所有編輯操作改為 Modal 方式（已完成）
- ✅ RWD 支援：手機版優化與響應式設計（已完成）
- ✅ 免費編輯器：替換 TinyMCE 為 Quill.js（已完成）

## 時程

- D1：修復頁面與導覽、訂單編輯、文檔（已完成）
- D2：主題切換、訂單詳情頁、彈出視窗系統（已完成）
- D3：權限細緻化、多商店支援、RWD 優化（已完成）

## 總結

所有要求的項目都已完成：
1. ✅ 免費編輯器（Quill.js）
2. ✅ Navbar 高度修正
3. ✅ RWD 支援與手機優化
4. ✅ 彈出視窗編輯系統
5. ✅ 三套主題切換
6. ✅ 訂單詳情頁面
7. ✅ 權限細緻化
8. ✅ 多商店管理支援
9. ✅ 物流與付款表格更新

系統已準備好進行全面測試與部署。