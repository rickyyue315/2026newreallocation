from typing import Optional

from config import (
    SOURCE_ND,
    SOURCE_ND_CLEARANCE,
    SOURCE_RF_SURPLUS,
    SOURCE_RF_ENHANCED,
    DEST_ZERO_STOCK,
    A_MODE_PERCENTAGE_CAP,
    A_MODE_MIN_TRANSFER,
)
from strategies.predicates import is_hd_to_hk_restricted


def _clamp_target_qty(transfer_qty: int, dest: dict, current_received: int) -> int:
    target_qty = dest.get("target_qty")
    dest_type = dest.get("dest_type", "")
    if target_qty and target_qty > 0:
        needs_clamp = (
            dest_type == DEST_ZERO_STOCK
            or dest.get("is_b_special_dest", False)
            or dest.get("is_d_family", False)
        )
        if needs_clamp:
            space = max(0, int(target_qty) - current_received)
            return min(transfer_qty, space)
    return transfer_qty


def _adjust_d_family_remainder(transfer_qty: int, source: dict, dest: dict) -> int:
    if source.get("source_type") != SOURCE_ND_CLEARANCE:
        return transfer_qty

    current_transferred = source.get("total_transferred", 0)
    transferable = source.get("transferable_qty", 0)
    total_available_pre = current_transferred + transferable
    remaining = total_available_pre - current_transferred - transfer_qty

    if remaining == 1:
        if transferable >= transfer_qty + 1:
            return transfer_qty + 1
        elif transfer_qty > 1:
            return transfer_qty - 1
    return transfer_qty


def compute_transfer_qty(
    logic,
    source: dict,
    dest: dict,
    mode: str,
    current_received_qty: int = 0,
) -> int:
    transferable = source.get("transferable_qty", 0)
    needed = dest.get("needed_qty", 0)
    if transferable <= 0 or needed <= 0:
        return 0

    transfer_qty = min(transferable, needed)

    transfer_qty = _clamp_target_qty(transfer_qty, dest, current_received_qty)

    transfer_qty = _adjust_d_family_remainder(transfer_qty, source, dest)

    source_type = source.get("source_type", "")
    single_piece_types = {
        SOURCE_ND,
        SOURCE_ND_CLEARANCE,
        SOURCE_RF_ENHANCED,
        SOURCE_RF_SURPLUS,
    }
    if transfer_qty == 1 and source_type in single_piece_types and transferable >= 2:
        if dest.get("needed_qty", 0) >= 2:
            transfer_qty = 2
        elif mode == "A" and source_type == SOURCE_RF_SURPLUS:
            transfer_qty = 2

    if source_type == SOURCE_ND_CLEARANCE and transfer_qty == 1 and transferable >= 3:
        remaining_after = transferable - 3
        if remaining_after == 1:
            transfer_qty = 3

    transfer_qty = _clamp_target_qty(transfer_qty, dest, current_received_qty)
    transfer_qty = _adjust_d_family_remainder(transfer_qty, source, dest)

    return max(transfer_qty, 0)


