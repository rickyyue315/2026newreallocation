import os
import json
import io
import pandas as pd
import numpy as np
from typing import Any, Optional, Union

from config import (
    REQUIRED_COLUMNS,
    OPTIONAL_COLUMNS,
    INTEGER_COLUMNS,
    STRING_COLUMNS,
    OUTLIER_CAP,
    FILE_SIZE_LIMIT_BYTES,
)


class DataProcessor:
    def __init__(self, stores_json_path: str = "data/stores.json"):
        self.stores_json_path = stores_json_path
        self.stores_data: dict = {}
        self._load_stores()

    def _load_stores(self):
        try:
            with open(self.stores_json_path, "r", encoding="utf-8") as f:
                self.stores_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.stores_data = {}

    def preprocess_data(
        self, file_path_or_buffer: Union[str, io.BytesIO]
    ) -> tuple[pd.DataFrame, dict]:
        stats: dict[str, Any] = {
            "original_rows": 0,
            "final_rows": 0,
            "invalid_rp_type_fixed": 0,
            "om_filled": 0,
            "type_filled": 0,
            "sites_not_found": [],
            "outliers_corrected": 0,
            "missing_values_filled": 0,
            "negative_values_fixed": 0,
        }

        file_size = self._get_file_size(file_path_or_buffer)
        if file_size is not None and file_size > FILE_SIZE_LIMIT_BYTES:
            raise ValueError(
                f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds limit "
                f"({FILE_SIZE_LIMIT_BYTES / 1024 / 1024:.0f}MB)"
            )

        df = self._read_excel_file(file_path_or_buffer)
        stats["original_rows"] = len(df)

        df = self._validate_columns(df)
        df = self._convert_data_types(df, stats)
        df = self._fill_default_store_data(df, stats)
        df = self._handle_missing_values(df, stats)
        df = self._correct_outliers(df, stats)
        df = self._calculate_effective_sold_qty(df)

        stats["final_rows"] = len(df)
        return df, stats

    def _read_excel_file(self, file_path_or_buffer) -> pd.DataFrame:
        if isinstance(file_path_or_buffer, io.BytesIO):
            file_path_or_buffer.seek(0)

        try:
            df = pd.read_excel(
                file_path_or_buffer,
                engine="calamine",
                dtype=str,
            )
        except Exception:
            df = pd.read_excel(
                file_path_or_buffer,
                engine="openpyxl",
                dtype=str,
            )

        df = self._normalize_columns(df)
        df = self._normalize_article(df)
        return df

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        col_map = {}
        for col in df.columns:
            col_upper = str(col).upper().strip()
            if col_upper == "ALL":
                col_map[col] = "ALL"
            elif col_upper in ("TARGET", "TARGET QTY", "TARGET_QTY"):
                col_map[col] = "Target"
            elif col_upper == "TYPE":
                col_map[col] = "Type"
            elif col_upper in ("ARTICLE DESCRIPTION", "PRODUCT DESC", "PRODUCT_DESC"):
                col_map[col] = "Article Description"
            elif col_upper in (
                "ARTICLE LONG TEXT (60 CHARS)",
                "ARTICLE_LONG_TEXT",
                "LONG TEXT",
            ):
                col_map[col] = "Article Long Text (60 Chars)"
            elif col_upper in ("LAST 2 MONTH SOLD QTY", "LAST_2_MONTH_SOLD_QTY"):
                col_map[col] = "Last 2 Month Sold Qty"
            elif col_upper in ("BRAND", "品牌", "PRODUCT HIERARCHY", "PRODUCT_HIERARCHY"):
                col_map[col] = "Brand"

        df = df.rename(columns=col_map)

        all_cols = [c for c in df.columns if c.upper() == "ALL"]
        if len(all_cols) > 1:
            target_col = all_cols[0]
            cols_to_drop = [c for c in all_cols if c != target_col]
            df = df.drop(columns=cols_to_drop)

        if "ALL" not in df.columns:
            df["ALL"] = ""

        return df

    def _normalize_article(self, df: pd.DataFrame) -> pd.DataFrame:
        if "Article" in df.columns:
            df["Article"] = df["Article"].astype(str).str.strip().str.zfill(12).str[-12:]
        return df

    def _get_file_size(self, file_path_or_buffer) -> Optional[int]:
        if isinstance(file_path_or_buffer, io.BytesIO):
            file_path_or_buffer.seek(0, os.SEEK_END)
            size = file_path_or_buffer.tell()
            file_path_or_buffer.seek(0)
            return size
        if isinstance(file_path_or_buffer, str) and os.path.isfile(file_path_or_buffer):
            return os.path.getsize(file_path_or_buffer)
        return None

    def _validate_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}")
        return df

    def _convert_data_types(self, df: pd.DataFrame, stats: dict) -> pd.DataFrame:
        for col in INTEGER_COLUMNS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

        for col in STRING_COLUMNS:
            if col in df.columns:
                df[col] = df[col].fillna("").astype(str).str.strip()

        if "RP Type" in df.columns:
            invalid = ~df["RP Type"].isin(["ND", "RF"])
            stats["invalid_rp_type_fixed"] = int(invalid.sum())
            df.loc[invalid, "RP Type"] = "RF"

        if "Site" in df.columns:
            df["Site"] = df["Site"].str.upper().str.strip()

        return df

    def _fill_default_store_data(self, df: pd.DataFrame, stats: dict) -> pd.DataFrame:
        if not self.stores_data:
            return df

        sites_upper = {s.upper(): s for s in self.stores_data}

        for idx, row in df.iterrows():
            site = str(row["Site"]).upper()
            store = self.stores_data.get(sites_upper.get(site, site))
            if store is None:
                stats["sites_not_found"].append(site)
                continue

            if "OM" in df.columns:
                om_val = row.get("OM", "")
                if not om_val or pd.isna(om_val) or str(om_val).strip() == "":
                    df.at[idx, "OM"] = store.get("om", "")
                    stats["om_filled"] += 1

            if "Type" in df.columns and "type" in store:
                type_val = row.get("Type", "")
                if not type_val or pd.isna(type_val) or str(type_val).strip() == "":
                    df.at[idx, "Type"] = store.get("type", "")
                    stats["type_filled"] += 1

        return df

    def _handle_missing_values(self, df: pd.DataFrame, stats: dict) -> pd.DataFrame:
        fill_cols = [
            "Safety Stock",
            "MOQ",
            "Last Month Sold Qty",
            "MTD Sold Qty",
            "Pending Received",
        ]
        for col in fill_cols:
            if col in df.columns:
                missing = df[col].isna().sum()
                stats["missing_values_filled"] += int(missing)
                df[col] = df[col].fillna(0).astype(int)

        if "Article Description" in df.columns and "Article Long Text (60 Chars)" in df.columns:
            df["Article Description"] = df["Article Description"].fillna(
                df["Article Long Text (60 Chars)"]
            )
            if "Article Description" in df.columns:
                df["Article Description"] = df["Article Description"].fillna("N/A")
        elif "Article Long Text (60 Chars)" in df.columns:
            df["Article Description"] = df["Article Long Text (60 Chars)"].fillna("N/A")
        else:
            df["Article Description"] = "N/A"

        return df

    def _correct_outliers(self, df: pd.DataFrame, stats: dict) -> pd.DataFrame:
        sales_cols = ["Last Month Sold Qty", "MTD Sold Qty", "Last 2 Month Sold Qty"]
        for col in sales_cols:
            if col in df.columns:
                neg_mask = df[col] < 0
                cap_mask = df[col] > OUTLIER_CAP
                stats["negative_values_fixed"] += int(neg_mask.sum())
                stats["outliers_corrected"] += int(cap_mask.sum())
                df.loc[neg_mask, col] = 0
                df.loc[cap_mask, col] = OUTLIER_CAP

        non_neg_cols = ["Safety Stock", "MOQ", "SaSa Net Stock", "Pending Received"]
        for col in non_neg_cols:
            if col in df.columns:
                neg = df[col] < 0
                stats["negative_values_fixed"] += int(neg.sum())
                df.loc[neg, col] = 0

        return df

    def _calculate_effective_sold_qty(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Effective Sold Qty"] = df["Last Month Sold Qty"].fillna(0).astype(int) + df[
            "MTD Sold Qty"
        ].fillna(0).astype(int)
        df["Total Available"] = df["SaSa Net Stock"].fillna(0).astype(int) + df[
            "Pending Received"
        ].fillna(0).astype(int)
        return df
