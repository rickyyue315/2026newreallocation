import os

VERSION = "v2.15.0"

ZEABUR_ENV_KEYS = [
    "ZEABUR_ENV",
    "ZEABUR_REGION",
    "ZEABUR_SERVICE_ID",
    "ZEABUR_WEB_URL",
    "ZEABUR",
    "RAILWAY_ENV",
    "RENDER",
    "FL0_ENV",
    "STREAMLIT_SERVER_MAX_UPLOAD_SIZE",
]
IS_ZEABUR_RUNTIME = any(os.getenv(k) for k in ZEABUR_ENV_KEYS)
ZEABUR_RESULT_PREVIEW_LIMIT = 1000

A_MODE_PERCENTAGE_CAP = 0.2
A_MODE_MIN_TRANSFER = 2
B_MODE_PERCENTAGE_CAP = 0.5
B_MODE_MIN_TRANSFER = 2
C_MODE_PERCENTAGE_CAP = 0.3
C_MODE_ABS_CAP = 3
C1_MODE_MIN_TRANSFER = 2
SAFETY_RECEIVE_MULTIPLIER = 2
MIN_RECEIVE_FLOOR = 3
F_TARGET_MULTIPLIER = 0.5
F_TARGET_FLOOR = 3
SIMPLIFIED_SKU_RECEIVE_MULTIPLIER = 2
ND_RECEIVE_MULTIPLIER = 2
OUTLIER_CAP = 100000
FILE_SIZE_LIMIT_BYTES = 50 * 1024 * 1024

SOURCE_ND = "ND轉出"
SOURCE_ND_SMART = "ND智能轉出"
SOURCE_ND_F_MODE = "F模式ND轉出"
SOURCE_ND_CLEARANCE = "ND清貨轉出"
SOURCE_RF_SURPLUS = "RF過剩轉出"
SOURCE_RF_SURPLUS_C_FALLBACK = "RF過剩轉出(C模式回退)"
SOURCE_RF_ENHANCED = "RF加強轉出"
SOURCE_RF_ENHANCED_C_FALLBACK = "RF加強轉出(C模式回退)"
SOURCE_RF_F_MODE = "F模式RF轉出"
SOURCE_LOCAL_FULL = "Local店舖全轉出"
SOURCE_E_MANDATORY = "E模式強制轉出"
SOURCE_SIMPLIFIED_ND = "精簡SKU ND轉出"
SOURCE_SIMPLIFIED_RF = "精簡SKU RF轉出"

DEST_CRITICAL = "緊急缺貨"
DEST_CRITICAL_ZERO = "緊急缺貨補貨"
DEST_CRITICAL_RESTOCK = "RF緊急缺貨補貨"
DEST_POTENTIAL = "潛在缺貨"
DEST_POTENTIAL_ND = "ND潛在缺貨接收"
DEST_ZERO_STOCK = "重點補0"
DEST_F_TARGET = "F模式目標接收"
DEST_F2_TARGET = "F指定模式目標接收"
DEST_E_RECEIVE = "E模式接收"
DEST_E1B_RECEIVE_PREFIX = "E1b"
DEST_SIMPLIFIED_RECV = "精簡SKU接收"

DEST_CRITICAL_PRIORITY = 1
DEST_POTENTIAL_PRIORITY = 2
DEST_ZERO_STOCK_PRIORITY = 1
SOURCE_ND_PRIORITY = 1
SOURCE_RF_PRIORITY = 2

REQUIRED_COLUMNS = [
    "Article",
    "OM",
    "RP Type",
    "Site",
    "SaSa Net Stock",
    "Pending Received",
    "Safety Stock",
    "Last Month Sold Qty",
    "MTD Sold Qty",
    "MOQ",
]

OPTIONAL_COLUMNS = [
    "Article Description",
    "Article Long Text (60 Chars)",
    "ALL",
    "Target",
    "Type",
    "Last 2 Month Sold Qty",
    "Product Hierarchy",
    "Brand",
]

INTEGER_COLUMNS = [
    "SaSa Net Stock",
    "Pending Received",
    "Safety Stock",
    "Last Month Sold Qty",
    "MTD Sold Qty",
    "MOQ",
]

STRING_COLUMNS = ["OM", "RP Type", "Site"]

EXCEL_HEADER_BG = "#D7E4BC"
EXCEL_HEADER_FONT = "Arial"
EXCEL_HEADER_SIZE = 10

THEME = {
    "bg_primary": "#0A0A0F",
    "accent": "#F5A623",
    "success": "#10B981",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "info": "#3B82F6",
    "text_primary": "#F9FAFB",
    "text_secondary": "#9CA3AF",
}

MODE_OPTIONS = [
    "A: 保守轉貨",
    "B: 加強轉貨",
    "B2: 附加B(特別模式)",
    "B2a: 附加B2a(T不出貨)",
    "B2L: 附加B2L(L保留2)",
    "B2La: 附加B2La(L2+T不出)",
    "B3: 附加B3(跨OM)",
    "B3a: 附加B3a(跨OM+T不出)",
    "B3L: 附加B3L(跨OM+L2)",
    "B3La: 附加B3La(跨OM+L2+T)",
    "C: 重點補0",
    "C1: 重點補0-只補0/1",
    "C2: 附加C2(跨OM)",
    "D: 清貨轉貨",
    "D2: 清貨轉貨(ND限定)",
    "E1: 強制轉出",
    "E1b: 強制轉出(優先類型)",
    "E2: 強制轉出(跨OM)",
    "F: 目標優化",
    "F2: F指定模式",
    "ND1: ND同OM轉貨",
    "ND2: ND混合OM轉貨",
    "簡同: 精簡SKU(限同OM)",
    "簡跨: 精簡SKU(跨OM)",
]

TRANSFER_EXCEL_COLUMNS = [
    "Brand",
    "Article",
    "Product Desc",
    "Transfer OM",
    "Transfer Site",
    "Receive OM",
    "Receive Site",
    "Transfer Qty",
    "Transfer Original Stock",
    "Transfer After Transfer Stock",
    "Transfer Safety Stock",
    "Transfer MOQ",
    "Remark",
    "Notes",
    "Transfer Site Last Month Sold Qty",
    "Transfer Site MTD Sold Qty",
    "Receive Site Last Month Sold Qty",
    "Receive Site MTD Sold Qty",
    "Receive Original Stock",
]
