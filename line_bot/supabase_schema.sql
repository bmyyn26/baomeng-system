-- =============================================
--  寶萌管理系統 Supabase 資料庫建表語法
--  在 Supabase → SQL Editor 貼上執行
-- =============================================

-- 客戶資料表（包含黑名單）
CREATE TABLE IF NOT EXISTS customers (
    id              SERIAL PRIMARY KEY,
    classification  TEXT,                        -- 會員分類
    id_9188         BIGINT,                      -- 9188 平台編號
    nickname_id     BIGINT,                      -- 暱稱編號
    nickname        TEXT,                        -- 暱稱
    bank_account    TEXT,                        -- 銀行帳號
    account_holder  TEXT,                        -- 戶名
    phone           TEXT,                        -- 電話
    id_number       TEXT,                        -- 身分證
    notes           TEXT,                        -- 備註
    notes2          TEXT,                        -- 備註2
    is_blacklist    BOOLEAN DEFAULT FALSE,       -- 是否黑名單
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 建立索引加速搜尋
CREATE INDEX IF NOT EXISTS idx_customers_nickname    ON customers (nickname);
CREATE INDEX IF NOT EXISTS idx_customers_phone       ON customers (phone);
CREATE INDEX IF NOT EXISTS idx_customers_id_9188     ON customers (id_9188);
CREATE INDEX IF NOT EXISTS idx_customers_is_blacklist ON customers (is_blacklist);


-- 訂單資料表
CREATE TABLE IF NOT EXISTS orders (
    id                SERIAL PRIMARY KEY,
    date              DATE,                      -- 交易日期
    sell_diamonds     NUMERIC(15,2),             -- 賣紅鑽數量
    buy_diamonds      NUMERIC(15,2),             -- 買紅鑽數量
    customer_nickname TEXT,                      -- 客戶暱稱
    transfer_out      NUMERIC(15,2),             -- 轉出金額
    transfer_in       NUMERIC(15,2),             -- 轉入金額
    fee               NUMERIC(15,2),             -- 手續費
    balance           NUMERIC(15,2),             -- 結存
    order_no_start    TEXT,                      -- 9188訂單編號（起）
    order_no_end      TEXT,                      -- 9188訂單編號（終）
    notes             TEXT,                      -- 備註
    customer_id_new   BIGINT,                    -- 客戶新編號
    bank_account      TEXT,                      -- 銀行帳號
    time_note         TEXT,                      -- 時間備註
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- 建立索引加速搜尋
CREATE INDEX IF NOT EXISTS idx_orders_nickname ON orders (customer_nickname);
CREATE INDEX IF NOT EXISTS idx_orders_date     ON orders (date DESC);


-- =============================================
--  完成！回到 Python 執行 import_data.py 匯入資料
-- =============================================