def can_transfer(
    logic,
    source: dict,
    dest: dict,
    mode: str,
    article: str,
    transfer_sites: set,
    receive_sites: set,
    matched_sites: set,
    receive_site_limit: Optional[int],
    received_qty_by_site: dict,
    skip_cross_om_for_b3: bool = False,
) -> bool:
    if source.get("site") == dest.get("site"):
        return False

    if dest.get("site") in transfer_sites:
        return False

    if source.get("site") in receive_sites:
        return False

    mode_def = logic._mode_info_cache.get(mode)
    skip_nd = mode_def and "nd_transfer" in mode_def.families if mode_def else False
    skip_f = mode in ("F", "F2")
    if dest.get("rp_type") == "ND":
        if not skip_nd and not skip_f:
            return False

    if receive_site_limit is not None and receive_site_limit > 0:
        dest_site = dest.get("site", "")
        if len(matched_sites) >= receive_site_limit and dest_site not in matched_sites:
            return False

    is_cross_om = source.get("om", "") != dest.get("om", "")

    if mode_def and "b3_family" in mode_def.families:
        if source.get("om", "") == "Windy" and dest.get("om", "") != "Windy":
            return False
        if is_hd_to_hk_restricted(source.get("site", ""), dest.get("site", "")):
            return False

    if is_cross_om and not (mode_def and "b3_family" in mode_def.families if mode_def else False):
        if is_hd_to_hk_restricted(source.get("site", ""), dest.get("site", "")):
            return False
        if source.get("om", "") == "Windy" and dest.get("om", "") != "Windy":
            return False

    if mode_def and "b_special" in mode_def.families if mode_def else False:
        if source.get("store_type") == "M" and dest.get("store_type") in ("T", "M"):
            source_sales = source.get("last_month_sold", 0) + source.get("mtd_sold", 0)
            dest_sales = dest.get("last_month_sold", 0) + dest.get("mtd_sold", 0)
            if source_sales > dest_sales:
                return False

    target_qty = dest.get("target_qty")
    if target_qty and target_qty > 0:
        dest_type = dest.get("dest_type", "")
        needs_receive_cap = (
            dest_type == DEST_ZERO_STOCK
            or dest.get("is_b_special_dest", False)
            or dest.get("is_d_family", False)
        )
        if needs_receive_cap:
            dest_key = dest.get("site", "")
            current_received = received_qty_by_site.get(dest_key, 0)
            if current_received >= int(target_qty):
                return False

    return True


def _mark_dest_saturated(dest: dict, received_qty_by_site: dict):
    target_qty = dest.get("target_qty")
    if target_qty and target_qty > 0:
        dest_key = dest.get("site", "")
        current_received = received_qty_by_site.get(dest_key, 0)
        if current_received >= target_qty:
            dest["needed_qty"] = 0


def match_by_priority(
    logic,
    sources: list,
    dests: list,
    recommendations: list,
    mode: str,
    article: str,
    source_priority: int,
    dest_priority: int,
    transfer_sites: set,
    receive_sites: set,
    source_to_receive_sites: dict,
    received_qty_by_site: dict,
    matched_sites: set,
    receive_site_limit: Optional[int],
    source_type_filter: Optional[str] = None,
    dest_type_filter: Optional[str] = None,
    is_c1_mode: bool = False,
) -> list:
    from services.recommendation_factory import build_recommendation, apply_transfer

    priority_sources = [
        s
        for s in sources
        if s.get("priority") == source_priority and s.get("transferable_qty", 0) > 0
    ]
    if source_type_filter:
        priority_sources = [s for s in priority_sources if s.get("source_type") == source_type_filter]

    if is_c1_mode:
        priority_sources.sort(key=lambda x: (-x.get("transferable_qty", 0), x.get("effective_sold_qty", 0)))
    elif priority_sources and "c1_priority_sort" in str(source_type_filter):
        priority_sources.sort(key=lambda x: -x.get("transferable_qty", 0))

    priority_dests = [
        d
        for d in dests
        if d.get("priority") == dest_priority and d.get("needed_qty", 0) > 0
    ]
    if dest_type_filter:
        priority_dests = [d for d in priority_dests if d.get("dest_type") == dest_type_filter]

    for source in priority_sources:
        if source.get("transferable_qty", 0) <= 0:
            continue
        for dest in priority_dests:
            if dest.get("needed_qty", 0) <= 0:
                continue
            if dest_type_filter and dest.get("dest_type") != dest_type_filter:
                continue

            if not can_transfer(
                logic, source, dest, mode, article,
                transfer_sites, receive_sites, matched_sites,
                receive_site_limit, received_qty_by_site,
            ):
                continue

            current_dest_received = received_qty_by_site.get(dest.get("site", ""), 0)
            transfer_qty = compute_transfer_qty(logic, source, dest, mode, current_dest_received)

            if transfer_qty <= 0:
                continue

            rec = build_recommendation(source, dest, transfer_qty, mode, received_qty_by_site)
            if rec:
                recommendations.append(rec)

            apply_transfer(source, dest, transfer_qty, received_qty_by_site)
            transfer_sites.add(source.get("site", ""))
            receive_sites.add(dest.get("site", ""))
            matched_sites.add(dest.get("site", ""))

            source_key = source.get("site", "")
            if source_key not in source_to_receive_sites:
                source_to_receive_sites[source_key] = set()
            source_to_receive_sites[source_key].add(dest.get("site", ""))

            _mark_dest_saturated(dest, received_qty_by_site)

    return recommendations


