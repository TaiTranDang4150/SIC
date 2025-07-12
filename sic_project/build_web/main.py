import streamlit as st
from utils.layout import header
from pages.trangchu import show_home
from pages.phan_tich_xu_huong import show_trend_analysis
from pages.page_chat_bot import show_chat

# Set cấu hình trang
st.set_page_config(page_title="Trang chủ", page_icon="📰", layout="wide")

# Đọc query param
page = st.query_params.get('page', 'trangchu')

# Điều hướng theo page
if page == 'trangchu':
    show_home()
elif page == 'phan_tich_xu_huong':
    show_trend_analysis()
elif page == 'page_chat_bot':
    show_chat()
else:
    st.error('Trang không tồn tại!')
