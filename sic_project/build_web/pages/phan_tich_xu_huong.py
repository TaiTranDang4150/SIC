import streamlit as st
from datetime import datetime, timedelta
from utils.load_data import load_news_data
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import altair as alt
import pytz
from pytz import timezone
import matplotlib.pyplot as plt


def show_trend_analysis():
    # Load dữ liệu
    data = load_news_data()
    df = pd.DataFrame(data)
    # Chuyển cột time_posted thành datetime
    df['time_posted'] = pd.to_datetime(df['time_posted'], errors='coerce', utc=True)
    df['time_posted'] = df['time_posted'].dt.tz_convert('Asia/Ho_Chi_Minh').dt.tz_localize(None)

    # Custom CSS cho giao diện đẹp mắt
    st.markdown("""
    <style>
    /* Ẩn navigation menu */
    [data-testid="stSidebarNav"] {
        display: none;
    }
    
    /* Custom header styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    
    .header-title {
        color: white;
        font-size: 2.5rem;
        font-weight: 700;
        text-align: center;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .header-subtitle {
        color: rgba(255,255,255,0.9);
        font-size: 1.2rem;
        text-align: center;
        margin-top: 0.5rem;
    }
    
    .time-display {
        background: rgba(255,255,255,0.2);
        padding: 0.8rem 1.5rem;
        border-radius: 25px;
        color: white;
        font-weight: 600;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.3);
    }
    
    /* Sidebar styling */
    .sidebar-content {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 1.5rem;
        border-radius: 15px;
        margin-bottom: 1rem;
        box-shadow: 0 5px 15px rgba(0,0,0,0.05);
    }
    
    /* Card styling */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
        margin-bottom: 1rem;
    }
    
    .metric-number {
        font-size: 2.5rem;
        font-weight: 700;
        color: #667eea;
        margin: 0;
    }
    
    .metric-label {
        color: #6c757d;
        font-size: 0.9rem;
        margin-top: 0.5rem;
    }
    
    /* Chart container styling */
    .chart-container {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        margin-bottom: 2rem;
    }
    
    .chart-title {
        font-size: 1.5rem;
        font-weight: 600;
        color: #2c3e50;
        margin-bottom: 1rem;
        text-align: center;
    }
    
    /* Animation for cards */
    .metric-card:hover {
        transform: translateY(-5px);
        transition: all 0.3s ease;
        box-shadow: 0 8px 30px rgba(0,0,0,0.15);
    }
    
    /* Responsive design */
    @media (max-width: 768px) {
        .header-title {
            font-size: 2rem;
        }
        .main-header {
            padding: 1rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    # Header section với thiết kế đẹp mắt
    st.markdown('<div class="main-header">', unsafe_allow_html=True)
    
    col_logo, col_center, col_time = st.columns([1, 2, 1])
    
    with col_logo:
        try:
            st.image("C:\\Users\\Admin\\Downloads\\anh_logo_meo.jpg", width=120)
        except:
            st.markdown("📰", unsafe_allow_html=True)
    
    with col_center:
        st.markdown('<h1 class="header-title">📰 Báo Điện Tử</h1>', unsafe_allow_html=True)
        st.markdown('<p class="header-subtitle">Phân tích xu hướng tin tức thông minh</p>', unsafe_allow_html=True)
    
    with col_time:
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        current_date = now.strftime("%d/%m/%Y")
        st.markdown(f'<div class="time-display">🕐 {current_time}<br>📅 {current_date}</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

    # Sidebar với thiết kế đẹp mắt
    with st.sidebar:
        st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
        
        # Logo nhỏ trong sidebar
        st.markdown("### 📊 Bộ lọc thời gian")
        st.markdown("---")
        
        # Danh sách mốc thời gian với emoji
        time_range_options = {
            '24 giờ qua': '🕐',
            '7 ngày qua': '📅', 
            '1 tháng qua': '🗓️'
        }
        
        selected_time_range = st.selectbox(
            'Chọn khoảng thời gian',
            list(time_range_options.keys()),
            format_func=lambda x: f"{time_range_options[x]} {x}"
        )

        st.markdown("### 🎨 Chủ đề màu sắc")
        
        # Chọn kiểu màu sắc hiển thị với preview
        color_theme_options = {
            'viridis': '🟢',
            'plasma': '🟣',
            'inferno': '🔥',
            'magma': '🌋',
            'cividis': '🔵',
            'turbo': '🌈',
            'greens': '🌿',
            'reds': '🔴',
            'rainbow': '🎨'
        }
        
        selected_color_theme = st.selectbox(
            'Chọn bảng màu',
            list(color_theme_options.keys()),
            format_func=lambda x: f"{color_theme_options[x]} {x.title()}"
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Thông tin thống kê nhanh
        st.markdown("### 📈 Thống kê tổng quan")
        total_articles = len(df)
        st.metric("📰 Tổng bài báo", total_articles, delta="100%")
        
        # Tính toán bài báo trong 24h
        recent_articles = len(df[df['time_posted'] >= now - timedelta(days=1)])
        st.metric("🕐 24h gần nhất", recent_articles, delta=f"{recent_articles - total_articles//30} so với TB")

    # Main content area
    st.markdown("## 📊 Phân tích xu hướng tin tức")
    
    # Gọi hàm phân tích với giao diện đẹp mắt
    line_chart_analytic(df, selected_time_range, selected_color_theme)


def line_chart_analytic(df, selected_time_range, selected_color_theme):
    import pandas as pd
    from datetime import datetime, timedelta

    # Bộ lọc thời gian
    now = datetime.now()
    if selected_time_range == '24 giờ qua':
        filtered_df = df[df['time_posted'] >= now - timedelta(days=1)]
        time_unit = 'hour'
    elif selected_time_range == '7 ngày qua':
        filtered_df = df[df['time_posted'] >= now - timedelta(days=7)]
        time_unit = 'day'
    else:
        filtered_df = df[df['time_posted'] >= now - timedelta(days=30)]
        time_unit = 'day'

    # Tạo cột thời gian phù hợp
    if time_unit == 'hour':
        filtered_df['time_group'] = filtered_df['time_posted'].dt.floor('H')
        time_format = '%H:%M - %d/%m'
    else:
        filtered_df['time_group'] = filtered_df['time_posted'].dt.date
        time_format = '%d/%m/%Y'

    time_count = filtered_df.groupby('time_group').size().reset_index(name='num_articles')

    if time_count.empty:
        st.error("⚠️ Không có dữ liệu trong khoảng thời gian được chọn.")
        return

    # Biểu đồ số lượng bài báo với thiết kế đẹp mắt
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown('<h3 class="chart-title">📈 Xu hướng số lượng bài báo</h3>', unsafe_allow_html=True)
    
    # Tạo biểu đồ với gradient và animation
    fig_time = go.Figure()
    
    fig_time.add_trace(go.Scatter(
        x=time_count['time_group'],
        y=time_count['num_articles'],
        mode='lines+markers',
        name='Số bài báo',
        line=dict(
            color='rgba(102, 126, 234, 0.8)',
            width=3,
            shape='spline'
        ),
        marker=dict(
            size=8,
            color='rgba(102, 126, 234, 1)',
            line=dict(color='white', width=2)
        ),
        fill='tonexty',
        fillcolor='rgba(102, 126, 234, 0.1)',
        hovertemplate='<b>%{x}</b><br>Số bài báo: %{y}<extra></extra>'
    ))
    
    fig_time.update_layout(
        title='',
        xaxis_title='Thời gian',
        yaxis_title='Số lượng bài báo',
        template='plotly_white',
        height=400,
        showlegend=False,
        hovermode='x unified',
        xaxis=dict(
            showgrid=True,
            gridcolor='rgba(0,0,0,0.1)',
            showline=True,
            linecolor='rgba(0,0,0,0.2)'
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='rgba(0,0,0,0.1)',
            showline=True,
            linecolor='rgba(0,0,0,0.2)'
        )
    )
    
    st.plotly_chart(fig_time, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Metrics cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown(f'<p class="metric-number">{len(filtered_df)}</p>', unsafe_allow_html=True)
        st.markdown('<p class="metric-label">📰 Tổng bài báo</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        avg_daily = round(len(filtered_df) / max(1, len(time_count)), 1)
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown(f'<p class="metric-number">{avg_daily}</p>', unsafe_allow_html=True)
        st.markdown('<p class="metric-label">📊 Trung bình/ngày</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        max_articles = time_count['num_articles'].max()
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown(f'<p class="metric-number">{max_articles}</p>', unsafe_allow_html=True)
        st.markdown('<p class="metric-label">🔥 Cao nhất</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        unique_categories = len(filtered_df['tags'].explode().unique())
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown(f'<p class="metric-number">{unique_categories}</p>', unsafe_allow_html=True)
        st.markdown('<p class="metric-label">🏷️ Chuyên mục</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Biểu đồ chuyên mục
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown('<h3 class="chart-title">🏆 Top 10 Chuyên mục nổi bật</h3>', unsafe_allow_html=True)

    # Đếm số lượng chuyên mục
    category_count = (
        filtered_df['tags']
        .explode()
        .value_counts()
        .head(10)
        .reset_index()
    )
    category_count.columns = ['Category', 'Count']

    if len(category_count) > 0:
        fig_category = px.bar(
            category_count,
            x='Count',
            y='Category',
            title='',
            color='Count',
            color_continuous_scale=selected_color_theme,
            orientation='h'
        )
        
        fig_category.update_layout(
            yaxis={'categoryorder': 'total ascending'},
            xaxis_title='Số lượng bài viết',
            yaxis_title='',
            template='plotly_white',
            height=500,
            showlegend=False
        )
        
        fig_category.update_traces(
            hovertemplate='<b>%{y}</b><br>Số bài viết: %{x}<extra></extra>'
        )
        
        st.plotly_chart(fig_category, use_container_width=True)
    else:
        st.info("📭 Không có dữ liệu phân loại chuyên mục.")
    
    st.markdown('</div>', unsafe_allow_html=True)

    # Phân tích thực thể NER
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown('<h3 class="chart-title">🔍 Phân tích thực thể được nhắc đến nhiều nhất</h3>', unsafe_allow_html=True)

    # Xử lý dữ liệu thực thể
    all_entities = []
    for entities in filtered_df['popular_tags']:
        if isinstance(entities, list):
            all_entities.extend(entities)

    if all_entities:
        entity_df = pd.DataFrame(all_entities, columns=['Entity', 'Type'])
        
        # Tạo tabs cho các loại thực thể
        tab1, tab2, tab3 = st.tabs(["👤 Nhân vật", "📍 Địa điểm", "🏢 Tổ chức"])
        
        entity_types = [('PER', '👤'), ('LOC', '📍'), ('ORG', '🏢')]
        tabs = [tab1, tab2, tab3]
        
        for idx, (entity_type, emoji) in enumerate(entity_types):
            with tabs[idx]:
                df_entity = entity_df[entity_df['Type'] == entity_type]
                
                if len(df_entity) > 0:
                    entity_count = df_entity['Entity'].value_counts().head(10).reset_index()
                    entity_count.columns = ['Entity', 'Count']
                    
                    fig = px.bar(
                        entity_count,
                        y='Entity',
                        x='Count',
                        title=f'{emoji} Top 10 {entity_type} được nhắc đến',
                        color='Count',
                        color_continuous_scale=selected_color_theme,
                        orientation='h'
                    )
                    
                    fig.update_layout(
                        yaxis={'categoryorder': 'total ascending'},
                        xaxis_title='Số lần nhắc đến',
                        yaxis_title='',
                        template='plotly_white',
                        height=400,
                        showlegend=False
                    )
                    
                    fig.update_traces(
                        hovertemplate='<b>%{y}</b><br>Số lần nhắc: %{x}<extra></extra>'
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info(f"{emoji} Không có dữ liệu cho nhóm {entity_type}")
    else:
        st.info("📭 Không có dữ liệu thực thể để hiển thị.")
    
    st.markdown('</div>', unsafe_allow_html=True)

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #6c757d; padding: 2rem;'>
            <p>📰 <strong>Báo Điện Tử</strong> - Phân tích xu hướng tin tức thông minh</p>
            <p>Cập nhật lần cuối: {}</p>
        </div>
        """.format(datetime.now().strftime("%H:%M:%S - %d/%m/%Y")),
        unsafe_allow_html=True
    )