def prep_temp_lists(sources: list, dests: list) -> tuple[list, list]:
    temp_sources = []
    for s in sources:
        temp = dict(s)
        temp["total_transferred"] = temp.get("total_transferred", 0)
        temp_sources.append(temp)

    temp_dests = [d.copy() for d in dests]
    return temp_sources, temp_dests


def match_general_mode(
    logic,
    sources: list,
    dests: list,
    recommendations: list,
    mode: str,
    article: str,
    transfer_sites: set,
    receive_sites: set,
    source_to_receive_sites: dict,
    received_qty_by_site: dict,
    matched_sites: set,
    receive_site_limit: Optional[int],
) -> list:
    from config import (
        SOURCE_ND_PRIORITY,
        SOURCE_RF_PRIORITY,
        DEST_CRITICAL_PRIORITY,
        DEST_POTENTIAL_PRIORITY,
        DEST_ZERO_STOCK_PRIORITY,
    )

    temp_sources, temp_dests = prep_temp_lists(sources, dests)

    if mode == "C":
        rounds = [
            (SOURCE_ND_PRIORITY, DEST_ZERO_STOCK_PRIORITY, None, DEST_ZERO_STOCK),
            (SOURCE_ND_PRIORITY, DEST_CRITICAL_PRIORITY, None, None),
            (SOURCE_ND_PRIORITY, DEST_POTENTIAL_PRIORITY, None, None),
            (SOURCE_RF_PRIORITY, DEST_ZERO_STOCK_PRIORITY, SOURCE_RF_SURPLUS, DEST_ZERO_STOCK),
            (SOURCE_RF_PRIORITY, DEST_CRITICAL_PRIORITY, SOURCE_RF_SURPLUS, None),
            (SOURCE_RF_PRIORITY, DEST_POTENTIAL_PRIORITY, SOURCE_RF_SURPLUS, None),
            (SOURCE_RF_PRIORITY, DEST_ZERO_STOCK_PRIORITY, SOURCE_RF_ENHANCED, DEST_ZERO_STOCK),
            (SOURCE_RF_PRIORITY, DEST_CRITICAL_PRIORITY, SOURCE_RF_ENHANCED, None),
            (SOURCE_RF_PRIORITY, DEST_POTENTIAL_PRIORITY, SOURCE_RF_ENHANCED, None),
        ]
    elif mode == "C1":
        rounds = [
            (SOURCE_ND_PRIORITY, DEST_CRITICAL_PRIORITY, None, None),
            (SOURCE_RF_PRIORITY, DEST_ZERO_STOCK_PRIORITY, SOURCE_RF_SURPLUS, DEST_ZERO_STOCK),
            (SOURCE_RF_PRIORITY, DEST_ZERO_STOCK_PRIORITY, SOURCE_RF_ENHANCED, DEST_ZERO_STOCK),
        ]
    else:
        rounds = [
            (SOURCE_ND_PRIORITY, DEST_CRITICAL_PRIORITY, None, None),
            (SOURCE_ND_PRIORITY, DEST_POTENTIAL_PRIORITY, None, None),
            (SOURCE_RF_PRIORITY, DEST_CRITICAL_PRIORITY, SOURCE_RF_SURPLUS, None),
            (SOURCE_RF_PRIORITY, DEST_POTENTIAL_PRIORITY, SOURCE_RF_SURPLUS, None),
            (SOURCE_RF_PRIORITY, DEST_CRITICAL_PRIORITY, SOURCE_RF_ENHANCED, None),
            (SOURCE_RF_PRIORITY, DEST_POTENTIAL_PRIORITY, SOURCE_RF_ENHANCED, None),
        ]

    for src_p, dst_p, src_filter, dst_filter in rounds:
        match_by_priority(
            logic, temp_sources, temp_dests, recommendations, mode, article,
            src_p, dst_p, transfer_sites, receive_sites,
            source_to_receive_sites, received_qty_by_site, matched_sites,
            receive_site_limit,
            source_type_filter=src_filter,
            dest_type_filter=dst_filter,
            is_c1_mode=(mode == "C1"),
        )

    return recommendations
