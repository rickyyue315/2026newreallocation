from config import (
    SOURCE_SIMPLIFIED_ND,
    SOURCE_SIMPLIFIED_RF,
    DEST_SIMPLIFIED_RECV,
)
from strategies.base import BaseMatchStrategy
from strategies.predicates import is_hd_to_hk_restricted


class SimplifiedSKUStrategy(BaseMatchStrategy):
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

        mode_def = logic._mode_info_cache.get(mode)
        is_cross_om = mode_def is not None and mode_def.cross_om_matching

        avail_sources = [s for s in sources if s.get("transferable_qty", 0) >= 2]
        avail_dests = [d for d in dests if d.get("needed_qty", 0) > 0]

        for dest in avail_dests:
            if dest.get("needed_qty", 0) <= 0:
                continue
            for source in avail_sources:
                if source.get("transferable_qty", 0) < 2:
                    continue
                if dest.get("needed_qty", 0) <= 0:
                    continue

                if not is_cross_om:
                    if source.get("om", "") != dest.get("om", ""):
                        continue
                else:
                    if source.get("om") == "Windy" and dest.get("om") != "Windy":
                        continue
                    if is_hd_to_hk_restricted(source.get("site", ""), dest.get("site", "")):
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
                if transfer_qty < 2:
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

        for s in avail_sources:
            if s.get("transferable_qty", 0) > 0 and s.get("site", "") not in transfer_sites:
                s["is_d001_return"] = True
                s["dest_priority_override"] = 99
                
                d001_dest = {
                    "article": article,
                    "site": "D001",
                    "om": s.get("om", ""),
                    "rp_type": "RF",
                    "net_stock": 0,
                    "pending_received": 0,
                    "safety_stock": 0,
                    "last_month_sold": 0,
                    "mtd_sold": 0,
                    "effective_sold_qty": 0,
                    "needed_qty": s.get("transferable_qty", 0),
                    "dest_type": "D001退回",
                    "priority": 99,
                    "store_type": "",
                    "brand": s.get("brand", ""),
                    "total_available": 0,
                }
                
                transfer_qty = s.get("transferable_qty", 0)
                rec = build_recommendation(s, d001_dest, transfer_qty, mode, received_qty_by_site)
                if rec:
                    rec["Remark"] = f"精簡SKU退回 -> D001退回"
                    recommendations.append(rec)
                
                apply_transfer(s, d001_dest, transfer_qty, received_qty_by_site)
                transfer_sites.add(s.get("site", ""))
                receive_sites.add("D001")

        return recommendations
