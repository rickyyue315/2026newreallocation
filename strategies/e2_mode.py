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
        group_df=None,
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

        if group_df is None:
            return recommendations

        e_mode_source_sites = set(s.get("site", "") for s in e_sources)

        from services.matching_engine import _clamp_target_qty, _adjust_d_family_remainder
        from config import SOURCE_RF_SURPLUS_C_FALLBACK, SOURCE_RF_ENHANCED_C_FALLBACK

        c_sources = []
        max_protected = logic._compute_max_protected_sold(group_df, om_col=False) if hasattr(logic, '_compute_max_protected_sold') else float("inf")

        for _, row in group_df.iterrows():
            rp = str(row.get("RP Type", "")).strip()
            if rp != "RF":
                continue

            site = str(row.get("Site", "")).strip()
            if site in e_mode_source_sites:
                continue
            if site in transfer_sites or site in receive_sites:
                continue

            net_stock = int(row.get("SaSa Net Stock", 0))
            if net_stock <= 0:
                continue

            pending = int(row.get("Pending Received", 0))
            total_avail = net_stock + pending
            safety = int(row.get("Safety Stock", 0))
            last_month = int(row.get("Last Month Sold Qty", 0))
            mtd = int(row.get("MTD Sold Qty", 0))
            eff_sold = int(row.get("Effective Sold Qty", 0))
            om = str(row.get("OM", "")).strip()
            store_type = str(row.get("Type", "")).strip().upper() if "Type" in group_df.columns else ""
            brand = str(row.get("Brand", "")).strip() if "Brand" in group_df.columns else ""

            if total_avail <= safety:
                continue
            if eff_sold >= max_protected:
                continue

            base = total_avail - safety
            cap = max(int(total_avail * C_MODE_PERCENTAGE_CAP), 1)
            abs_cap = C_MODE_ABS_CAP
            transferable = max(1, int(min(base, cap, abs_cap, net_stock)))

            if transferable <= 0:
                continue

            remaining = net_stock - transferable
            if remaining >= safety:
                source_type = SOURCE_RF_SURPLUS_C_FALLBACK
            else:
                source_type = SOURCE_RF_ENHANCED_C_FALLBACK

            c_sources.append({
                "article": article, "site": site, "om": om,
                "rp_type": rp, "net_stock": net_stock,
                "pending_received": pending, "safety_stock": safety,
                "last_month_sold": last_month, "mtd_sold": mtd,
                "effective_sold_qty": eff_sold,
                "transferable_qty": transferable,
                "source_type": source_type,
                "priority": 2,
                "store_type": store_type, "brand": brand,
                "product_desc": str(row.get("Article Description", "")).strip() if "Article Description" in group_df.columns else "",
                "total_available": total_avail,
                "original_stock": net_stock,
                "total_transferred": 0,
            })

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

                rec = build_recommendation(source, dest, transfer_qty, mode, received_qty_by_site)
                if rec:
                    rec["Source Type"] = source.get("source_type", "")
                    rec["Remark"] = f"{source.get('source_type', '')} -> {dest.get('dest_type', '')}"
                    recommendations.append(rec)

                apply_transfer(source, dest, transfer_qty, received_qty_by_site)
                transfer_sites.add(source.get("site", ""))
                receive_sites.add(dest.get("site", ""))

                source_key = source.get("site", "")
                if source_key not in source_to_receive_sites:
                    source_to_receive_sites[source_key] = set()
                source_to_receive_sites[source_key].add(dest.get("site", ""))

        return recommendations
