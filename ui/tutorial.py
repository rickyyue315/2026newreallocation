import streamlit as st


def render_tutorial_page():
    st.markdown("#### 📚 模式教學 - 24種調貨模式完整說明")

    with st.expander("🌐 全局規則 (All Modes)", expanded=False):
        st.markdown("""
        **全局業務規則**

        1. **ND店舖限制**: ND只能作為轉出來源(SOURCE)，不可作為接收方(DESTINATION)
           - 例外: ND1/ND2/F/F2模式可讓ND接收
        2. **最高動銷店保護**: 每個(Article,OM)組中銷量最高的RF不作為轉出源
        3. **禁止雙重角色**: 同一(Article,Site)不能同時轉出和接收
        4. **不可自己轉自己**: source.site != dest.site
        5. **HD→HK限制**: 澳門(HD)不能轉香港(HA/HB/HC)
        6. **Windy限制**: Windy OM只能轉Windy OM
        7. **單件消除**: 後處理自動消除Transfer Qty=1的記錄

        **轉出上限速查**

        | 模式 | 上限公式 | 下限 |
        |------|---------|------|
        | A | min(20%×Total, NetStock) | 2 |
        | B | min(50%×Total, NetStock) | 2 |
        | C | min(30%×Total, 3, NetStock) | 1 |
        | C1 | min(30%×Total, 3, NetStock) | 2 |
        | E | 全數轉出 | - |
        | F | 全數轉出(Target有值除外) | - |
        | ND | 全數轉出 | - |
        | 精簡SKU | 超出2×Safety/Last2Month | - |
        """)

    with st.expander("📦 基本模式: A/B", expanded=False):
        st.markdown("""
        **模式A: 保守轉貨**
        - **上限**: 20% of Total Available (至少2件)
        - **限制**: 轉後必須保持≥Safety Stock
        - **場景**: 日常保守補貨，庫存充足

        **模式B: 加強轉貨**
        - **上限**: 50% of Total Available (至少2件)
        - **限制**: 可低於Safety Stock
        - **場景**: 積極補貨，快速分配庫存

        **A vs B 對比**

        | 項目 | A模式 | B模式 |
        |------|-------|-------|
        | 庫存上限 | 20% | 50% |
        | Safety限制 | 必須保持 | 可低於 |
        | 適用場景 | 保守 | 積極 |
        """)

    with st.expander("🔧 B2系列: 特別模式 (B2/B2a/B2L/B2La)", expanded=False):
        st.markdown("""
        **B2: 附加B(特別模式)**
        - **特點**: Type L低銷店全轉出
        - **條件**: max(LastMonth, MTD) ≤ 2
        - **接收上限**: max(Safety×2, 3)

        **B2a: T不出貨**
        - B2規則 + Type T不可作為轉出源

        **B2L: L保留2**
        - Type L低銷保留2件: max(NetStock - 2, 0)

        **B2La: L保留2 + T不出**
        - 組合限制

        **B2系列接收優先級**
        1. Type T + sales>0 (遊客高銷量)
        2. Type M + sales>0 (混合高銷量)
        3. Type T + sales=0 (遊客Safety優先)
        4. Type M + sales=0 (混合Safety優先)
        """)

    with st.expander("🌍 B3系列: 跨OM特別模式 (B3/B3a/B3L/B3La)", expanded=False):
        st.markdown("""
        **B3/B3a/B3L/B3La: 跨OM特別模式**
        - **跨OM**: cross_om_grouping + cross_om_matching
        - **特殊**: 同OM也檢查HD/Windy限制
        - **B3a**: T不出貨
        - **B3L**: L保留2
        - **B3La**: L保留2 + T不出

        **8回合匹配順序**
        1. ND(1) → P1 dest
        2. ND(1) → P2 dest
        3. RF過剩(2) → P1
        4. RF過剩(2) → P2
        5. Local全轉出(2) → P1
        6. Local全轉出(2) → P2
        7. RF加強(2) → P1
        8. RF加強(2) → P2
        """)

    with st.expander("🎯 C系列: 重點補0 (C/C1/C2)", expanded=False):
        st.markdown("""
        **C: 重點補0**
        - **轉出**: 30%上限, 最多3件, 至少1件
        - **接收**: 總可用≤1 + Safety>0或EffSold>0 → 需補max(Safety×0.5, 3)
        - **9回合**: ND/RF過剩/RF加強 × 重點補0/緊急/潛在

        **C1: 重點補0-只補0/1**
        - **轉出**: 庫存>2才轉, 至少2件
        - **接收**: 僅總可用≤1 (重點補0)
        - **不回落**: 不回落到緊急/潛在

        **C2: 跨OM重點補0**
        - C模式 + 跨OM匹配
        - HD/Windy限制
        """)

    with st.expander("🧹 D系列: 清貨轉貨 (D/D2)", expanded=False):
        st.markdown("""
        **D: 清貨轉貨**
        - **ND清貨**: 無銷售(LastMonth=0, MTD=0) ND全轉出
        - **有銷售ND**: 正常ND轉出
        - **RF**: 同A模式嚴格限制
        - **餘貨調整**: 避免1件, 調整±1

        **D2: ND限定清貨**
        - 僅無銷售ND可轉出
        - RF完全不轉出
        - 有銷售ND也不轉出
        """)

    with st.expander("⚡ E系列: 強制轉出 (E1/E1b/E2)", expanded=False):
        st.markdown("""
        **E1: 強制轉出(同OM)**
        - **觸發**: ALL欄位有值
        - **轉出**: 全數轉出, 不分ND/RF
        - **接收**: RF, 上限max(Safety×2, 3)
        - **限制**: 僅同OM, HD限制

        **E1b: 優先類型**
        - E1 + Type排序:
          1. T型高銷量 2. M型高銷量
          3. T型Safety 4. M型Safety 5. 其他

        **E2: 跨OM強制轉出**
        - **Phase 1**: 同OM優先
        - **Phase 2**: 跨OM回退 (HD/Windy限制)
        - **Phase 3**: C模式回退 (非E-mode OMs的RF源)
        """)

    with st.expander("🎯 F系列: 目標優化 (F/F2)", expanded=False):
        st.markdown("""
        **F: 目標優化**
        - **Target驅動**: 解析Target數值
        - **轉出**: ND/RF全轉 (Target有值店除外)
        - **P1接收**: Target目標接收
        - **P2補0**: 總可用≤1, max(Safety×0.5, 3) (僅F)

        **F2: F指定模式**
        - 僅P1接收 (無P2補0)
        - **target_stores**: 全域Any Target>0的店都不做source
        - **Windy penalty=5**: 非Windy源→Windy目標降優先級
        - **HD penalty=10**: HD→HK降優先級 (需開啟HD可轉出)
        """)

    with st.expander("📋 ND & 精簡SKU模式", expanded=False):
        st.markdown("""
        **ND1: ND同OM轉貨**
        - **ND可接收**: 打破常規限制
        - **轉出**: 保護最高銷量ND, 0銷優先
        - **接收**:
          - P1: RF緊急缺貨 (零庫存+有銷售)
          - P2: ND潛在缺貨 (上限=2×銷量)

        **ND2: ND混合OM轉貨**
        - ND1 + 跨OM (Windy/HD限制)

        **精簡SKU(限同OM)**
        - **Cap**: max(Safety×2, Last2Month×2)
        - **轉出**: 超出Cap部分
        - **最少2件起轉**
        - D001退回: 未配對庫存標記退回

        **精簡SKU(跨OM)**
        - 跨OM版本 + HD/Windy限制
        """)

    st.markdown("---")
    st.markdown("#### 🎯 決策指南")

    decision_data = [
        ["日常補貨", "A", "保守, 20%上限"],
        ["加速去庫存", "B", "積極, 50%上限"],
        ["解決零庫存", "C", "高優先級, 30%限3"],
        ["區域清貨", "D", "無銷售ND處理"],
        ["強制調撥", "E1", "ALL標記, 同OM"],
        ["目標分配", "F", "Target精準控制"],
        ["ND內部調度", "ND1", "ND可雙向流動"],
        ["簡化庫存管理", "簡同", "簡化SKU邏輯"],
    ]

    st.table(
        {"場景": [r[0] for r in decision_data],
         "推薦模式": [r[1] for r in decision_data],
         "說明": [r[2] for r in decision_data]}
    )

    st.markdown("#### 📊 24模式完整對比")
    st.markdown("""
    | 模式 | 跨OM | 特別策略 | 接收限制 | 轉出上限 |
    |------|------|---------|---------|---------|
    | A | N | - | - | 20% |
    | B | N | - | - | 50% |
    | B2 | N | B Special | Y(S×2) | 50%+Low全轉 |
    | C | N | - | - | 30%(max3) |
    | C1 | N | - | - | 30%(max3) |
    | D | N | - | - | 20% |
    | E1 | N | E1 Strategy | Y(S×2) | 全轉 |
    | E2 | Y | E2 3-Phase | Y(S×2) | 全轉+C回退 |
    | F | Y | F Strategy | - | 全轉(P2同OM) |
    | F2 | Y | F(penalty) | - | 全轉(無P2) |
    | ND1 | N | ND Dest-first | Y(銷×2) | 全轉 |
    | ND2 | Y | ND+跨OM | Y(銷×2) | 全轉 |
    | 簡同 | N | SKU Min2 | - | 超出Cap |
    | 簡跨 | Y | SKU+跨OM | - | 超出Cap |
    """)