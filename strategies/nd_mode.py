from config import DEST_CRITICAL_RESTOCK, DEST_POTENTIAL_ND
from strategies.base import BaseMatchStrategy
from strategies.predicates import is_hd_to_hk_restricted


class NDModeStrategy(BaseMatchStrategy):
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

        priority_dests = sorted(dests, key=lambda d: (
            0 if d.get("dest_type") == DEST_CRITICAL_RESTOCK else 1,
            -d.get("needed_qty", 0),
        ))

        nd_sources = [s for s in sources if s.get("transferable_qty", 0) > 0]

        for dest in priority_dests:
            if dest.get("needed_qty", 0) <= 0:
                continue

            target_qty = dest.get("target_qty")
            dest_key = dest.get("site", "")
            current_received = received_qty_by_site.get(dest_key, 0)
            if target_qty and current_received >= target_qty:
                continue

            for source in nd_sources:
                if source.get("transferable_qty", 0) <= 0:
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

                current_received_qty = received_qty_by_site.get(dest_key, 0)
                transfer_qty = compute_transfer_qty(logic, source, dest, mode, current_received_qty)
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
