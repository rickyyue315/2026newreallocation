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
    A_MODE_PERCENTAGE_CAP,
    B_MODE_PERCENTAGE_CAP,
    C_MODE_PERCENTAGE_CAP,
    C_MODE_ABS_CAP,
    SAFETY_RECEIVE_MULTIPLIER,
    MIN_RECEIVE_FLOOR,
)


def create_recommendation_note(rec: dict) -> str:
    return " | ".join(filter(None, [
        _note_source_analysis(rec),
        _note_dest_analysis(rec),
        _note_transfer_summary(rec),
    ]))


def _note_source_analysis(rec: dict) -> str:
    source_type = rec.get("Source Type", "")
    site = rec.get("Transfer Site", "")
    om = rec.get("Transfer OM", "")
    original = rec.get("Transfer Original Stock", 0)
    after = rec.get("Transfer After Transfer Stock", 0)
    safety = rec.get("Transfer Safety Stock", 0)
    last = rec.get("Transfer Site Last Month Sold Qty", 0)
    mtd = rec.get("Transfer Site MTD Sold Qty", 0)
    store_type = rec.get("Transfer Store Type", "")
    qty = rec.get("Transfer Qty", 0)
    rp_type = rec.get("Transfer RP Type", "")
    total_sales = last + mtd
    total_avail = original  # net stock at decision time

    # Shared prefix
    prefix = f"【轉出】{site}({om})"

    if source_type == SOURCE_ND_SMART:
        return (
            f"{prefix} ND智能轉出 | "
            f"無銷量優先 (銷量={total_sales}) | "
            f"預計轉出={qty}件 | "
            f"原始庫存={original} → 轉後={after}"
        )

    elif source_type == SOURCE_ND:
        return (
            f"{prefix} ND轉出 (RP={rp_type}) | "
            f"不設庫存上限,全額轉出 | "
            f"庫存={original}件"
        )

    elif source_type == SOURCE_ND_F_MODE:
        return (
            f"{prefix} F模式ND轉出 | "
            f"非Target店舖,庫存全額釋出 | "
            f"庫存={original}件"
        )

    elif source_type == SOURCE_ND_CLEARANCE:
        return (
            f"{prefix} ND清貨轉出 | "
            f"無銷售紀錄 (LastMonth={last}) | "
            f"倉庫庫存不佔用,全數釋出 | "
            f"原始庫存={original} → 轉後={after}"
        )

    elif source_type == SOURCE_RF_F_MODE:
        return (
            f"{prefix} F模式RF轉出 | "
            f"非Target店舖,可忽視安全庫存 | "
            f"原始庫存={original} → 轉後={after}"
        )

    elif source_type == SOURCE_E_MANDATORY:
        return (
            f"{prefix} E模式強制轉出 (ALL標記) | "
            f"RP={rp_type} | "
            f"強制釋放全部庫存={original}件 → 轉後={after}"
        )

    elif source_type == SOURCE_LOCAL_FULL:
        return (
            f"{prefix} L型店舖全轉出 | "
            f"Type={store_type},低銷量 (兩月={total_sales}) | "
            f"只保留2件/可全轉 | "
            f"原始庫存={original} → 轉後={after}"
        )

    elif SOURCE_RF_SURPLUS in source_type:
        # Determine which cap was used based on the mode context
        # For surplus: remaining >= safety
        remaining = after
        return (
            f"{prefix} RF過剩轉出 | "
            f"庫存={original} > 安全庫存={safety} | "
            f"安全店,轉後仍保有≥安全庫存 | "
            f"轉出={qty}件 → 轉後={remaining} (安全={safety})"
        )

    elif SOURCE_RF_ENHANCED in source_type:
        remaining = after
        return (
            f"{prefix} RF加強轉出 | "
            f"庫存={original},安全庫存={safety} | "
            f"轉後可能低於安全庫存 | "
            f"轉出={qty}件 → 轉後={remaining} (安全={safety})"
        )

    elif source_type == SOURCE_SIMPLIFIED_ND:
        return (
            f"{prefix} 精簡SKU ND轉出 | "
            f"全數可釋放={original}件"
        )

    elif source_type == SOURCE_SIMPLIFIED_RF:
        return (
            f"{prefix} 精簡SKU RF轉出 | "
            f"超出Cap部分釋出 | "
            f"兩月銷量={total_sales} | "
            f"庫存={original} → 轉後={after}"
        )

    return f"{prefix} 轉出原因={source_type} | 庫存={original} → {after}"


