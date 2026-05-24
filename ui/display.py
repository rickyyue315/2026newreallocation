import streamlit as st
import pandas as pd

from config import IS_ZEABUR_RUNTIME, ZEABUR_RESULT_PREVIEW_LIMIT
from excel_generator import ExcelGenerator


def render_upload_requirements(mode_code: str):
    st.markdown("#### 📤 上傳需求")

    base_cols = "Article, OM, RP Type, Site, SaSa Net Stock, Pending Received, Safety Stock, Last Month/MTD Sold Qty, MOQ"

    extra = ""
    if mode_code in ("B2", "B2a", "B2L", "B2La", "B3", "B3a", "B3L", "B3La", "E1b"):
        extra = " + **Type** (T/M/L)"
    elif mode_code in ("E1", "E1b", "E2"):
        extra = " + **ALL** (E模式標記)"
    elif mode_code in ("F", "F2"):
        extra = " + **Target** (目標數量)"
    elif mode_code in ("簡同", "簡跨"):
        extra = " + **Last 2 Month Sold Qty**"

    st.info(f"必填欄位：{base_cols}{extra}")

    article_fmt = "000000000000 (12 digits)"
    st.caption(f"**Article格式**: {article_fmt}")


def render_data_preview(df: pd.DataFrame, stats: dict):
    st.markdown("#### 📊 數據預覽")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("總行數", stats.get("final_rows", len(df)))
    with col2:
        articles = df["Article"].nunique() if "Article" in df.columns else 0
        st.metric("商品數", articles)
    with col3:
        sites = df["Site"].nunique() if "Site" in df.columns else 0
        st.metric("店鋪數", sites)

    with st.expander("查看前10行", expanded=False):
        st.dataframe(df.head(10), use_container_width=True)

    if stats.get("om_filled", 0) > 0:
        st.info(f"已為 {stats['om_filled']} 筆記錄填充 OM 預設值")
    if stats.get("type_filled", 0) > 0:
        st.info(f"已為 {stats['type_filled']} 筆記錄填充 Type 預設值")


def render_kpi_cards(statistics: dict):
    st.markdown("#### 📈 處理結果")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("建議數", statistics.get("total_recommendations", 0))
    with col2:
        st.metric("總件數", statistics.get("total_transfer_qty", 0))
    with col3:
        st.metric("產品數", statistics.get("unique_articles", 0))
    with col4:
        st.metric("OM數", statistics.get("unique_oms", 0))


def render_results_table(recommendations: list):
    st.markdown("#### 📋 調貨建議清單")

    if not recommendations:
        st.warning("無調貨建議")
        return

    df = pd.DataFrame(recommendations)

    display_cols = [
        "Article", "Product Desc",
        "Transfer OM", "Transfer Site", "Receive OM", "Receive Site",
        "Transfer Qty",
        "Remark",
    ]
    display_cols = [c for c in display_cols if c in df.columns]

    limit = ZEABUR_RESULT_PREVIEW_LIMIT if IS_ZEABUR_RUNTIME else None
    if limit and len(df) > limit:
        st.warning(f"結果過多，僅顯示前 {limit} 行 (Zeabur模式)")
        df = df.head(limit)

    st.dataframe(df[display_cols], use_container_width=True, hide_index=True)


def render_statistics(statistics: dict):
    with st.expander("📊 詳細統計", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**按Article**")
            article_stats = statistics.get("article_stats", {})
            if article_stats:
                art_data = []
                for art, data in sorted(article_stats.items(), key=lambda x: -x[1].get("total_qty", 0))[:10]:
                    art_data.append({
                        "Article": art,
                        "Total Qty": data.get("total_qty", 0),
                        "Records": data.get("count", 0),
                    })
                st.dataframe(pd.DataFrame(art_data), use_container_width=True, hide_index=True)

        with col2:
            st.markdown("**按OM**")
            om_stats = statistics.get("om_stats", {})
            if om_stats:
                om_data = []
                for om, data in sorted(om_stats.items(), key=lambda x: -x[1].get("total_qty", 0)):
                    om_data.append({
                        "OM": om,
                        "Transfer Qty": data.get("transfer_qty", 0),
                        "Receive Qty": data.get("receive_qty", 0),
                        "Articles": data.get("article_count", 0),
                    })
                st.dataframe(pd.DataFrame(om_data), use_container_width=True, hide_index=True)

        col3, col4 = st.columns(2)

        with col3:
            st.markdown("**按轉出類型**")
            src_stats = statistics.get("source_type_stats", {})
            if src_stats:
                src_data = []
                for stype, data in sorted(src_stats.items(), key=lambda x: -x[1].get("qty", 0)):
                    src_data.append({
                        "Source Type": stype,
                        "Qty": data.get("qty", 0),
                        "Count": data.get("count", 0),
                    })
                st.dataframe(pd.DataFrame(src_data), use_container_width=True, hide_index=True)

        with col4:
            st.markdown("**按接收類型**")
            dst_stats = statistics.get("dest_type_stats", {})
            if dst_stats:
                dst_data = []
                for dtype, data in sorted(dst_stats.items(), key=lambda x: -x[1].get("qty", 0)):
                    dst_data.append({
                        "Dest Type": dtype,
                        "Qty": data.get("qty", 0),
                        "Count": data.get("count", 0),
                    })
                st.dataframe(pd.DataFrame(dst_data), use_container_width=True, hide_index=True)


def render_quality_report(passed: bool, errors: list):
    with st.expander("🔍 質量檢查", expanded=not passed):
        if passed:
            st.success("所有質量檢查通過!")
        else:
            st.error(f"發現 {len(errors)} 個問題:")
            for err in errors[:20]:
                st.warning(err)
            if len(errors) > 20:
                st.warning(f"...還有 {len(errors) - 20} 個問題")


def render_download_button(recommendations: list, statistics: dict):
    if not recommendations:
        return

    from excel_generator import generate_filename

    generator = ExcelGenerator()
    excel_bytes = generator.generate_excel_file(recommendations, statistics)

    st.download_button(
        label="⬇️ 下載調貨建議Excel",
        data=excel_bytes,
        file_name=generate_filename(),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )