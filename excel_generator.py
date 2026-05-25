import io
from datetime import datetime, timezone, timedelta

import pandas as pd
from xlsxwriter import Workbook

from config import (
    VERSION,
    EXCEL_HEADER_BG,
    EXCEL_HEADER_FONT,
    EXCEL_HEADER_SIZE,
    TRANSFER_EXCEL_COLUMNS,
    THEME,
)

_STAT_SECTION_FIELDS: dict[str, list[tuple[str, str]]] = {
    "article_stats": [
        ("Total Qty", "total_qty"),
        ("Count", "count"),
        ("OM Count", "om_count"),
    ],
    "om_stats": [
        ("Transfer Qty", "transfer_qty"),
        ("Receive Qty", "receive_qty"),
        ("Count", "count"),
        ("Article Count", "article_count"),
    ],
    "default": [
        ("Total Qty", "qty"),
        ("Count", "count"),
    ],
}


HKT = timezone(timedelta(hours=8))


def generate_filename() -> str:
    now = datetime.now(HKT)
    return f"調貨建議_{now.strftime('%Y%m%d_%H%M%S')}.xlsx"


class ExcelGenerator:
    def __init__(self):
        pass

    def generate_excel_file(
        self,
        recommendations: list,
        statistics: dict = None,
    ) -> io.BytesIO:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            self._create_transfer_recommendations_sheet(writer, recommendations)
            if statistics:
                self._create_summary_dashboard_sheet(writer, statistics)
        output.seek(0)
        return output

    def _create_transfer_recommendations_sheet(self, writer, recommendations: list):
        if not recommendations:
            df = pd.DataFrame(columns=TRANSFER_EXCEL_COLUMNS)
            df.to_excel(writer, sheet_name="調貨建議", index=False)
            return

        df = pd.DataFrame(recommendations)

        excel_cols = [c for c in TRANSFER_EXCEL_COLUMNS if c in df.columns]
        extra_cols = [c for c in df.columns if c not in TRANSFER_EXCEL_COLUMNS]
        final_cols = excel_cols + extra_cols
        df_out = df[final_cols]

        df_out.to_excel(writer, sheet_name="調貨建議", index=False, startrow=0)

        workbook: Workbook = writer.book
        worksheet = writer.sheets["調貨建議"]

        header_format = workbook.add_format({
            "bg_color": EXCEL_HEADER_BG,
            "font_name": EXCEL_HEADER_FONT,
            "font_size": EXCEL_HEADER_SIZE,
            "bold": True,
            "border": 1,
            "text_wrap": True,
            "valign": "vcenter",
        })

        for col_idx, col_name in enumerate(final_cols):
            worksheet.write(0, col_idx, col_name, header_format)

        for col_idx in range(len(final_cols)):
            max_width = len(str(final_cols[col_idx])) + 4
            for row_idx in range(len(df_out)):
                val = str(df_out.iloc[row_idx, col_idx]) if col_idx < len(df_out.columns) else ""
                max_width = max(max_width, min(len(val) + 2, 40))
            worksheet.set_column(col_idx, col_idx, max_width)

        worksheet.freeze_panes(1, 0)
        worksheet.autofilter(0, 0, len(df_out), len(final_cols) - 1)

    def _create_summary_dashboard_sheet(self, writer, statistics: dict):
        workbook: Workbook = writer.book
        worksheet = workbook.add_worksheet("Summary Dashboard")

        header_fmt = workbook.add_format({
            "bg_color": EXCEL_HEADER_BG,
            "bold": True,
            "font_size": 11,
            "border": 1,
        })
        cell_fmt = workbook.add_format({"border": 1})
        num_fmt = workbook.add_format({"border": 1, "num_format": "#,##0"})
        section_fmt = workbook.add_format({
            "bg_color": THEME.get("accent", "#D7E4BC"),
            "bold": True,
            "font_color": "#000000",
            "font_size": 11,
            "border": 1,
        })

        worksheet.write(0, 0, "調貨建議統計 - Summary Dashboard", workbook.add_format({"bold": True, "font_size": 14}))
        worksheet.write(1, 0, f"Version: {VERSION}")

        row = 3
        worksheet.write(row, 0, "KPI", header_fmt)
        worksheet.write(row, 1, "Value", header_fmt)
        row += 1

        kpis = [
            ("Total Recommendations", statistics.get("total_recommendations", 0)),
            ("Total Transfer Qty", statistics.get("total_transfer_qty", 0)),
            ("Unique Articles", statistics.get("unique_articles", 0)),
            ("Unique OMs", statistics.get("unique_oms", 0)),
        ]

        for label, val in kpis:
            worksheet.write(row, 0, label, cell_fmt)
            worksheet.write(row, 1, val, num_fmt)
            row += 1

        row += 1
        sections = [
            ("By Article", "article_stats"),
            ("By OM", "om_stats"),
            ("By Source Type", "source_type_stats"),
            ("By Destination Type", "dest_type_stats"),
            ("By Brand", "brand_stats"),
            ("By Transfer Store Type", "transfer_store_type_stats"),
            ("By Receive Store Type", "receive_store_type_stats"),
            ("By Transfer RP Type", "transfer_rp_type_stats"),
            ("By Receive RP Type", "receive_rp_type_stats"),
        ]

        for title, key in sections:
            stats = statistics.get(key, {})
            if stats:
                row = self._write_stat_section(worksheet, row, title, stats, section_fmt, cell_fmt, num_fmt, key)

        worksheet.set_column(0, 0, 25)
        worksheet.set_column(1, 6, 15)

    def _write_stat_section(self, worksheet, start_row, title, stats, section_fmt, cell_fmt, num_fmt, stats_key=""):
        fields = _STAT_SECTION_FIELDS.get(stats_key, _STAT_SECTION_FIELDS["default"])

        worksheet.merge_range(start_row, 0, start_row, len(fields), title, section_fmt)
        start_row += 1

        for col_idx, (label, _) in enumerate(fields):
            worksheet.write(start_row, col_idx, label, worksheet.workbook.add_format({
                "bold": True, "border": 1, "bg_color": "#E8F0FE",
            }))
        start_row += 1

        for key, data in sorted(stats.items()):
            if not isinstance(data, dict):
                continue
            for col_idx, (_, dict_key) in enumerate(fields):
                val = data.get(dict_key, 0)
                fmt = num_fmt if isinstance(val, (int, float)) else cell_fmt
                if col_idx == 0:
                    worksheet.write(start_row, col_idx, str(key), cell_fmt)
                else:
                    worksheet.write(start_row, col_idx, val, fmt)
            start_row += 1

        return start_row + 1
