from collections import defaultdict
from typing import Callable, Optional


def get_record_sales_total(rec: dict, prefix: str = "Transfer") -> int:
    return int(rec.get(f"{prefix} Site Last Month Sold Qty", 0)) + int(
        rec.get(f"{prefix} Site MTD Sold Qty", 0)
    )


def optimize_single_piece_transfers(
    recommendations: list,
    mode: str,
    create_note_fn: Optional[Callable] = None,
) -> list:
    if not recommendations:
        return recommendations

    groups: dict[tuple, list] = defaultdict(list)
    for idx, rec in enumerate(recommendations):
        key = (rec.get("Article", ""), rec.get("Transfer Site", ""), rec.get("Transfer OM", ""))
        groups[key].append((idx, rec))

    for key, items in groups.items():
        if len(items) <= 1:
            continue

        iterations = 0
        while iterations < 50:
            iterations += 1
            single_items = [(i, r) for i, r in items if r.get("Transfer Qty", 0) == 1]
            if not single_items:
                break

            single_idx, single_rec = single_items[0]
            single_sales = get_record_sales_total(single_rec, "Transfer")

            donor = None
            donor_idx = None
            for i, r in items:
                if r.get("Transfer Qty", 0) >= 3 and i != single_idx:
                    if donor is None or r.get("Transfer Qty", 0) > donor.get("Transfer Qty", 0):
                        donor = r
                        donor_idx = i
                    elif donor and r.get("Transfer Qty", 0) == donor.get("Transfer Qty", 0):
                        if get_record_sales_total(r, "Receive") > get_record_sales_total(donor, "Receive"):
                            donor = r
                            donor_idx = i

            if donor is not None:
                donor["Transfer Qty"] = donor["Transfer Qty"] - 1
                single_rec["Transfer Qty"] = 2
                continue

            merge_target = None
            merge_idx = None
            for i, r in items:
                if r.get("Transfer Qty", 0) >= 2 and i != single_idx:
                    if merge_target is None or get_record_sales_total(r, "Receive") > get_record_sales_total(merge_target, "Receive"):
                        merge_target = r
                        merge_idx = i
                    elif (
                        merge_target
                        and get_record_sales_total(r, "Receive") == get_record_sales_total(merge_target, "Receive")
                        and r.get("Transfer Qty", 0) > merge_target.get("Transfer Qty", 0)
                    ):
                        merge_target = r
                        merge_idx = i

            if merge_target is not None:
                if len(items) == 2 or single_sales <= get_record_sales_total(merge_target, "Receive"):
                    merge_target["Transfer Qty"] = merge_target["Transfer Qty"] + 1
                    single_rec["Transfer Qty"] = 0
                    continue
                elif len(items) >= 3:
                    best_donor = None
                    best_donor_idx = None
                    for i, r in items:
                        if r.get("Transfer Qty", 0) >= 2 and i != single_idx:
                            if best_donor is None or r.get("Transfer Qty", 0) > best_donor.get("Transfer Qty", 0):
                                best_donor = r
                                best_donor_idx = i
                    if best_donor is not None:
                        best_donor["Transfer Qty"] = best_donor["Transfer Qty"] - 1
                        single_rec["Transfer Qty"] = 2
                        continue

            break

    result = [r for _, r in list(groups.values())[0] if groups is not None]
    result = []
    for key, items in groups.items():
        for _, rec in items:
            if rec.get("Transfer Qty", 0) > 0:
                result.append(rec)

    result = refresh_recommendation_fields(result, mode, create_note_fn)
    return result


def refresh_recommendation_fields(
    recommendations: list,
    mode: str,
    create_note_fn: Optional[Callable] = None,
) -> list:
    source_running: dict[tuple, int] = defaultdict(int)
    receive_running: dict[tuple, int] = defaultdict(int)

    for rec in recommendations:
        article = rec.get("Article", "")
        transfer_site = rec.get("Transfer Site", "")
        transfer_om = rec.get("Transfer OM", "")
        receive_site = rec.get("Receive Site", "")
        qty = rec.get("Transfer Qty", 0)

        source_key = (article, transfer_site, transfer_om)
        source_running[source_key] += qty

        original_stock = rec.get("Transfer Original Stock", 0)
        after_stock = max(0, original_stock - source_running[source_key])
        rec["Transfer After Transfer Stock"] = after_stock

        receive_key = (article, receive_site)
        receive_running[receive_key] += qty
        rec["Cumulative Received Qty"] = receive_running[receive_key]

        if create_note_fn:
            rec["Notes"] = create_note_fn(rec)

    return recommendations
