import math
from typing import Optional

import pandas as pd

from config import (
    A_MODE_PERCENTAGE_CAP,
    A_MODE_MIN_TRANSFER,
    B_MODE_PERCENTAGE_CAP,
    B_MODE_MIN_TRANSFER,
    C_MODE_PERCENTAGE_CAP,
    C_MODE_ABS_CAP,
    C1_MODE_MIN_TRANSFER,
    SAFETY_RECEIVE_MULTIPLIER,
    MIN_RECEIVE_FLOOR,
    F_TARGET_MULTIPLIER,
    F_TARGET_FLOOR,
    SIMPLIFIED_SKU_RECEIVE_MULTIPLIER,
    ND_RECEIVE_MULTIPLIER,
    SOURCE_ND,
    SOURCE_ND_CLEARANCE,
    SOURCE_ND_F_MODE,
    SOURCE_ND_SMART,
    SOURCE_RF_SURPLUS,
    SOURCE_RF_ENHANCED,
    SOURCE_RF_F_MODE,
    SOURCE_LOCAL_FULL,
    SOURCE_E_MANDATORY,
    SOURCE_SIMPLIFIED_ND,
    SOURCE_SIMPLIFIED_RF,
    DEST_CRITICAL,
    DEST_CRITICAL_RESTOCK,
    DEST_POTENTIAL,
    DEST_POTENTIAL_ND,
    DEST_ZERO_STOCK,
    DEST_F_TARGET,
    DEST_F2_TARGET,
    DEST_E_RECEIVE,
    DEST_SIMPLIFIED_RECV,
    SOURCE_ND_PRIORITY,
    SOURCE_RF_PRIORITY,
    DEST_CRITICAL_PRIORITY,
    DEST_POTENTIAL_PRIORITY,
    DEST_ZERO_STOCK_PRIORITY,
)
from models.mode_registry import MODE_REGISTRY, ModeDef


