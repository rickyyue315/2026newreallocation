from config import DEST_ZERO_STOCK
from strategies.base import BaseMatchStrategy
from strategies.predicates import is_hd_to_hk_restricted


class C2ModeStrategy(BaseMatchStrategy):
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

        priority_dests = [
            d for d in dests
            if d.get("dest_type") == DEST_ZERO_STOCK and d.get("needed_qty", 0) > 0
        ]
        priority_dests.sort(key=lambda d: -d.get("needed_qty", 0))

        priority_sources = [
            s for s in sources if s.get("transferable_qty", 0) > 0
        ]

        for dest in priority_dests:
            if dest.get("needed_qty", 0) <= 0:
                continue
            for source in priority_sources:
                if source.get("transferable_qty", 0) <= 0:
                    continue

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
