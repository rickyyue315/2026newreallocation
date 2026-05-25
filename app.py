import io

import streamlit as st
import pandas as pd

from config import VERSION
from data_processor import DataProcessor
from business_logic import TransferLogic
from services.post_processing import optimize_single_piece_transfers
from services.quality_checks import run_quality_checks
from services.statistics import compute_transfer_statistics
from services.notes import create_recommendation_note
from services.perf_timer import PerfTimer
from ui.styles import apply_styles
from ui.sidebar import render_sidebar
from ui.display import (
    render_upload_requirements,
    render_data_preview,
    render_kpi_cards,
    render_results_table,
    render_statistics,
    render_quality_report,
    render_download_button,
)
from ui.tutorial import render_tutorial_page


st.set_page_config(
    page_title="庫存調貨建議系統",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_styles()


@st.cache_data(show_spinner=False)
def cached_preprocess(file_bytes, file_name):
    processor = DataProcessor()
    df, stats = processor.preprocess_data(io.BytesIO(file_bytes))
    return df, stats


def main():
    tab1, tab2 = st.tabs(["調貨系統", "模式教學"])

    with tab2:
        render_tutorial_page()

    with tab1:
        mode_code, receive_site_limit, f2_hd_transfer = render_sidebar()

        st.title("📦 庫存調貨建議系統")
        st.caption(f"Intelligent Inventory Reallocation System | {VERSION}")

        if "df" not in st.session_state:
            st.session_state.df = None
        if "stats" not in st.session_state:
            st.session_state.stats = None
        if "recommendations" not in st.session_state:
            st.session_state.recommendations = None
        if "statistics" not in st.session_state:
            st.session_state.statistics = None
        if "quality_passed" not in st.session_state:
            st.session_state.quality_passed = True
        if "quality_errors" not in st.session_state:
            st.session_state.quality_errors = []
        if "run_key" not in st.session_state:
            st.session_state.run_key = 0
        if "processing" not in st.session_state:
            st.session_state.processing = False

        render_upload_requirements(mode_code)

        uploaded_file = st.file_uploader(
            "上傳庫存Excel檔案",
            type=["xlsx", "xls"],
            help="支援 .xlsx / .xls 格式，上限50MB",
        )

        if uploaded_file is not None:
            file_bytes = uploaded_file.read()

            if st.button("開始處理調貨建議", type="primary", use_container_width=True):
                st.session_state.processing = True
                st.session_state.run_key += 1

            if st.session_state.processing and st.session_state.run_key > 0:
                progress = st.progress(0, "正在處理...")

                try:
                    progress.progress(10, "讀取與預處理數據...")
                    df, stats = cached_preprocess(file_bytes, uploaded_file.name)
                    st.session_state.df = df
                    st.session_state.stats = stats

                    render_data_preview(df, stats)

                    progress.progress(25, "識別轉出/接收來源...")
                    logic = TransferLogic()

                    progress.progress(40, "執行匹配引擎...")
                    with PerfTimer() as timer:
                        recommendations = logic.generate_transfer_recommendations(
                            df, mode_code,
                            receive_site_limit=receive_site_limit,
                            f2_hd_transfer=f2_hd_transfer,
                        )
                    st.caption(f"匹配完成 ({timer.elapsed:.2f}s)")

                    progress.progress(60, "後處理: 優化單件調貨...")
                    recommendations = optimize_single_piece_transfers(
                        recommendations, mode_code, create_recommendation_note
                    )

                    if recommendations:
                        for rec in recommendations:
                            if not rec.get("Notes"):
                                rec["Notes"] = create_recommendation_note(rec)

                    st.session_state.recommendations = recommendations

                    progress.progress(70, "質量檢查中...")
                    skip_nd = mode_code in ("ND1", "ND2", "F", "F2")
                    passed, errors = run_quality_checks(recommendations, df, skip_nd_check=skip_nd)
                    st.session_state.quality_passed = passed
                    st.session_state.quality_errors = errors

                    progress.progress(80, "計算統計數據...")
                    statistics = compute_transfer_statistics(recommendations)
                    st.session_state.statistics = statistics

                    progress.progress(90, "生成報告...")

                    progress.progress(100, "完成!")
                    st.success(f"處理完成! 共生成 {len(recommendations)} 條調貨建議")

                except ValueError as e:
                    st.error(f"數據錯誤: {e}")
                except Exception as e:
                    st.error(f"處理失敗: {e}")
                    import traceback
                    st.code(traceback.format_exc())
                finally:
                    st.session_state.processing = False

            if st.session_state.recommendations is not None and not st.session_state.processing:
                render_kpi_cards(st.session_state.statistics)
                render_results_table(st.session_state.recommendations)
                render_statistics(st.session_state.statistics)
                render_quality_report(st.session_state.quality_passed, st.session_state.quality_errors)
                render_download_button(st.session_state.recommendations, st.session_state.statistics)


if __name__ == "__main__":
    main()
