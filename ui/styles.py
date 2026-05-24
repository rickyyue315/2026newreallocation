import streamlit as st

from config import THEME


def apply_styles():
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {THEME["bg_primary"]};
            color: {THEME["text_primary"]};
        }}
        .main .block-container {{
            padding-top: 1rem;
        }}
        .stButton > button {{
            background-color: {THEME["accent"]};
            color: white;
            border-radius: 8px;
            border: none;
            font-weight: 600;
            transition: all 0.3s;
        }}
        .stButton > button:hover {{
            background-color: #d48f1e;
            transform: translateY(-1px);
        }}
        .kpi-card {{
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            border: 1px solid #2a2a4a;
            border-radius: 12px;
            padding: 1.2rem;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }}
        .kpi-value {{
            font-size: 2rem;
            font-weight: 700;
            color: {THEME["accent"]};
        }}
        .kpi-label {{
            font-size: 0.85rem;
            color: {THEME["text_secondary"]};
            margin-top: 0.3rem;
        }}
        .info-card {{
            background: linear-gradient(135deg, #1e293b, #0f172a);
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 0.8rem;
        }}
        .mode-emoji {{
            font-size: 1.5rem;
        }}
        hr {{
            border-color: #2a2a4a;
        }}
        .stDownloadButton > button {{
            background-color: {THEME["success"]};
            color: white;
            border-radius: 8px;
            font-weight: 600;
        }}
        .stDownloadButton > button:hover {{
            background-color: #0d9668;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
