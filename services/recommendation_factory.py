from config import (
    DEST_CRITICAL,
    DEST_CRITICAL_ZERO,
    DEST_CRITICAL_RESTOCK,
    DEST_POTENTIAL,
    DEST_POTENTIAL_ND,
    DEST_ZERO_STOCK,
    DEST_F_TARGET,
    DEST_F2_TARGET,
    DEST_E_RECEIVE,
    DEST_SIMPLIFIED_RECV,
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
)


def _get_product_desc(source: dict, original_df=None) -> str:
    desc = source.get("product_desc", "")
    if desc:
        return desc

    brand = source.get("brand", "")
    article = source.get("article", "")

    if original_df is not None and article:
        matches = original_df[original_df["Article"] == article]
        if not matches.empty:
            if "Brand" in matches.columns:
                brand = str(matches["Brand"].iloc[0]) if not pd.isna else brand
            if "Article Description" in matches.columns:
                desc = str(matches["Article Description"].iloc[0])

    if not desc:
        parts = []
        if brand:
            parts.append(str(brand))
        parts.append(str(article))
        desc = " ".join(parts)
    return desc or "N/A"


def build_recommendation(
    source: dict,
    dest: dict,
    transfer_qty: int,
    mode: str,
    received_qty_by_site: dict = None,
    original_df=None,
) -> dict:
    import pandas as pd

    if transfer_qty <= 0:
        return None

    source_type = source.get("source_type", "")
    dest_type = dest.get("dest_type", "")
    article = source.get("article", "")

    product_desc = _get_product_desc(source, original_df)

    source_original_stock = source.get("original_stock", source.get("net_stock", 0))
    source_total_transferred = source.get("total_transferred", 0)
    after_transfer_stock = source_original_stock - source_total_transferred - transfer_qty

    remark = f"{source_type} -> {dest_type}"

    rec = {
        "Brand": source.get("brand", ""),
        "Article": article,
        "Product Desc": product_desc,
        "Transfer OM": source.get("om", ""),
        "Transfer Site": source.get("site", ""),
        "Receive OM": dest.get("om", ""),
        "Receive Site": dest.get("site", ""),
        "Transfer Qty": transfer_qty,
        "Transfer Original Stock": source_original_stock,
        "Transfer After Transfer Stock": max(0, after_transfer_stock),
        "Transfer Safety Stock": source.get("safety_stock", 0),
        "Transfer MOQ": source.get("moq", 0),
        "Remark": remark,
        "Notes": "",
        "Transfer Site Last Month Sold Qty": source.get("last_month_sold", 0),
        "Transfer Site MTD Sold Qty": source.get("mtd_sold", 0),
        "Receive Site Last Month Sold Qty": dest.get("last_month_sold", 0),
        "Receive Site MTD Sold Qty": dest.get("mtd_sold", 0),
        "Receive Original Stock": dest.get("net_stock", 0),
        "Source Type": source_type,
        "Destination Type": dest_type,
        "Source Priority": source.get("priority", 0),
        "Destination Priority": dest.get("priority", 0),
        "Cumulative Received Qty": received_qty_by_site.get(dest.get("site", ""), 0) if received_qty_by_site else 0,
        "Transfer RP Type": source.get("rp_type", ""),
        "Receive RP Type": dest.get("rp_type", ""),
        "Transfer Store Type": source.get("store_type", ""),
        "Receive Store Type": dest.get("store_type", ""),
    }

    target_qty = dest.get("target_qty")
    if target_qty is not None and target_qty > 0:
        rec["Target Qty"] = target_qty

    return rec


def apply_transfer(source: dict, dest: dict, transfer_qty: int, received_qty_by_site: dict = None):
    source["total_transferred"] = source.get("total_transferred", 0) + transfer_qty
    source["transferable_qty"] = max(0, source.get("transferable_qty", 0) - transfer_qty)

    dest["needed_qty"] = max(0, dest.get("needed_qty", 0) - transfer_qty)

    if received_qty_by_site is not None:
        dest_key = dest.get("site", "")
        received_qty_by_site[dest_key] = received_qty_by_site.get(dest_key, 0) + transfer_qty


def infer_source_rp_type(source_type: str) -> str:
    if "ND" in source_type:
        return "ND"
    return "RF"
