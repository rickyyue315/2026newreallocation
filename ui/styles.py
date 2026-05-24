import streamlit as st

from config import THEME


def apply_styles():
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700&family=Inter:wght@400;500;600&display=swap');

        .stApp {{
            background-color: {THEME["bg_primary"]};
            color: {THEME["text_primary"]};
            font-family: 'Noto Sans TC', 'Inter', sans-serif;
        }}
        .main .block-container {{
            padding-top: 0.5rem;
            padding-bottom: 2rem;
        }}
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
        }}
        .stTabs [data-baseweb="tab"] {{
            background-color: transparent;
            border-radius: 8px 8px 0px 0px;
            padding: 12px 24px;
            font-weight: 500;
        }}
        .stTabs [aria-selected="true"] {{
            background-color: {THEME["bg_card"]} !important;
            border-bottom: 2px solid {THEME["accent"]};
        }}
        .stButton > button {{
            background: linear-gradient(135deg, {THEME["accent"]}, #00A080);
            color: {THEME["bg_primary"]};
            border-radius: 12px;
            border: none;
            font-weight: 600;
            font-size: 1rem;
            padding: 0.6rem 1.5rem;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(0, 212, 170, 0.3);
        }}
        .stButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 212, 170, 0.4);
            background: linear-gradient(135deg, #00E8BB, {THEME["accent"]});
        }}
        .stDownloadButton > button {{
            background: linear-gradient(135deg, {THEME["success"]}, #059669);
            color: white;
            border-radius: 12px;
            font-weight: 600;
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
        }}
        .stDownloadButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4);
        }}
        .kpi-card {{
            background: linear-gradient(145deg, {THEME["bg_card"]}, {THEME["bg_secondary"]});
            border: 1px solid {THEME["border"]};
            border-radius: 16px;
            padding: 1.5rem;
            text-align: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            transition: all 0.3s ease;
        }}
        .kpi-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.3);
            border-color: {THEME["accent"]};
        }}
        .kpi-value {{
            font-size: 2.5rem;
            font-weight: 700;
            color: {THEME["accent"]};
            font-family: 'Inter', sans-serif;
        }}
        .kpi-label {{
            font-size: 0.9rem;
            color: {THEME["text_secondary"]};
            margin-top: 0.5rem;
            font-weight: 400;
        }}
        .info-card {{
            background: linear-gradient(145deg, {THEME["bg_card"]}, {THEME["bg_secondary"]});
            border: 1px solid {THEME["border"]};
            border-radius: 16px;
            padding: 1.2rem;
            margin-bottom: 1rem;
        }}
        .info-card h3 {{
            color: {THEME["text_primary"]};
            margin: 0 0 0.3rem 0;
            font-size: 1.2rem;
        }}
        .mode-emoji {{
            font-size: 1.5rem;
        }}
        hr {{
            border-color: {THEME["border"]};
            margin: 1rem 0;
        }}
        .stMetric {{
            background: transparent;
        }}
        .stMetric label {{
            color: {THEME["text_secondary"]} !important;
        }}
        .stMetric value {{
            color: {THEME["accent"]} !important;
        }}
        .st-expander {{
            background-color: {THEME["bg_secondary"]};
            border-radius: 12px;
            border: 1px solid {THEME["border"]};
        }}
        .st-expander header {{
            color: {THEME["text_primary"]};
        }}
        .st-expander:hover {{
            border-color: {THEME["accent"]};
        }}
        .stSelectbox [data-baseweb="select"] {{
            background-color: {THEME["bg_card"]};
            border-radius: 10px;
        }}
        .stRadio [data-baseweb="radio-group"] {{
            background-color: {THEME["bg_card"]};
            border-radius: 10px;
            padding: 0.5rem;
        }}
        .stDataFrame {{
            border-radius: 12px;
        }}
        div[data-testid="stExpander"] {{
            border-color: {THEME["border"]};
        }}
        .streamlit-expanderHeader {{
            color: {THEME["text_primary"]};
        }}
        .stAlert {{
            border-radius: 12px;
        }}
        .stSuccess {{
            background-color: rgba(16, 185, 129, 0.15);
            border: 1px solid {THEME["success"]};
        }}
        .stWarning {{
            background-color: rgba(245, 158, 11, 0.15);
            border: 1px solid {THEME["warning"]};
        }}
        .stError {{
            background-color: rgba(239, 68, 68, 0.15);
            border: 1px solid {THEME["danger"]};
        }}
        .stInfo {{
            background-color: rgba(59, 130, 246, 0.15);
            border: 1px solid {THEME["info"]};
        }}
        .stTabs {{
            background-color: transparent;
        }}
        [data-testid="stSidebar"] {{
            background-color: {THEME["bg_secondary"]};
            border-right: 1px solid {THEME["border"]};
        }}
        .stSidebar .st-expander {{
            background-color: transparent;
            border: none;
        }}
        h1, h2, h3, h4 {{
            color: {THEME["text_primary"]};
        }}
        .stCaption {{
            color: {THEME["text_secondary"]};
        }}
        .stFileUploader {{
            background-color: {THEME["bg_card"]};
            border-radius: 12px;
            border: 2px dashed {THEME["border"]};
            padding: 1rem;
        }}
        .stFileUploader:hover {{
            border-color: {THEME["accent"]};
        }}
        .progress-bar {{
            background-color: {THEME["bg_card"]};
            border-radius: 10px;
            height: 8px;
        }}
        div[data-testid="stHorizontalBlock"] {{
            gap: 1rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )