from config import DEST_F_TARGET, DEST_F2_TARGET, DEST_ZERO_STOCK
from strategies.base import BaseMatchStrategy
from strategies.predicates import is_hd_to_hk_restricted


class FModeStrategy(BaseMatchStrategy):
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

        f2_hd_transfer = kwargs.get("f2_hd_transfer", False)

        p1_dests = [d for d in dests if d.get("needed_qty", 0) > 0 and d.get("dest_type", "").startswith("F")]
        p1_dests.sort(key=lambda d: -d.get("needed_qty", 0))

        p1_sources = [s for s in sources if s.get("transferable_qty", 0) > 0]
        p1_sources.sort(key=lambda s: self._sort_key(s, p1_dests, f2_hd_transfer=mode == "F2" and f2_hd_transfer))

        for dest in p1_dests:
            if dest.get("needed_qty", 0) <= 0:
                continue
            for source in p1_sources:
                if source.get("transferable_qty", 0) <= 0:
                    continue
                if dest.get("site", "") in transfer_sites:
                    continue

                if source.get("om") == "Windy" and dest.get("om") != "Windy":
                    continue
                if not (mode == "F2" and f2_hd_transfer):
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

        if mode == "F2":
            return recommendations

        p2_dests = [
            d for d in dests
            if d.get("dest_type") == DEST_ZERO_STOCK and d.get("needed_qty", 0) > 0
        ]

        p2_sources = [
            s for s in sources if s.get("transferable_qty", 0) > 0
        ]

        for source in p2_sources:
            if source.get("transferable_qty", 0) <= 0:
                continue
            for dest in p2_dests:
                if dest.get("needed_qty", 0) <= 0:
                    continue
                if source.get("om", "") != dest.get("om", ""):
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

    def _sort_key(self, source: dict, dests: list, f2_hd_transfer: bool = False):
        same_om_bonus = 0
        om = source.get("om", "")

        dest_oms_in_p1 = set(d.get("om", "") for d in dests if d.get("needed_qty", 0) > 0)
        same_om = 0 if om in dest_oms_in_p1 else 10

        nd_bonus = 0 if source.get("rp_type") == "ND" else 1

        hd_penalty = 0
        if f2_hd_transfer and source.get("site", "").upper().startswith("HD"):
            non_hk = True
            for d in dests:
                if d.get("site", "").upper().startswith(("HA", "HB", "HC")):
                    continue
            hd_penalty = 10

        windy_penalty = 0
        if om == "Windy":
            target_is_windy = any(
                d.get("om", "") == "Windy" for d in dests
            )
            if not target_is_windy:
                windy_penalty = 5

        return (same_om, nd_bonus, hd_penalty, windy_penalty, -source.get("effective_sold_qty", 0))
