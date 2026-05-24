import streamlit as st

from config import THEME


def apply_styles():
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700&family=Inter:wght@400;500;600;700&display=swap');

        html, body, .stApp {{
            background-color: {THEME["bg_primary"]} !important;
            color: {THEME["text_primary"]} !important;
            font-family: 'Noto Sans TC', 'Inter', sans-serif;
        }}
        .stApp {{
            background-color: {THEME["bg_primary"]};
        }}
        .main .block-container {{
            padding-top: 0.3rem;
            padding-bottom: 1rem;
            padding-left: 1rem;
            padding-right: 1rem;
            max-width: 100%;
            background-color: {THEME["bg_primary"]};
        }}
        [data-testid="stMainBlockContainer"] {{
            background-color: {THEME["bg_primary"]};
        }}
        .stTabs [data-baseweb="tab-list"] {{
            gap: 6px;
            background-color: {THEME["bg_secondary"]};
            padding: 4px;
            border-radius: 10px;
        }}
        .stTabs [data-baseweb="tab"] {{
            background-color: transparent;
            border-radius: 8px;
            padding: 10px 20px;
            font-weight: 500;
            color: {THEME["text_secondary"]};
        }}
        .stTabs [aria-selected="true"] {{
            background-color: {THEME["bg_card"]} !important;
            color: {THEME["accent"]} !important;
        }}
        .stButton > button {{
            background: linear-gradient(135deg, {THEME["accent"]}, #00CC96);
            color: {THEME["bg_primary"]};
            border-radius: 10px;
            border: none;
            font-weight: 700;
            font-size: 1rem;
            padding: 0.5rem 1.2rem;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(0, 255, 185, 0.3);
            width: 100%;
        }}
        .stButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 255, 185, 0.5);
        }}
        .stDownloadButton > button {{
            background: linear-gradient(135deg, {THEME["success"]}, #0891B2);
            color: {THEME["bg_primary"]};
            border-radius: 10px;
            font-weight: 700;
            box-shadow: 0 4px 15px rgba(34, 211, 238, 0.3);
            width: 100%;
        }}
        .stDownloadButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(34, 211, 238, 0.5);
        }}
        .kpi-card {{
            background: {THEME["bg_card"]};
            border: 1px solid {THEME["border"]};
            border-radius: 12px;
            padding: 1rem 0.5rem;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }}
        .kpi-value {{
            font-size: 2rem;
            font-weight: 700;
            color: {THEME["accent"]};
            font-family: 'Inter', sans-serif;
        }}
        .kpi-label {{
            font-size: 0.85rem;
            color: {THEME["text_secondary"]};
            margin-top: 0.3rem;
            font-weight: 500;
        }}
        .info-card {{
            background: {THEME["bg_card"]};
            border: 1px solid {THEME["border"]};
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 0.8rem;
        }}
        .info-card h3 {{
            color: {THEME["text_primary"]};
            margin: 0 0 0.3rem 0;
            font-size: 1.1rem;
        }}
        hr {{
            border-color: {THEME["border"]};
            margin: 0.6rem 0;
        }}
        .stMetric label {{
            color: {THEME["text_primary"]} !important;
            font-weight: 600 !important;
        }}
        .stMetric value {{
            color: {THEME["accent"]} !important;
            font-weight: 700;
        }}
        .st-expander {{
            background-color: {THEME["bg_secondary"]};
            border-radius: 10px;
            border: 1px solid {THEME["border"]};
        }}
        .st-expander header {{
            color: {THEME["text_primary"]};
            font-weight: 500;
        }}
        [data-testid="stExpander"] {{
            background-color: {THEME["bg_secondary"]} !important;
        }}
        [data-testid="stExpanderContent"] {{
            background-color: {THEME["bg_secondary"]} !important;
        }}
        .stSelectbox label {{
            color: {THEME["text_primary"]} !important;
        }}
        .stSelectbox [data-baseweb="select"] {{
            background-color: {THEME["bg_card"]} !important;
        }}
        .stRadio label {{
            color: {THEME["text_primary"]} !important;
        }}
        [data-testid="stSidebar"] {{
            background-color: {THEME["bg_secondary"]} !important;
            border-right: 1px solid {THEME["border"]};
            padding-top: 1rem;
        }}
        [data-testid="stSidebar"] .stMarkdown {{
            color: {THEME["text_primary"]};
        }}
        [data-testid="stSidebar"] h3 {{
            color: {THEME["accent"]};
        }}
        h1, h2, h3, h4, h5, h6 {{
            color: {THEME["text_primary"]} !important;
        }}
        h1 {{ font-size: 1.5rem; margin-bottom: 0.3rem; color: {THEME["accent"]} !important; }}
        h2 {{ font-size: 1.2rem; margin-top: 0.5rem; margin-bottom: 0.3rem; }}
        h3 {{ font-size: 1rem; margin-top: 0.3rem; }}
        h4 {{ font-size: 0.9rem; margin-top: 0.2rem; }}
        .stCaption {{
            color: {THEME["text_secondary"]} !important;
        }}
        .stFileUploader {{
            background-color: {THEME["bg_card"]};
            border-radius: 10px;
            border: 2px dashed {THEME["border"]} !important;
            padding: 0.8rem;
        }}
        .stAlert {{
            border-radius: 10px;
            border: none;
        }}
        .stSuccess, [data-testid="stSuccess"] {{
            background-color: rgba(34, 211, 238, 0.2) !important;
            color: #FFFFFF !important;
        }}
        .stWarning, [data-testid="stWarning"] {{
            background-color: rgba(251, 191, 36, 0.2) !important;
            color: #FFFFFF !important;
        }}
        .stError, [data-testid="stError"] {{
            background-color: rgba(248, 113, 113, 0.2) !important;
            color: #FFFFFF !important;
        }}
        .stInfo, [data-testid="stInfo"] {{
            background-color: rgba(96, 165, 250, 0.2) !important;
            color: #FFFFFF !important;
        }}
        section[data-testid="stHorizontalBlock"] > div {{
            background-color: {THEME["bg_card"]};
            border-radius: 10px;
            padding: 0.8rem;
            border: 1px solid {THEME["border"]};
        }}
        .streamlit-expanderHeader {{
            color: {THEME["text_primary"]} !important;
        }}
        div[data-testid="stHorizontalBlock"] {{
            gap: 0.8rem;
        }}
        .stTable {{
            background-color: {THEME["bg_card"]} !important;
            border-radius: 10px;
        }}
        .stTable th {{
            background-color: {THEME["bg_secondary"]} !important;
            color: {THEME["accent"]} !important;
        }}
        .stTable td {{
            color: {THEME["text_primary"]} !important;
        }}
        table {{
            background-color: {THEME["bg_card"]} !important;
            color: {THEME["text_primary"]} !important;
        }}
        th, td {{
            background-color: {THEME["bg_card"]} !important;
            color: {THEME["text_primary"]} !important;
            border-color: {THEME["border"]} !important;
        }}
        thead {{
            background-color: {THEME["bg_secondary"]} !important;
        }}
        thead th {{
            color: {THEME["accent"]} !important;
        }}
        [data-testid="stDataFrame"] {{
            background-color: {THEME["bg_card"]} !important;
        }}
        .dataframe {{
            background-color: {THEME["bg_card"]} !important;
        }}
        .dataframe thead {{
            background-color: {THEME["bg_secondary"]} !important;
        }}
        .dataframe th {{
            color: {THEME["accent"]} !important;
        }}
        .dataframe td {{
            color: {THEME["text_primary"]} !important;
        }}
        .stProgress bar {{
            background-color: {THEME["accent"]};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )