from config import (
    SOURCE_E_MANDATORY,
    DEST_ZERO_STOCK,
    C_MODE_PERCENTAGE_CAP,
    C_MODE_ABS_CAP,
)
from strategies.base import BaseMatchStrategy
from strategies.predicates import is_hd_to_hk_restricted


class E2ModeStrategy(BaseMatchStrategy):
    def match(
        self,
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
        receive_site_limit=None,
        **kwargs,
    ) -> list:
        from services.matching_engine import can_transfer, compute_transfer_qty, _mark_dest_saturated
        from services.recommendation_factory import build_recommendation, apply_transfer

        e_sources = [
            s for s in sources
            if s.get("source_type") == SOURCE_E_MANDATORY
            and s.get("transferable_qty", 0) > 0
        ]

        e_dests = [
            d for d in dests
            if d.get("needed_qty", 0) > 0
        ]

        for source in e_sources:
            if source.get("transferable_qty", 0) <= 0:
                continue
            for dest in e_dests:
                if dest.get("needed_qty", 0) <= 0:
                    continue
                if source.get("om", "") != dest.get("om", ""):
                    continue

                if is_hd_to_hk_restricted(source.get("site", ""), dest.get("site", "")):
                    continue
                if source.get("om", "") == "Windy" and dest.get("om", "") != "Windy":
                    continue

                can = can_transfer(
                    logic, source, dest, mode, article,
                    transfer_sites, receive_sites, matched_sites,
                    receive_site_limit, received_qty_by_site,
                )
                if not can:
                    continue

                current_received = received_qty_by_site.get(dest.get("site", ""), 0)
                transfer_qty = compute_transfer_qty(logic, source, dest, mode, current_received)
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

        for source in e_sources:
            if source.get("transferable_qty", 0) <= 0:
                continue
            for dest in e_dests:
                if dest.get("needed_qty", 0) <= 0:
                    continue
                if source.get("om", "") == dest.get("om", ""):
                    continue

                if is_hd_to_hk_restricted(source.get("site", ""), dest.get("site", "")):
                    continue
                if source.get("om", "") == "Windy" and dest.get("om", "") != "Windy":
                    continue

                can = can_transfer(
                    logic, source, dest, mode, article,
                    transfer_sites, receive_sites, matched_sites,
                    receive_site_limit, received_qty_by_site,
                )
                if not can:
                    continue

                current_received = received_qty_by_site.get(dest.get("site", ""), 0)
                transfer_qty = compute_transfer_qty(logic, source, dest, mode, current_received)
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

        unfulfilled_dests = [d for d in e_dests if d.get("needed_qty", 0) > 0]
        if not unfulfilled_dests:
            return recommendations

        e_mode_source_oms = set()
        for s in e_sources:
            e_mode_source_oms.add(s.get("om", ""))

        c_fallback_dests = [
            d for d in unfulfilled_dests
            if d.get("om", "") not in e_mode_source_oms
        ]
        if not c_fallback_dests:
            return recommendations

        c_sources = [
            s for s in sources
            if s.get("source_type") != SOURCE_E_MANDATORY
            and s.get("rp_type") == "RF"
            and s.get("transferable_qty", 0) <= 0
        ]

        for s in c_sources:
            site = s.get("site", "")
            if site in transfer_sites or site in receive_sites:
                continue
            net_stock = s.get("net_stock", 0)
            total_avail = s.get("total_available", s.get("net_stock", 0))
            safety = s.get("safety_stock", 0)

            if total_avail <= safety:
                continue

            base = total_avail - safety
            cap = max(int(total_avail * C_MODE_PERCENTAGE_CAP), 1)
            abs_cap = C_MODE_ABS_CAP
            transferable = max(1, int(min(base, cap, abs_cap, net_stock)))

            if transferable <= 0:
                continue

            s["transferable_qty"] = transferable
            s["source_type"] = SOURCE_SURPLUS_C_FALLBACK

        from config import SOURCE_RF_SURPLUS, SOURCE_RF_ENHANCED
        SOURCE_SURPLUS_C_FALLBACK = "RF過剩轉出(C模式回退)"
        SOURCE_ENHANCED_C_FALLBACK = "RF加強轉出(C模式回退)"

        c_sources = [
            s for s in sources
            if s.get("transferable_qty", 0) > 0 and s.get("source_type", "").endswith("(C模式回退)")
        ]

        for source in c_sources:
            if source.get("transferable_qty", 0) <= 0:
                continue
            for dest in c_fallback_dests:
                if dest.get("needed_qty", 0) <= 0:
                    continue
                if source.get("site", "") == dest.get("site", ""):
                    continue
                if source.get("site", "") in transfer_sites:
                    continue
                if dest.get("site", "") in receive_sites:
                    continue
                if dest.get("rp_type") == "ND":
                    continue

                if is_hd_to_hk_restricted(source.get("site", ""), dest.get("site", "")):
                    continue
                if source.get("om", "") == "Windy" and dest.get("om", "") != "Windy":
                    continue

                current_received = received_qty_by_site.get(dest.get("site", ""), 0)
                transfer_qty = min(source.get("transferable_qty", 0), dest.get("needed_qty", 0))
                transfer_qty = max(transfer_qty, 0)
                if transfer_qty <= 0:
                    continue

                remaining = source.get("net_stock", 0) - source.get("total_transferred", 0) - transfer_qty
                if remaining <= safety:
                    source_type = SOURCE_ENHANCED_C_FALLBACK
                else:
                    source_type = SOURCE_SURPLUS_C_FALLBACK

                rec = build_recommendation(source, dest, transfer_qty, mode, received_qty_by_site)
                if rec:
                    rec["Source Type"] = source_type
                    rec["Remark"] = f"{source_type} -> {dest.get('dest_type', '')}"
                    recommendations.append(rec)

                apply_transfer(source, dest, transfer_qty, received_qty_by_site)
                transfer_sites.add(source.get("site", ""))
                receive_sites.add(dest.get("site", ""))

                source_key = source.get("site", "")
                if source_key not in source_to_receive_sites:
                    source_to_receive_sites[source_key] = set()
                source_to_receive_sites[source_key].add(dest.get("site", ""))

        return recommendations
