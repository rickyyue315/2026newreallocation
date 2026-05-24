from config import (
    SOURCE_ND,
    SOURCE_RF_SURPLUS,
    SOURCE_RF_ENHANCED,
    SOURCE_LOCAL_FULL,
    SOURCE_ND_PRIORITY,
    SOURCE_RF_PRIORITY,
    DEST_CRITICAL_PRIORITY,
    DEST_POTENTIAL_PRIORITY,
)
from strategies.base import BaseMatchStrategy
from strategies.predicates import is_hd_to_hk_restricted


class BSpecialStrategy(BaseMatchStrategy):
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
        is_b3_family = mode_def is not None and "b3_family" in mode_def.families

        rounds = [
            (SOURCE_ND_PRIORITY, DEST_CRITICAL_PRIORITY, None),
            (SOURCE_ND_PRIORITY, DEST_POTENTIAL_PRIORITY, None),
            (SOURCE_RF_PRIORITY, DEST_CRITICAL_PRIORITY, SOURCE_RF_SURPLUS),
            (SOURCE_RF_PRIORITY, DEST_POTENTIAL_PRIORITY, SOURCE_RF_SURPLUS),
            (SOURCE_RF_PRIORITY, DEST_CRITICAL_PRIORITY, SOURCE_LOCAL_FULL),
            (SOURCE_RF_PRIORITY, DEST_POTENTIAL_PRIORITY, SOURCE_LOCAL_FULL),
            (SOURCE_RF_PRIORITY, DEST_CRITICAL_PRIORITY, SOURCE_RF_ENHANCED),
            (SOURCE_RF_PRIORITY, DEST_POTENTIAL_PRIORITY, SOURCE_RF_ENHANCED),
        ]

        for source_priority, dest_priority, source_type_filter in rounds:
            priority_sources = [
                s
                for s in sources
                if s.get("priority") == source_priority
                and s.get("transferable_qty", 0) > 0
            ]
            if source_type_filter:
                priority_sources = [
                    s for s in priority_sources if s.get("source_type") == source_type_filter
                ]

            priority_dests = [
                d
                for d in dests
                if d.get("priority") == dest_priority and d.get("needed_qty", 0) > 0
            ]

            for source in priority_sources:
                if source.get("transferable_qty", 0) <= 0:
                    continue
                for dest in priority_dests:
                    if dest.get("needed_qty", 0) <= 0:
                        continue

                    can = can_transfer(
                        logic, source, dest, mode, article,
                        transfer_sites, receive_sites, matched_sites,
                        receive_site_limit, received_qty_by_site,
                        skip_cross_om_for_b3=is_b3_family,
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

        return recommendations
