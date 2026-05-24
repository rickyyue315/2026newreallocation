from collections import defaultdict
from typing import Any


def run_quality_checks(
    recommendations: list,
    df: Any = None,
    skip_nd_check: bool = False,
) -> tuple[bool, list[str]]:
    errors = []

    transfer_sites_by_article: dict[str, set] = defaultdict(set)
    receive_sites_by_article: dict[str, set] = defaultdict(set)
    cumulative_transfer: dict[tuple, int] = defaultdict(int)
    cumulative_receive_zero: dict[tuple, int] = defaultdict(int)

    original_stocks: dict[tuple, int] = {}
    if df is not None:
        for _, row in df.iterrows():
            article = str(row.get("Article", "")).strip()
            site = str(row.get("Site", "")).strip()
            stock = int(row.get("SaSa Net Stock", 0))
            original_stocks[(article, site)] = stock
            rp_type = str(row.get("RP Type", "")).strip()
            if rp_type == "ND":
                pass

    for i, rec in enumerate(recommendations):
        article = str(rec.get("Article", ""))
        transfer_site = str(rec.get("Transfer Site", ""))
        receive_site = str(rec.get("Receive Site", ""))
        transfer_om = str(rec.get("Transfer OM", ""))
        qty = rec.get("Transfer Qty", 0)

        if not article:
            errors.append(f"[Record {i}] Article field is empty: Check 1")
            continue

        if not isinstance(qty, (int, float)) or qty <= 0:
            errors.append(f"[Record {i}, Article {article}] Transfer Qty must be positive integer: Check 2")
            continue

        qty = int(qty)

        key = (article, transfer_site)
        cumulative_transfer[key] += qty
        total_transferred = cumulative_transfer[key]

        if key in original_stocks and total_transferred > original_stocks[key]:
            errors.append(
                f"[Record {i}, Article {article}] Cumulative transfer ({total_transferred}) "
                f"exceeds original stock ({original_stocks[key]}) for {transfer_site}: Check 3"
            )

        if transfer_site == receive_site:
            errors.append(
                f"[Record {i}, Article {article}] Transfer Site ({transfer_site}) "
                f"equals Receive Site ({receive_site}): Check 4"
            )

        if len(article) != 12 or not article.isdigit():
            errors.append(
                f"[Record {i}, Article {article}] Article must be 12-digit string: Check 5"
            )

        transfer_sites_by_article[article].add(transfer_site)
        receive_sites_by_article[article].add(receive_site)

        if not skip_nd_check:
            rp_dest = None
            if df is not None:
                matches = df[df["Site"] == receive_site]
                if not matches.empty:
                    rp_dest = str(matches["RP Type"].iloc[0]).strip()
            else:
                dest_type = rec.get("Destination Type", "")
                if "ND" in dest_type:
                    rp_dest = "ND"

            if rp_dest == "ND":
                errors.append(
                    f"[Record {i}, Article {article}] ND site ({receive_site}) "
                    f"cannot be a receive destination: Check 7"
                )

        dest_type = rec.get("Destination Type", "")
        if dest_type == "重點補0":
            target_qty = rec.get("Target Qty", 0)
            cum_recv = rec.get("Cumulative Received Qty", 0)
            if target_qty > 0 and cum_recv > target_qty:
                errors.append(
                    f"[Record {i}, Article {article}] Zero-stock destination ({receive_site}) "
                    f"received {cum_recv} but target is {target_qty}: Check 8"
                )

    for article, sites in transfer_sites_by_article.items():
        if article in receive_sites_by_article:
            dual = sites & receive_sites_by_article[article]
            if dual:
                errors.append(
                    f"Article {article}: Sites with dual role (both transfer & receive): "
                    f"{', '.join(sorted(dual))}: Check 6"
                )

    passed = len(errors) == 0
    return passed, errors
