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

## 變更檔案摘要

- `app/web_api.py`
  - 新增 `admin_users` 路由
  - 新增 `admin_order_update_status` 路由
- `app/templates/base.html`
  - 側欄穩定化與新增導覽連結（優惠券、頁面管理）
- `app/templates/admin/orders.html`
  - 每列新增「狀態編輯」表單
- `README.md`
  - 加入上述設計方案與測試指引（簡版）

## 驗收建議

1. 啟動：`python -m app.run --service web --init-db`
2. 登入：至 `/login` 任意帳密將建立測試帳號（或以種子資料登入）
3. 驗證：
   - `/admin` 儀表板載入與側欄穩定
   - `/admin/orders` 列表內更新狀態（觀察成功/失敗提示）
   - `/admin/users`、`/admin/coupons`、`/admin/raw-pages` 可瀏覽與操作

## 待辦與任務分配

- UI 主題切換（我）：抽象 CSS 變數與主題切換器
- 訂單詳情頁（我）：`/admin/orders/<id>` 顯示出貨、付款、紀錄與可操作動作
- 權限細緻化（我）：依 `AdminLevel` 控制側欄與表單可編輯
- 產品體驗優化（你）：提供偏好主題與實際使用中想強化的欄位/流程

## 時程

- D1：修復頁面與導覽、訂單編輯、文檔（完成）
- D2：主題切換、訂單詳情頁（進行中）
- D3：權限細緻化與表單校驗（預定）