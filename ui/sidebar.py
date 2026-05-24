import streamlit as st

from config import VERSION, MODE_OPTIONS
from models.mode_registry import MODE_REGISTRY


def render_sidebar() -> tuple[str, int | None, bool]:
    with st.sidebar:
        st.markdown(
            f"""
            <div class="info-card">
                <h3>庫存調貨建議系統</h3>
                <p style="color:#9CA3AF;font-size:0.85rem;">Intelligent Inventory Reallocation</p>
                <p style="color:#F5A623;font-size:0.8rem;margin:0;">Version {VERSION} | Ricky Yue</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander("核心功能", expanded=False):
            st.markdown("""
            - **24種調貨模式**: A/B/C/D/E/F/ND/精簡SKU
            - **智能識別**: 自動標記ND清貨/RF過剩/重點補0
            - **跨OM限制**: HD→HK不可, Windy只轉Windy
            - **自動化**: 單件消除、質量檢查、統計生成
            """)

        with st.expander("操作指引", expanded=False):
            st.markdown("""
            1. **上傳檔案**: Excel (.xlsx/.xls)
            2. **選擇模式**: 從24種模式中選擇
            3. **啟動處理**: 點擊執行按鈕
            4. **查看結果**: KPI及詳細表格
            5. **下載報告**: Excel格式輸出
            """)

        st.markdown("---")

        selected_option = st.selectbox(
            "調貨模式",
            MODE_OPTIONS,
            index=0,
            help="選擇調貨模式，詳見模式說明",
        )

        mode_code = selected_option.split(":")[0].strip()

        receive_limit = None
        f2_hd_transfer = False

        mode_def = MODE_REGISTRY.get(mode_code)
        if mode_def and mode_def.receive_site_limit:
            limit_choice = st.radio(
                "接收店數限制",
                ["優先1間", "最多2間", "不限制"],
                index=2,
                horizontal=True,
                help="限制每個Article的接收店數量",
            )
            limit_map = {"優先1間": 1, "最多2間": 2, "不限制": None}
            receive_limit = limit_map.get(limit_choice)

        if mode_code == "F2":
            hd_choice = st.radio(
                "HD澳門轉出設定",
                ["HD不能轉出", "HD可轉出(最後優先)"],
                index=0,
                horizontal=True,
                help="控制澳門(HD)店舖是否可以作為轉出來源",
            )
            f2_hd_transfer = hd_choice == "HD可轉出(最後優先)"

        with st.expander("模式說明", expanded=False):
            mode_desc = _get_mode_in_description(mode_code)
            st.markdown(mode_desc)

    return mode_code, receive_limit, f2_hd_transfer


def _get_mode_in_description(mode_code: str) -> str:
    descriptions = {
        "A": "**保守轉貨**\n- 20%庫存上限，至少2件\n- 嚴格保持Safety Stock\n- 適用：基本補貨場景",
        "B": "**加強轉貨**\n- 50%庫存上限，至少2件\n- 可低於Safety Stock\n- 適用：積極補貨場景",
        "B2": "**附加B(特別模式)**\n- B模式基礎 + Type L低銷全轉出\n- 接收上限：Safety×2, 至少3件\n- 適用：低銷店清理",
        "B2a": "**附加B2a(T不出貨)**\n- B2模式 + Type T不可轉出\n- 適用：保護遊客區店舖",
        "B2L": "**附加B2L(L保留2)**\n- Type L低銷保留2件\n- 適用：保留基本庫存",
        "B2La": "**附加B2La(L2+T不出)**\n- L保留2件 + T不出貨",
        "B3": "**附加B3(跨OM)**\n- 跨OM匹配，HD/Windy限制\n- 同OM也檢查跨OM規則",
        "B3a": "**附加B3a(跨OM+T不出)**\n- B3 + T不可轉出",
        "B3L": "**附加B3L(跨OM+L2)**\n- 跨OM + L保留2件",
        "B3La": "**附加B3La(跨OM+L2+T)**\n- 跨OM + L保留2件 + T不出",
        "C": "**重點補0**\n- 30%/3件上限\n- 優先補充零庫存+有銷售店\n- 9回合匹配",
        "C1": "**重點補0-只補0/1**\n- 僅補總可用≤1的店\n- 庫存>2才轉出，至少2件\n- 不回落緊急/潛在",
        "C2": "**附加C2(跨OM)**\n- 跨OM重點補0\n- HD/Windy限制",
        "D": "**清貨轉貨**\n- 無銷售ND全轉出\n- 避免1件餘貨\n- 接收：最小2件",
        "D2": "**清貨轉貨(ND限定)**\n- 僅無銷售ND可轉出\n- RF完全不轉出",
        "E1": "**強制轉出(同OM)**\n- ALL標記強制轉出\n- 僅同OM配對\n- 接收上限：Safety×2",
        "E1b": "**強制轉出(優先類型)**\n- T/M型店優先接收\n- 嚴格按優先級排序",
        "E2": "**強制轉出(跨OM)**\n- 3-Phase回退機制\n- Phase3: C模式回退\n- 跨OM + HD/Windy限制",
        "F": "**目標優化**\n- Target驅動轉移\n- 含補0邏輯(P2)\n- ND/F模式跳過ND檢查",
        "F2": "**F指定模式**\n- Target驅動無補0\n- HD可轉出選項\n- Windy penalty=5, HD penalty=10",
        "ND1": "**ND同OM轉貨**\n- ND可轉入/轉出\n- 保護最高銷量ND\n- 接收上限：銷量×2",
        "ND2": "**ND混合OM轉貨**\n- 跨OM ND轉貨\n- HD/Windy限制",
        "簡同": "**精簡SKU(限同OM)**\n- Cap=2×Safety或Last2Month\n- 最少2件起轉",
        "簡跨": "**精簡SKU(跨OM)**\n- 跨OM精簡SKU\n- HD/Windy限制",
    }
    return descriptions.get(mode_code, f"模式 {mode_code} 說明待補充")