def _note_dest_analysis(rec: dict) -> str:
    dest_type = rec.get("Destination Type", "")
    site = rec.get("Receive Site", "")
    om = rec.get("Receive OM", "")
    original = rec.get("Receive Original Stock", 0)
    target = rec.get("Target Qty", 0)
    cum_recv = rec.get("Cumulative Received Qty", 0)
    qty = rec.get("Transfer Qty", 0)
    last = rec.get("Receive Site Last Month Sold Qty", 0)
    mtd = rec.get("Receive Site MTD Sold Qty", 0)
    total_sales = last + mtd
    rp_type = rec.get("Receive RP Type", "")
    store_type = rec.get("Receive Store Type", "")

    prefix = f"【接收】{site}({om})"

    if dest_type in (DEST_F_TARGET, DEST_F2_TARGET):
        return (
            f"{prefix} Target店目標接收 | "
            f"目標={target}件 | "
            f"已收={cum_recv} | "
            f"缺口={max(0, target - cum_recv)} | "
            f"本次補={qty}件 "
            f"({ '已達標' if cum_recv >= target else '持續補貨' })"
        )

    elif dest_type == DEST_E_RECEIVE or "E1b" in dest_type:
        cap = target or (safety := rec.get("Transfer Safety Stock", 0) * SAFETY_RECEIVE_MULTIPLIER)
        cap = max(cap, MIN_RECEIVE_FLOOR)
        return (
            f"{prefix} E模式接收 (Type={store_type}) | "
            f"原始庫存={original} | "
            f"安全庫存={rec.get('Transfer Safety Stock', 0)} | "
            f"接收上限(2x)={target} | "
            f"本次補={qty}件 | 累計={cum_recv}"
        )

    elif dest_type == DEST_ZERO_STOCK:
        return (
            f"{prefix} 重點補0 (零庫存補貨) | "
            f"原始庫存≈0 | "
            f"目標={target}件 | "
            f"已收={cum_recv} | "
            f"本次補={qty}件 | "
            f"剩餘缺口={max(0, target - cum_recv)}"
        )

    elif dest_type == DEST_POTENTIAL_ND:
        return (
            f"{prefix} ND潛在缺貨接收 | "
            f"兩月銷量={total_sales} | "
            f"接收上限(2x銷量)={target} | "
            f"累計={cum_recv} | 本次補={qty}件"
        )

    elif dest_type == DEST_CRITICAL_RESTOCK:
        return (
            f"{prefix} RF緊急缺貨補貨 | "
            f"零庫存 但有銷售紀錄 (LastMonth={last}) | "
            f"緊急:缺貨中斷銷售 | "
            f"本次補={qty}件 | 累計={cum_recv}"
        )

    elif dest_type == DEST_CRITICAL:
        return (
            f"{prefix} 緊急缺貨補貨 | "
            f"零庫存 且上月有銷售={last} | "
            f"需立即補貨避免斷貨 | "
            f"本次補={qty}件"
        )

    elif dest_type == DEST_POTENTIAL:
        gap = target or 0
        return (
            f"{prefix} 潛在缺貨補貨 | "
            f"庫存不足安全庫存 | "
            f"原始庫存={original} < 安全庫存={rec.get('Transfer Safety Stock', 0)} | "
            f"本次補={qty}件"
        )

    elif dest_type == DEST_SIMPLIFIED_RECV:
        return (
            f"{prefix} 精簡SKU接收 | "
            f"原始庫存不足Cap={target} | "
            f"本次補={qty}件 | "
            f"累計={cum_recv}"
        )

    return f"{prefix} 接收原因={dest_type} | 補貨={qty}件(累計={cum_recv})"


def _note_transfer_summary(rec: dict) -> str:
    qty = rec.get("Transfer Qty", 0)
    article = rec.get("Article", "")
    from_site = rec.get("Transfer Site", "")
    to_site = rec.get("Receive Site", "")

    mode = rec.get("Remark", "")
    return f"【調撥】{article} {from_site}→{to_site} {qty}件 ({mode})"