class TransferLogic:
    def __init__(self):
        self._mode_info_cache = MODE_REGISTRY

    def generate_transfer_recommendations(
        self,
        df: pd.DataFrame,
        mode: str,
        receive_site_limit: Optional[int] = None,
        f2_hd_transfer: bool = False,
    ) -> list:
        mode_def = self._mode_info_cache.get(mode)
        if not mode_def:
            raise ValueError(f"Unknown mode: {mode}")

        cross_om = mode_def.cross_om_grouping

        all_recommendations = []

        group_cols = ["Article"]
        if not cross_om:
            group_cols.append("OM")

        for group_key, group_df in df.groupby(group_cols, dropna=False):
            if isinstance(group_key, tuple):
                article = group_key[0]
                om_val = group_key[1] if len(group_key) > 1 else None
            else:
                article = str(group_key)
                om_val = None

            article = str(article).strip()

            sources = self._identify_sources(group_df, mode, article)
            dests = self._identify_destinations(group_df, mode, article, sources)

            if mode_def.source_filter:
                source_sites = {s["site"] for s in sources}
                dests = [d for d in dests if d["site"] not in source_sites]

            if not sources or not dests:
                continue

            transfer_sites: set = set()
            receive_sites: set = set()
            source_to_receive_sites: dict = {}
            received_qty_by_site: dict = {}
            matched_sites: set = set()

            group_recs = self._run_matching(
                sources,
                dests,
                mode,
                article,
                transfer_sites,
                receive_sites,
                source_to_receive_sites,
                received_qty_by_site,
                matched_sites,
                receive_site_limit,
                f2_hd_transfer,
            )

            all_recommendations.extend(group_recs)

        return all_recommendations

    def _run_matching(
        self,
        sources: list,
        dests: list,
        mode: str,
        article: str,
        transfer_sites: set,
        receive_sites: set,
        source_to_receive_sites: dict,
        received_qty_by_site: dict,
        matched_sites: set,
        receive_site_limit: Optional[int],
        f2_hd_transfer: bool = False,
    ) -> list:
        recommendations = []
        mode_def = self._mode_info_cache.get(mode)
        strategy_key = mode_def.strategy_key if mode_def else None

        if strategy_key == "b_special":
            from strategies.b_special import BSpecialStrategy
            strategy = BSpecialStrategy()
            return strategy.match(
                self, sources, dests, recommendations, mode, article,
                transfer_sites, receive_sites, source_to_receive_sites,
                received_qty_by_site, matched_sites, receive_site_limit,
            )
        elif strategy_key == "c2_mode":
            from strategies.c2_mode import C2ModeStrategy
            strategy = C2ModeStrategy()
            return strategy.match(
                self, sources, dests, recommendations, mode, article,
                transfer_sites, receive_sites, source_to_receive_sites,
                received_qty_by_site, matched_sites, receive_site_limit,
            )
        elif strategy_key == "e1_mode":
            from strategies.e1_mode import E1ModeStrategy
            strategy = E1ModeStrategy()
            return strategy.match(
                self, sources, dests, recommendations, mode, article,
                transfer_sites, receive_sites, source_to_receive_sites,
                received_qty_by_site, matched_sites, receive_site_limit,
            )
        elif strategy_key == "e2_mode":
            from strategies.e2_mode import E2ModeStrategy
            strategy = E2ModeStrategy()
            return strategy.match(
                self, sources, dests, recommendations, mode, article,
                transfer_sites, receive_sites, source_to_receive_sites,
                received_qty_by_site, matched_sites, receive_site_limit,
            )
        elif strategy_key == "f_mode":
            from strategies.f_mode import FModeStrategy
            strategy = FModeStrategy()
            return strategy.match(
                self, sources, dests, recommendations, mode, article,
                transfer_sites, receive_sites, source_to_receive_sites,
                received_qty_by_site, matched_sites, receive_site_limit,
                f2_hd_transfer=f2_hd_transfer,
            )
        elif strategy_key == "nd_mode":
            from strategies.nd_mode import NDModeStrategy
            strategy = NDModeStrategy()
            return strategy.match(
                self, sources, dests, recommendations, mode, article,
                transfer_sites, receive_sites, source_to_receive_sites,
                received_qty_by_site, matched_sites, receive_site_limit,
            )
        elif strategy_key == "simplified_sku":
            from strategies.simplified_sku import SimplifiedSKUStrategy
            strategy = SimplifiedSKUStrategy()
            return strategy.match(
                self, sources, dests, recommendations, mode, article,
                transfer_sites, receive_sites, source_to_receive_sites,
                received_qty_by_site, matched_sites, receive_site_limit,
            )
        else:
            from services.matching_engine import match_general_mode
            return match_general_mode(
                self, sources, dests, recommendations, mode, article,
                transfer_sites, receive_sites, source_to_receive_sites,
                received_qty_by_site, matched_sites, receive_site_limit,
            )

    @staticmethod
    def _extract_article(df: pd.DataFrame) -> str:
        return str(df["Article"].iloc[0]).strip() if len(df) > 0 else ""

    def _identify_sources(self, df: pd.DataFrame, mode: str, article: str) -> list:
        mode_def = self._mode_info_cache.get(mode)
        if not mode_def:
            return []

        source_method = mode_def.source_method
        if source_method and hasattr(self, source_method):
            return getattr(self, source_method)(df, mode, article)

        return self._sources_general(df, mode, article)

    def _identify_destinations(self, df: pd.DataFrame, mode: str, article: str, sources: list = None) -> list:
        mode_def = self._mode_info_cache.get(mode)
        if not mode_def:
            return []

        dest_method = mode_def.dest_method
        if dest_method and hasattr(self, dest_method):
            return getattr(self, dest_method)(df, mode)

        return self._dests_general(df, mode, article)

    def _compute_max_protected_sold(self, df: pd.DataFrame, om_col: bool = True) -> float:
        rf_df = df[df["RP Type"] == "RF"]
        if len(rf_df) <= 1:
            return float("inf")

        max_sold = rf_df["Effective Sold Qty"].max()
        if max_sold == 0:
            return float("inf")

        if rf_df["Effective Sold Qty"].nunique() == 1:
            return float("inf")

        return max_sold

    def _sources_general(self, df: pd.DataFrame, mode: str, article: str = "") -> list:
        sources = []
        max_protected = self._compute_max_protected_sold(df)
        mode_def = self._mode_info_cache.get(mode, self._mode_info_cache.get("B"))
        if not article:
            article = self._extract_article(df)
        is_b_special = mode_def and "b_special" in mode_def.families if mode_def else False
        is_d_family = mode_def and "d_family" in mode_def.families if mode_def else False
        no_tourist = mode_def and "b_tourist_no_source" in mode_def.families if mode_def else False
        l_retain = mode_def and "b_l_retain" in mode_def.families if mode_def else False

        for _, row in df.iterrows():
            rp = str(row.get("RP Type", "")).strip()
            net_stock = int(row.get("SaSa Net Stock", 0))
            pending = int(row.get("Pending Received", 0))
            total_avail = net_stock + pending
            safety = int(row.get("Safety Stock", 0))
            last_month = int(row.get("Last Month Sold Qty", 0))
            mtd = int(row.get("MTD Sold Qty", 0))
            eff_sold = int(row.get("Effective Sold Qty", 0))
            moq = int(row.get("MOQ", 0))
            site = str(row.get("Site", "")).strip()
            om = str(row.get("OM", "")).strip()
            store_type = str(row.get("Type", "")).strip().upper() if "Type" in df.columns else ""
            brand = str(row.get("Brand", "")).strip() if "Brand" in df.columns else ""
            prod_desc = str(row.get("Article Description", "")).strip() if "Article Description" in df.columns else ""

            if rp == "ND":
                if net_stock <= 0:
                    continue

                if is_d_family:
                    if last_month > 0 or mtd > 0:
                        sources.append({
                            "article": article, "site": site, "om": om,
                            "rp_type": rp, "net_stock": net_stock,
                            "pending_received": pending, "safety_stock": safety,
                            "last_month_sold": last_month, "mtd_sold": mtd,
                            "effective_sold_qty": eff_sold, "moq": moq,
                            "transferable_qty": net_stock,
                            "source_type": SOURCE_ND,
                            "priority": SOURCE_ND_PRIORITY,
                            "store_type": store_type, "brand": brand,
                            "product_desc": prod_desc,
                            "total_available": total_avail,
                            "original_stock": net_stock,
                            "total_transferred": 0,
                        })
                    else:
                        sources.append({
                            "article": article, "site": site, "om": om,
                            "rp_type": rp, "net_stock": net_stock,
                            "pending_received": pending, "safety_stock": safety,
                            "last_month_sold": last_month, "mtd_sold": mtd,
                            "effective_sold_qty": eff_sold, "moq": moq,
                            "transferable_qty": net_stock,
                            "source_type": SOURCE_ND_CLEARANCE,
                            "priority": SOURCE_ND_PRIORITY,
                            "store_type": store_type, "brand": brand,
                            "product_desc": prod_desc,
                            "total_available": total_avail,
                            "original_stock": net_stock,
                            "total_transferred": 0,
                        })
                else:
                    if net_stock > 0:
                        sources.append({
                            "article": article, "site": site, "om": om,
                            "rp_type": rp, "net_stock": net_stock,
                            "pending_received": pending, "safety_stock": safety,
                            "last_month_sold": last_month, "mtd_sold": mtd,
                            "effective_sold_qty": eff_sold, "moq": moq,
                            "transferable_qty": net_stock,
                            "source_type": SOURCE_ND,
                            "priority": SOURCE_ND_PRIORITY,
                            "store_type": store_type, "brand": brand,
                            "product_desc": prod_desc,
                            "total_available": total_avail,
                            "original_stock": net_stock,
                            "total_transferred": 0,
                        })

            elif rp == "RF":
                if no_tourist and store_type == "T":
                    continue

                if is_b_special and store_type == "L":
                    sales_check = max(last_month, mtd)
                    if sales_check <= 2:
                        if l_retain:
                            transferable = max(net_stock - 2, 0)
                        else:
                            transferable = net_stock
                        if transferable > 0:
                            sources.append({
                                "article": article, "site": site, "om": om,
                                "rp_type": rp, "net_stock": net_stock,
                                "pending_received": pending, "safety_stock": safety,
                                "last_month_sold": last_month, "mtd_sold": mtd,
                                "effective_sold_qty": eff_sold, "moq": moq,
                                "transferable_qty": transferable,
                                "source_type": SOURCE_LOCAL_FULL,
                                "priority": SOURCE_RF_PRIORITY,
                                "store_type": store_type, "brand": brand,
                                "product_desc": prod_desc,
                                "total_available": total_avail,
                                "original_stock": net_stock,
                                "total_transferred": 0,
                            })
                        continue

                if mode in ("D", "D2"):
                    continue

                if net_stock <= 0:
                    continue

                if eff_sold >= max_protected:
                    continue

                if mode in ("A", "D", "D2"):
                    if total_avail <= safety:
                        continue
                    if eff_sold >= max_protected:
                        continue
                    base = total_avail - safety
                    cap = max(int(total_avail * A_MODE_PERCENTAGE_CAP), A_MODE_MIN_TRANSFER)
                    actual = int(min(base, cap, net_stock))

                    remaining = net_stock - actual
                    if actual == 1 and remaining >= 3 and cap >= 2:
                        actual = 2

                    if actual <= 0:
                        continue
                    if net_stock - actual < safety:
                        continue

                    sources.append({
                        "article": article, "site": site, "om": om,
                        "rp_type": rp, "net_stock": net_stock,
                        "pending_received": pending, "safety_stock": safety,
                        "last_month_sold": last_month, "mtd_sold": mtd,
                        "effective_sold_qty": eff_sold, "moq": moq,
                        "transferable_qty": actual,
                        "source_type": SOURCE_RF_SURPLUS,
                        "priority": SOURCE_RF_PRIORITY,
                        "store_type": store_type, "brand": brand,
                        "product_desc": prod_desc,
                        "total_available": total_avail,
                        "original_stock": net_stock,
                        "total_transferred": 0,
                    })
                    continue

                if total_avail <= safety:
                    continue

                base = total_avail - safety
                if mode in ("C", "C1", "C2"):
                    cap = max(int(total_avail * C_MODE_PERCENTAGE_CAP), 1)
                    abs_cap = C_MODE_ABS_CAP
                    actual = max(1, int(min(base, cap, abs_cap, net_stock)))
                    if mode == "C1":
                        if net_stock <= 2:
                            continue
                        if actual < C1_MODE_MIN_TRANSFER:
                            continue
                else:
                    cap = max(int(total_avail * B_MODE_PERCENTAGE_CAP), B_MODE_MIN_TRANSFER)
                    actual = int(min(base, cap, net_stock))

                if actual <= 0:
                    continue

                remaining = net_stock - actual
                if remaining >= safety:
                    source_type = SOURCE_RF_SURPLUS
                else:
                    source_type = SOURCE_RF_ENHANCED

                sources.append({
                    "article": article, "site": site, "om": om,
                    "rp_type": rp, "net_stock": net_stock,
                    "pending_received": pending, "safety_stock": safety,
                    "last_month_sold": last_month, "mtd_sold": mtd,
                    "effective_sold_qty": eff_sold, "moq": moq,
                    "transferable_qty": actual,
                    "source_type": source_type,
                    "priority": SOURCE_RF_PRIORITY,
                    "store_type": store_type, "brand": brand,
                    "product_desc": prod_desc,
                    "total_available": total_avail,
                    "original_stock": net_stock,
                    "total_transferred": 0,
                })

        return sources

    def _dests_general(self, df: pd.DataFrame, mode: str, article: str = "") -> list:
        dests = []
        mode_def = self._mode_info_cache.get(mode, self._mode_info_cache.get("B"))
        is_d_family = mode_def and "d_family" in mode_def.families if mode_def else False
        if not article:
            article = self._extract_article(df)

        for _, row in df.iterrows():
            rp = str(row.get("RP Type", "")).strip()
            if rp != "RF":
                continue

            net_stock = int(row.get("SaSa Net Stock", 0))
            pending = int(row.get("Pending Received", 0))
            total_avail = net_stock + pending
            safety = int(row.get("Safety Stock", 0))
            last_month = int(row.get("Last Month Sold Qty", 0))
            mtd = int(row.get("MTD Sold Qty", 0))
            eff_sold = int(row.get("Effective Sold Qty", 0))
            moq = int(row.get("MOQ", 0))
            site = str(row.get("Site", "")).strip()
            om = str(row.get("OM", "")).strip()
            store_type = str(row.get("Type", "")).strip().upper() if "Type" in df.columns else ""
            brand = str(row.get("Brand", "")).strip() if "Brand" in df.columns else ""

            if net_stock == 0 and eff_sold > 0:
                if is_d_family:
                    needed = max(safety, 2) - total_avail
                else:
                    needed = safety

                dests.append({
                    "article": article, "site": site, "om": om,
                    "rp_type": rp, "net_stock": net_stock,
                    "pending_received": pending, "safety_stock": safety,
                    "last_month_sold": last_month, "mtd_sold": mtd,
                    "effective_sold_qty": eff_sold, "moq": moq,
                    "needed_qty": max(needed, 1),
                    "dest_type": DEST_CRITICAL,
                    "priority": DEST_CRITICAL_PRIORITY,
                    "store_type": store_type, "brand": brand,
                    "total_available": total_avail,
                })
                continue

            if total_avail < safety:
                needed = safety - total_avail
                if needed <= 0:
                    continue
                dests.append({
                    "article": article, "site": site, "om": om,
                    "rp_type": rp, "net_stock": net_stock,
                    "pending_received": pending, "safety_stock": safety,
                    "last_month_sold": last_month, "mtd_sold": mtd,
                    "effective_sold_qty": eff_sold, "moq": moq,
                    "needed_qty": needed,
                    "dest_type": DEST_POTENTIAL,
                    "priority": DEST_POTENTIAL_PRIORITY,
                    "store_type": store_type, "brand": brand,
                    "total_available": total_avail,
                })
                continue

            if mode == "C" and total_avail <= 1 and (safety > 0 or eff_sold > 0):
                target_qty = max(int(safety * F_TARGET_MULTIPLIER), F_TARGET_FLOOR)
                needed = target_qty - total_avail
                if needed > 0:
                    dests.append({
                        "article": article, "site": site, "om": om,
                        "rp_type": rp, "net_stock": net_stock,
                        "pending_received": pending, "safety_stock": safety,
                        "last_month_sold": last_month, "mtd_sold": mtd,
                        "effective_sold_qty": eff_sold, "moq": moq,
                        "needed_qty": needed,
                        "dest_type": DEST_ZERO_STOCK,
                        "priority": DEST_ZERO_STOCK_PRIORITY,
                        "target_qty": target_qty,
                        "is_d_family": False,
                        "store_type": store_type, "brand": brand,
                        "total_available": total_avail,
                    })

        return dests

    def _dests_b_special(self, df: pd.DataFrame, mode: str) -> list:
        dests = []
        article = self._extract_article(df)

        for _, row in df.iterrows():
            rp = str(row.get("RP Type", "")).strip()
            if rp != "RF":
                continue

            net_stock = int(row.get("SaSa Net Stock", 0))
            pending = int(row.get("Pending Received", 0))
            total_avail = net_stock + pending
            safety = int(row.get("Safety Stock", 0))
            last_month = int(row.get("Last Month Sold Qty", 0))
            mtd = int(row.get("MTD Sold Qty", 0))
            eff_sold = int(row.get("Effective Sold Qty", 0))
            site = str(row.get("Site", "")).strip()
            om = str(row.get("OM", "")).strip()
            store_type = str(row.get("Type", "")).strip().upper() if "Type" in df.columns else ""
            brand = str(row.get("Brand", "")).strip() if "Brand" in df.columns else ""

            cap_receive = max(safety * SAFETY_RECEIVE_MULTIPLIER, MIN_RECEIVE_FLOOR)

            if total_avail >= cap_receive:
                continue

            needed = cap_receive - total_avail
            if needed <= 0:
                continue

            sales_total = last_month + mtd

            if store_type == "T" and sales_total > 0:
                priority = 1
            elif store_type == "M" and sales_total > 0:
                priority = 2
            elif store_type == "T" and sales_total == 0:
                priority = 3
            elif store_type == "M" or sales_total == 0:
                priority = 4
            else:
                priority = 5

            dests.append({
                "article": article, "site": site, "om": om,
                "rp_type": rp, "net_stock": net_stock,
                "pending_received": pending, "safety_stock": safety,
                "last_month_sold": last_month, "mtd_sold": mtd,
                "effective_sold_qty": eff_sold,
                "needed_qty": needed,
                "dest_type": DEST_CRITICAL,
                "priority": priority,
                "target_qty": cap_receive,
                "is_b_special_dest": True,
                "store_type": store_type, "brand": brand,
                "total_available": total_avail,
            })

        dests.sort(key=lambda d: (d["priority"], -d.get("effective_sold_qty", 0) if d["priority"] <= 2 else -d.get("safety_stock", 0)))
        return dests

    def _dests_c1_mode(self, df: pd.DataFrame, mode: str) -> list:
        dests = []
        article = self._extract_article(df)

        for _, row in df.iterrows():
            rp = str(row.get("RP Type", "")).strip()
            if rp != "RF":
                continue

            net_stock = int(row.get("SaSa Net Stock", 0))
            pending = int(row.get("Pending Received", 0))
            total_avail = net_stock + pending
            safety = int(row.get("Safety Stock", 0))
            last_month = int(row.get("Last Month Sold Qty", 0))
            mtd = int(row.get("MTD Sold Qty", 0))
            eff_sold = int(row.get("Effective Sold Qty", 0))
            site = str(row.get("Site", "")).strip()
            om = str(row.get("OM", "")).strip()
            brand = str(row.get("Brand", "")).strip() if "Brand" in df.columns else ""

            if total_avail > 1:
                continue

            if safety <= 0 and eff_sold <= 0:
                continue

            target_qty = max(int(safety * F_TARGET_MULTIPLIER), F_TARGET_FLOOR)
            needed = target_qty - total_avail
            if needed <= 0:
                continue

            dests.append({
                "article": article, "site": site, "om": om,
                "rp_type": rp, "net_stock": net_stock,
                "pending_received": pending, "safety_stock": safety,
                "last_month_sold": last_month, "mtd_sold": mtd,
                "effective_sold_qty": eff_sold,
                "needed_qty": needed,
                "dest_type": DEST_ZERO_STOCK,
                "priority": DEST_ZERO_STOCK_PRIORITY,
                "target_qty": target_qty,
                "is_d_family": False,
                "store_type": "", "brand": brand,
                "total_available": total_avail,
            })

        return dests

    def _dests_d_mode(self, df: pd.DataFrame, mode: str) -> list:
        dests = []
        article = self._extract_article(df)

        for _, row in df.iterrows():
            rp = str(row.get("RP Type", "")).strip()
            if rp != "RF":
                continue

            net_stock = int(row.get("SaSa Net Stock", 0))
            pending = int(row.get("Pending Received", 0))
            total_avail = net_stock + pending
            safety = int(row.get("Safety Stock", 0))
            last_month = int(row.get("Last Month Sold Qty", 0))
            mtd = int(row.get("MTD Sold Qty", 0))
            eff_sold = int(row.get("Effective Sold Qty", 0))
            site = str(row.get("Site", "")).strip()
            om = str(row.get("OM", "")).strip()
            store_type = str(row.get("Type", "")).strip().upper() if "Type" in df.columns else ""
            brand = str(row.get("Brand", "")).strip() if "Brand" in df.columns else ""

            if net_stock == 0 and eff_sold > 0:
                needed = max(safety, 2) - total_avail
                dests.append({
                    "article": article, "site": site, "om": om,
                    "rp_type": rp, "net_stock": net_stock,
                    "pending_received": pending, "safety_stock": safety,
                    "last_month_sold": last_month, "mtd_sold": mtd,
                    "effective_sold_qty": eff_sold,
                    "needed_qty": max(needed, 1),
                    "dest_type": DEST_CRITICAL,
                    "priority": DEST_CRITICAL_PRIORITY,
                    "store_type": store_type, "brand": brand,
                    "total_available": total_avail,
                })
                continue

            if total_avail < safety:
                needed = safety - total_avail
                if needed > 0:
                    dests.append({
                        "article": article, "site": site, "om": om,
                        "rp_type": rp, "net_stock": net_stock,
                        "pending_received": pending, "safety_stock": safety,
                        "last_month_sold": last_month, "mtd_sold": mtd,
                        "effective_sold_qty": eff_sold,
                        "needed_qty": needed,
                        "dest_type": DEST_POTENTIAL,
                        "priority": DEST_POTENTIAL_PRIORITY,
                        "store_type": store_type, "brand": brand,
                        "total_available": total_avail,
                    })

        return dests

    def _sources_e_mode(self, df: pd.DataFrame, mode: str, article: str = "") -> list:
        sources = []
        for _, row in df.iterrows():
            all_val = str(row.get("ALL", "")).strip()
            if not all_val:
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
            site = str(row.get("Site", "")).strip()
            om = str(row.get("OM", "")).strip()
            rp = str(row.get("RP Type", "")).strip()
            store_type = str(row.get("Type", "")).strip().upper() if "Type" in df.columns else ""
            brand = str(row.get("Brand", "")).strip() if "Brand" in df.columns else ""

            sources.append({
                "article": article, "site": site, "om": om,
                "rp_type": rp, "net_stock": net_stock,
                "pending_received": pending, "safety_stock": safety,
                "last_month_sold": last_month, "mtd_sold": mtd,
                "effective_sold_qty": eff_sold,
                "transferable_qty": net_stock,
                "source_type": SOURCE_E_MANDATORY,
                "priority": SOURCE_ND_PRIORITY,
                "store_type": store_type, "brand": brand,
                "product_desc": str(row.get("Article Description", "")).strip(),
                "total_available": total_avail,
                "original_stock": net_stock,
                "total_transferred": 0,
            })

        return sources

    def _dests_e_mode(self, df: pd.DataFrame, mode: str) -> list:
        dests = []
        article = self._extract_article(df)

        dest_entries = []
        for _, row in df.iterrows():
            rp = str(row.get("RP Type", "")).strip()
            if rp != "RF":
                continue

            net_stock = int(row.get("SaSa Net Stock", 0))
            pending = int(row.get("Pending Received", 0))
            total_avail = net_stock + pending
            safety = int(row.get("Safety Stock", 0))
            last_month = int(row.get("Last Month Sold Qty", 0))
            mtd = int(row.get("MTD Sold Qty", 0))
            eff_sold = int(row.get("Effective Sold Qty", 0))
            site = str(row.get("Site", "")).strip()
            om = str(row.get("OM", "")).strip()
            store_type = str(row.get("Type", "")).strip().upper() if "Type" in df.columns else ""
            brand = str(row.get("Brand", "")).strip() if "Brand" in df.columns else ""

            cap_receive = max(safety * SAFETY_RECEIVE_MULTIPLIER, MIN_RECEIVE_FLOOR)
            if total_avail >= cap_receive:
                continue

            needed = cap_receive - total_avail
            if needed <= 0:
                continue

            entry = {
                "article": article, "site": site, "om": om,
                "rp_type": rp, "net_stock": net_stock,
                "pending_received": pending, "safety_stock": safety,
                "last_month_sold": last_month, "mtd_sold": mtd,
                "effective_sold_qty": eff_sold,
                "needed_qty": needed,
                "dest_type": DEST_E_RECEIVE,
                "priority": 0,
                "target_qty": cap_receive,
                "is_b_special_dest": True,
                "store_type": store_type, "brand": brand,
                "total_available": total_avail,
            }
            dest_entries.append(entry)

        if mode == "E1b":
            dest_entries.sort(key=lambda d: (
                0 if (d["store_type"] == "T" and (d["last_month_sold"] + d["mtd_sold"]) > 0) else
                1 if (d["store_type"] == "M" and (d["last_month_sold"] + d["mtd_sold"]) > 0) else
                2 if (d["store_type"] == "T") else
                3 if (d["store_type"] == "M") else 4,
                -(d["last_month_sold"] + d["mtd_sold"]) if d["store_type"] in ("T", "M") and (d["last_month_sold"] + d["mtd_sold"]) > 0 else -d["safety_stock"],
            ))
        else:
            dest_entries.sort(key=lambda d: (-d["needed_qty"], -d["effective_sold_qty"]))

        for i, entry in enumerate(dest_entries):
            entry["priority"] = i + 1
            dests.append(entry)

        return dests

    def _sources_f_mode(self, df: pd.DataFrame, mode: str, article: str = "") -> list:
        sources = []
        from services.target_utils import parse_target_series

        if not article:
            article = self._extract_article(df)

        target_stores = set()
        if mode == "F2":
            target_stores = set()
            for _, row in df.iterrows():
                has_target, _, _, _ = parse_target_series(row.get("Target"))
                if has_target and str(row.get("Site", "")).strip():
                    target_stores.add(str(row.get("Site", "")).strip())

        for _, row in df.iterrows():
            site = str(row.get("Site", "")).strip()
            has_target, _, _, _ = parse_target_series(row.get("Target"))

            if has_target:
                continue
            if mode == "F2" and site in target_stores:
                continue

            rp = str(row.get("RP Type", "")).strip()
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
            store_type = str(row.get("Type", "")).strip().upper() if "Type" in df.columns else ""
            brand = str(row.get("Brand", "")).strip() if "Brand" in df.columns else ""

            if rp == "ND":
                sources.append({
                    "article": article, "site": site, "om": om,
                    "rp_type": rp, "net_stock": net_stock,
                    "pending_received": pending, "safety_stock": safety,
                    "last_month_sold": last_month, "mtd_sold": mtd,
                    "effective_sold_qty": eff_sold,
                    "transferable_qty": net_stock,
                    "source_type": SOURCE_ND_F_MODE,
                    "priority": SOURCE_ND_PRIORITY,
                    "store_type": store_type, "brand": brand,
                    "product_desc": "",
                    "total_available": total_avail,
                    "original_stock": net_stock,
                    "total_transferred": 0,
                })
            elif rp == "RF":
                max_protected = self._compute_max_protected_sold(df, om_col=False)
                if eff_sold >= max_protected:
                    continue

                sources.append({
                    "article": article, "site": site, "om": om,
                    "rp_type": rp, "net_stock": net_stock,
                    "pending_received": pending, "safety_stock": safety,
                    "last_month_sold": last_month, "mtd_sold": mtd,
                    "effective_sold_qty": eff_sold,
                    "transferable_qty": net_stock,
                    "source_type": SOURCE_RF_F_MODE,
                    "priority": SOURCE_RF_PRIORITY,
                    "store_type": store_type, "brand": brand,
                    "product_desc": "",
                    "total_available": total_avail,
                    "original_stock": net_stock,
                    "total_transferred": 0,
                })

        return sources

    def _dests_f_mode(self, df: pd.DataFrame, mode: str) -> list:
        from services.target_utils import parse_target_series

        dests = []
        article = self._extract_article(df)

        for _, row in df.iterrows():
            has_target, target_val, _, _ = parse_target_series(row.get("Target"))
            if not has_target:
                continue

            site = str(row.get("Site", "")).strip()
            net_stock = int(row.get("SaSa Net Stock", 0))
            pending = int(row.get("Pending Received", 0))
            total_avail = net_stock + pending
            safety = int(row.get("Safety Stock", 0))
            last_month = int(row.get("Last Month Sold Qty", 0))
            mtd = int(row.get("MTD Sold Qty", 0))
            eff_sold = int(row.get("Effective Sold Qty", 0))
            om = str(row.get("OM", "")).strip()
            rp = str(row.get("RP Type", "")).strip()
            store_type = str(row.get("Type", "")).strip().upper() if "Type" in df.columns else ""
            brand = str(row.get("Brand", "")).strip() if "Brand" in df.columns else ""

            needed = int(target_val)
            if needed <= 0:
                continue

            dest_type = DEST_F2_TARGET if mode == "F2" else DEST_F_TARGET

            dests.append({
                "article": article, "site": site, "om": om,
                "rp_type": rp, "net_stock": net_stock,
                "pending_received": pending, "safety_stock": safety,
                "last_month_sold": last_month, "mtd_sold": mtd,
                "effective_sold_qty": eff_sold,
                "needed_qty": needed,
                "dest_type": dest_type,
                "priority": DEST_CRITICAL_PRIORITY,
                "target_qty": needed,
                "store_type": store_type, "brand": brand,
                "total_available": total_avail,
            })

        if mode != "F2":
            for _, row in df.iterrows():
                rp = str(row.get("RP Type", "")).strip()
                if rp != "RF":
                    continue

                site = str(row.get("Site", "")).strip()
                net_stock = int(row.get("SaSa Net Stock", 0))
                pending = int(row.get("Pending Received", 0))
                total_avail = net_stock + pending
                safety = int(row.get("Safety Stock", 0))
                last_month = int(row.get("Last Month Sold Qty", 0))
                mtd = int(row.get("MTD Sold Qty", 0))
                eff_sold = int(row.get("Effective Sold Qty", 0))
                om = str(row.get("OM", "")).strip()
                brand = str(row.get("Brand", "")).strip() if "Brand" in df.columns else ""

                if total_avail > 1:
                    continue
                if safety <= 0 and eff_sold <= 0:
                    continue

                target_qty = max(int(safety * F_TARGET_MULTIPLIER), F_TARGET_FLOOR)
                needed = target_qty - total_avail
                if needed <= 0:
                    continue

                dests.append({
                    "article": article, "site": site, "om": om,
                    "rp_type": rp, "net_stock": net_stock,
                    "pending_received": pending, "safety_stock": safety,
                    "last_month_sold": last_month, "mtd_sold": mtd,
                    "effective_sold_qty": eff_sold,
                    "needed_qty": needed,
                    "dest_type": DEST_ZERO_STOCK,
                    "priority": DEST_POTENTIAL_PRIORITY,
                    "target_qty": target_qty,
                    "is_d_family": False,
                    "store_type": "", "brand": brand,
                    "total_available": total_avail,
                })

        return dests

    def _sources_nd_mode(self, df: pd.DataFrame, mode: str, article: str = "") -> list:
        sources = []
        nd_df = df[df["RP Type"] == "ND"]
        if len(nd_df) == 0:
            return sources

        max_nd_sold = nd_df["Effective Sold Qty"].max() if len(nd_df) > 1 else 0
        if len(nd_df) == 1 or nd_df["Effective Sold Qty"].nunique() == 1:
            max_nd_sold = float("inf")

        entries = []
        for _, row in nd_df.iterrows():
            net_stock = int(row.get("SaSa Net Stock", 0))
            if net_stock <= 0:
                continue
            eff_sold = int(row.get("Effective Sold Qty", 0))
            if eff_sold >= max_nd_sold:
                continue

            pending = int(row.get("Pending Received", 0))
            total_avail = net_stock + pending
            safety = int(row.get("Safety Stock", 0))
            last_month = int(row.get("Last Month Sold Qty", 0))
            mtd = int(row.get("MTD Sold Qty", 0))
            site = str(row.get("Site", "")).strip()
            om = str(row.get("OM", "")).strip()
            store_type = str(row.get("Type", "")).strip().upper() if "Type" in df.columns else ""
            brand = str(row.get("Brand", "")).strip() if "Brand" in df.columns else ""

            entries.append({
                "article": article, "site": site, "om": om,
                "rp_type": "ND", "net_stock": net_stock,
                "pending_received": pending, "safety_stock": safety,
                "last_month_sold": last_month, "mtd_sold": mtd,
                "effective_sold_qty": eff_sold,
                "transferable_qty": net_stock,
                "source_type": SOURCE_ND_SMART,
                "priority": SOURCE_ND_PRIORITY,
                "store_type": store_type, "brand": brand,
                "product_desc": str(row.get("Article Description", "")).strip(),
                "total_available": total_avail,
                "original_stock": net_stock,
                "total_transferred": 0,
                "total_sales": last_month + mtd,
            })

        entries.sort(key=lambda x: x["total_sales"])
        sources.extend(entries)
        return sources

    def _dests_nd_mode(self, df: pd.DataFrame, mode: str) -> list:
        dests = []
        article = self._extract_article(df)

        for _, row in df.iterrows():
            rp = str(row.get("RP Type", "")).strip()
            net_stock = int(row.get("SaSa Net Stock", 0))
            pending = int(row.get("Pending Received", 0))
            total_avail = net_stock + pending
            safety = int(row.get("Safety Stock", 0))
            last_month = int(row.get("Last Month Sold Qty", 0))
            mtd = int(row.get("MTD Sold Qty", 0))
            eff_sold = int(row.get("Effective Sold Qty", 0))
            site = str(row.get("Site", "")).strip()
            om = str(row.get("OM", "")).strip()
            store_type = str(row.get("Type", "")).strip().upper() if "Type" in df.columns else ""
            brand = str(row.get("Brand", "")).strip() if "Brand" in df.columns else ""

            if rp == "RF":
                if net_stock == 0 and eff_sold > 0:
                    needed = max(safety, 2)
                    dests.append({
                        "article": article, "site": site, "om": om,
                        "rp_type": rp, "net_stock": net_stock,
                        "pending_received": pending, "safety_stock": safety,
                        "last_month_sold": last_month, "mtd_sold": mtd,
                        "effective_sold_qty": eff_sold,
                        "needed_qty": needed,
                        "dest_type": DEST_CRITICAL_RESTOCK,
                        "priority": DEST_CRITICAL_PRIORITY,
                        "store_type": store_type, "brand": brand,
                        "total_available": total_avail,
                    })
            elif rp == "ND":
                total_sales = last_month + mtd
                if total_sales <= 0:
                    continue

                max_receive = total_sales * ND_RECEIVE_MULTIPLIER
                current_stock = total_avail
                if current_stock >= max_receive:
                    continue

                needed = max_receive - current_stock
                if needed <= 0:
                    continue

                dests.append({
                    "article": article, "site": site, "om": om,
                    "rp_type": rp, "net_stock": net_stock,
                    "pending_received": pending, "safety_stock": safety,
                    "last_month_sold": last_month, "mtd_sold": mtd,
                    "effective_sold_qty": eff_sold,
                    "needed_qty": needed,
                    "dest_type": DEST_POTENTIAL_ND,
                    "priority": DEST_POTENTIAL_PRIORITY,
                    "target_qty": max_receive,
                    "store_type": store_type, "brand": brand,
                    "total_available": total_avail,
                })

        dests.sort(key=lambda d: (
            0 if d["dest_type"] == DEST_CRITICAL_RESTOCK else 1,
            -d.get("total_sales", d.get("last_month_sold", 0) + d.get("mtd_sold", 0)),
        ))
        return dests

    def _sources_simplified_sku(self, df: pd.DataFrame, mode: str, article: str = "") -> list:
        sources = []

        max_protected = self._compute_max_protected_sold(df, om_col=False)

        for _, row in df.iterrows():
            rp = str(row.get("RP Type", "")).strip()
            net_stock = int(row.get("SaSa Net Stock", 0))
            if net_stock <= 0:
                continue
            pending = int(row.get("Pending Received", 0))
            total_avail = net_stock + pending
            safety = int(row.get("Safety Stock", 0))
            last_month = int(row.get("Last Month Sold Qty", 0))
            mtd = int(row.get("MTD Sold Qty", 0))
            eff_sold = int(row.get("Effective Sold Qty", 0))
            last2 = int(row.get("Last 2 Month Sold Qty", 0)) if "Last 2 Month Sold Qty" in df.columns else 0
            site = str(row.get("Site", "")).strip()
            om = str(row.get("OM", "")).strip()
            store_type = str(row.get("Type", "")).strip().upper() if "Type" in df.columns else ""
            brand = str(row.get("Brand", "")).strip() if "Brand" in df.columns else ""

            cap_val = max(safety * SIMPLIFIED_SKU_RECEIVE_MULTIPLIER, last2 * SIMPLIFIED_SKU_RECEIVE_MULTIPLIER)

            if rp == "ND":
                sources.append({
                    "article": article, "site": site, "om": om,
                    "rp_type": rp, "net_stock": net_stock,
                    "pending_received": pending, "safety_stock": safety,
                    "last_month_sold": last_month, "mtd_sold": mtd,
                    "effective_sold_qty": eff_sold,
                    "transferable_qty": net_stock,
                    "source_type": SOURCE_SIMPLIFIED_ND,
                    "priority": SOURCE_ND_PRIORITY,
                    "store_type": store_type, "brand": brand,
                    "product_desc": str(row.get("Article Description", "")).strip(),
                    "total_available": total_avail,
                    "original_stock": net_stock,
                    "total_transferred": 0,
                    "cap": cap_val,
                })
            elif rp == "RF":
                if eff_sold >= max_protected:
                    continue
                if total_avail <= cap_val:
                    continue

                transferable = min(total_avail - cap_val, net_stock)
                if transferable <= 0:
                    continue

                sources.append({
                    "article": article, "site": site, "om": om,
                    "rp_type": rp, "net_stock": net_stock,
                    "pending_received": pending, "safety_stock": safety,
                    "last_month_sold": last_month, "mtd_sold": mtd,
                    "effective_sold_qty": eff_sold,
                    "transferable_qty": transferable,
                    "source_type": SOURCE_SIMPLIFIED_RF,
                    "priority": SOURCE_RF_PRIORITY,
                    "store_type": store_type, "brand": brand,
                    "product_desc": str(row.get("Article Description", "")).strip(),
                    "total_available": total_avail,
                    "original_stock": net_stock,
                    "total_transferred": 0,
                    "cap": cap_val,
                })

        return sources

    def _dests_simplified_sku(self, df: pd.DataFrame, mode: str) -> list:
        dests = []
        article = self._extract_article(df)

        for _, row in df.iterrows():
            rp = str(row.get("RP Type", "")).strip()
            if rp != "RF":
                continue

            net_stock = int(row.get("SaSa Net Stock", 0))
            pending = int(row.get("Pending Received", 0))
            total_avail = net_stock + pending
            safety = int(row.get("Safety Stock", 0))
            last_month = int(row.get("Last Month Sold Qty", 0))
            mtd = int(row.get("MTD Sold Qty", 0))
            eff_sold = int(row.get("Effective Sold Qty", 0))
            last2 = int(row.get("Last 2 Month Sold Qty", 0)) if "Last 2 Month Sold Qty" in df.columns else 0
            site = str(row.get("Site", "")).strip()
            om = str(row.get("OM", "")).strip()
            store_type = str(row.get("Type", "")).strip().upper() if "Type" in df.columns else ""
            brand = str(row.get("Brand", "")).strip() if "Brand" in df.columns else ""

            cap_val = max(safety * SIMPLIFIED_SKU_RECEIVE_MULTIPLIER, last2 * SIMPLIFIED_SKU_RECEIVE_MULTIPLIER)
            if total_avail >= cap_val:
                continue

            needed = cap_val - total_avail
            if needed <= 0:
                continue

            dests.append({
                "article": article, "site": site, "om": om,
                "rp_type": rp, "net_stock": net_stock,
                "pending_received": pending, "safety_stock": safety,
                "last_month_sold": last_month, "mtd_sold": mtd,
                "effective_sold_qty": eff_sold,
                "needed_qty": needed,
                "dest_type": DEST_SIMPLIFIED_RECV,
                "priority": DEST_CRITICAL_PRIORITY,
                "target_qty": cap_val,
                "store_type": store_type, "brand": brand,
                "total_available": total_avail,
                "cap": cap_val,
            })

        dests.sort(key=lambda d: -d["needed_qty"])
        return dests
