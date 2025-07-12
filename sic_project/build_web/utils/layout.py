import streamlit as st
from datetime import datetime

def header():
    hide_sidebar = """
        <style>
        [data-testid="stSidebar"] {display: none;}
        [data-testid="collapsedControl"] {display: none;}
        </style>
    """
    st.markdown(hide_sidebar, unsafe_allow_html=True)
    
    col_logo, col_time = st.columns([2, 1])

    with col_logo:
        st.image("C:\\Users\\Admin\\Downloads\\anh_logo_meo.jpg", width=150)
        st.markdown("<h2 style='color:#2c3e50;'>📰 Báo Điện Tử</h2>", unsafe_allow_html=True)

    with col_time:
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S - %d/%m/%Y")
        st.markdown(f"<h4 style='text-align:right; color: #2c3e50;'>⏰ {current_time}</h4>", unsafe_allow_html=True)

    # st.image("assets/banner.png", use_column_width=True)
    st.markdown("---")

def menu():
    st.sidebar.page_link("pages/trangchu.py", label="Trang chủ", icon="🏠")
