from config import (
    SOURCE_ND,
    SOURCE_ND_SMART,
    SOURCE_ND_F_MODE,
    SOURCE_ND_CLEARANCE,
    SOURCE_RF_SURPLUS,
    SOURCE_RF_ENHANCED,
    SOURCE_RF_F_MODE,
    SOURCE_LOCAL_FULL,
    SOURCE_E_MANDATORY,
    SOURCE_SIMPLIFIED_ND,
    SOURCE_SIMPLIFIED_RF,
    DEST_F_TARGET,
    DEST_F2_TARGET,
    DEST_E_RECEIVE,
    DEST_ZERO_STOCK,
    DEST_CRITICAL,
    DEST_CRITICAL_RESTOCK,
    DEST_POTENTIAL,
    DEST_POTENTIAL_ND,
    DEST_SIMPLIFIED_RECV,
)


def create_recommendation_note(rec: dict) -> str:
    parts = []

    source_type = rec.get("Source Type", "")
    dest_type = rec.get("Destination Type", "")

    source_analysis = _note_source_analysis(rec, source_type)
    if source_analysis:
        parts.append(source_analysis)

    dest_analysis = _note_dest_analysis(rec, dest_type)
    if dest_analysis:
        parts.append(dest_analysis)

    return " | ".join(parts)


def _note_source_analysis(rec: dict, source_type: str) -> str:
    site = rec.get("Transfer Site", "")
    original = rec.get("Transfer Original Stock", 0)
    after = rec.get("Transfer After Transfer Stock", 0)
    safety = rec.get("Transfer Safety Stock", 0)
    last = rec.get("Transfer Site Last Month Sold Qty", 0)
    mtd = rec.get("Transfer Site MTD Sold Qty", 0)
    om = rec.get("Transfer OM", "")

    if source_type == SOURCE_ND_SMART:
        total_sales = last + mtd
        return (
            f"【轉出分析】{site}({om}) ND智能轉出 | "
            f"0銷量優先 | 兩月銷量={total_sales} | "
            f"轉後剩餘={after}"
        )
    elif source_type == SOURCE_ND:
        return f"【轉出分析】{site}({om}) ND轉出 | 無庫存限制,可全數轉出"
    elif source_type == SOURCE_ND_F_MODE:
        return f"【轉出分析】{site}({om}) F模式ND轉出 | 無庫存限制,全數轉出"
    elif source_type == SOURCE_ND_CLEARANCE:
        return (
            f"【轉出分析】{site}({om}) ND清貨轉出 | "
            f"轉後剩餘={after} | 已優化避免1件"
        )
    elif source_type == SOURCE_RF_F_MODE:
        return (
            f"【轉出分析】{site}({om}) F模式RF轉出 | "
            f"可忽視最小庫存要求 | 轉後剩餘={after}"
        )
    elif source_type == SOURCE_E_MANDATORY:
        all_val = rec.get("ALL", "N/A")
        rp = rec.get("rp_type", "")
        return (
            f"【轉出分析】{site}({om}) E模式強制轉出(ALL={all_val}) | "
            f"{rp} | 原始庫存={original} | 轉後剩餘={after}"
        )
    elif source_type == SOURCE_LOCAL_FULL:
        total_sales = last + mtd
        return (
            f"【轉出分析】{site}({om}) Local店舖全轉出(L型) | "
            f"可全數轉出 | 兩月銷量={total_sales} | 轉後剩餘={after}"
        )
    elif SOURCE_RF_SURPLUS in source_type:
        return (
            f"【轉出分析】{site}({om}) RF過剩轉出 | "
            f"Safety={safety} | 轉後剩餘={after}(>={safety})"
        )
    elif SOURCE_RF_ENHANCED in source_type:
        return (
            f"【轉出分析】{site}({om}) RF加強轉出 | "
            f"Safety={safety} | 轉後剩餘={after}(可能<={safety})"
        )
    elif source_type == SOURCE_SIMPLIFIED_ND:
        return f"【轉出分析】{site}({om}) 精簡SKU ND轉出 | 全數可轉出"
    elif source_type == SOURCE_SIMPLIFIED_RF:
        return (
            f"【轉出分析】{site}({om}) 精簡SKU RF轉出 | "
            f"超出Cap部分轉出 | 兩月銷量={last + mtd}"
        )

    return f"【轉出分析】{site}({om}) {source_type}"


def _note_dest_analysis(rec: dict, dest_type: str) -> str:
    site = rec.get("Receive Site", "")
    om = rec.get("Receive OM", "")
    needed = rec.get("needed_qty", rec.get("Transfer Qty", 0))
    target = rec.get("Target Qty", 0)
    cum_recv = rec.get("Cumulative Received Qty", 0)
    safety = rec.get("Transfer Safety Stock", 0)
    last = rec.get("Receive Site Last Month Sold Qty", 0)
    mtd = rec.get("Receive Site MTD Sold Qty", 0)

    if dest_type in (DEST_F_TARGET, DEST_F2_TARGET):
        return (
            f"【接收分析】{site}({om}) 目標接收 | "
            f"目標={target} | 累計={cum_recv} | 缺口={max(0, target - cum_recv)}"
        )
    elif dest_type == DEST_E_RECEIVE or dest_type.startswith("E1b"):
        return (
            f"【接收分析】{site}({om}) {dest_type} | "
            f"當前總庫存={rec.get('Receive Original Stock', 0)} | "
            f"安全庫存={safety} | 接收上限(2x)={target} | 累計={cum_recv}"
        )
    elif dest_type == DEST_ZERO_STOCK:
        return (
            f"【接收分析】{site}({om}) 重點補0 | "
            f"目標={target} | 累計={cum_recv} | 缺口={max(0, target - cum_recv)}"
        )
    elif dest_type == DEST_POTENTIAL_ND:
        total_sales = last + mtd
        return (
            f"【接收分析】{site}({om}) ND潛在缺貨接收 | "
            f"兩月銷量={total_sales} | 接收上限(2x)={target} | 累計={cum_recv}"
        )
    elif dest_type == DEST_CRITICAL_RESTOCK:
        return (
            f"【接收分析】{site}({om}) RF緊急缺貨補貨 | "
            f"零庫存但有銷售記錄"
        )
    elif dest_type == DEST_CRITICAL:
        return f"【接收分析】{site}({om}) 緊急缺貨補貨 | 零庫存但有銷售記錄"
    elif dest_type == DEST_POTENTIAL:
        return (
            f"【接收分析】{site}({om}) 潛在缺貨補貨 | "
            f"庫存不足,補充至Safety({safety})"
        )
    elif dest_type == DEST_SIMPLIFIED_RECV:
        return (
            f"【接收分析】{site}({om}) 精簡SKU接收 | "
            f"接收上限(Cap)={target} | 累計={cum_recv}"
        )

    return f"【接收分析】{site}({om}) {dest_type}"
