import streamlit as st
from utils.layout import header
from utils.load_data import load_news_data
import random
from pathlib import Path

# ==== Hàm hiển thị ảnh an toàn ====
def show_image(image_path):
    if not image_path:
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 200px;
            border-radius: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 1.2rem;
            margin-bottom: 1rem;
        ">
            📰 Không có ảnh
        </div>
        """, unsafe_allow_html=True)
        return

    # Kiểm tra nếu là URL
    if isinstance(image_path, str) and (image_path.startswith("http://") or image_path.startswith("https://")):
        try:
            st.image(image_path, use_container_width=True)
        except Exception as e:
            st.warning(f"Không thể load ảnh: {e}")
    else:
        # Kiểm tra file local
        image_file = Path(image_path)
        if image_file.exists():
            try:
                st.image(str(image_file), use_container_width=True)
            except Exception as e:
                st.warning(f"Không thể load ảnh: {e}")
        else:
            st.warning(f"Ảnh không tồn tại: {image_path}")

# ==== Trang chủ ====
def show_home():
    # Ẩn sidebar và custom CSS
    hide_streamlit_style = """
        <style>
        [data-testid="stSidebar"] {display: none;}
        [data-testid="collapsedControl"] {display: none;}
        
        /* Import Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        /* Global styles */
        .stApp {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
        }
        
        /* Main container */
        .main-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        /* Hero banner */
        .hero-banner {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 3rem;
            border-radius: 20px;
            text-align: center;
            margin-bottom: 3rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        .hero-title {
            font-size: 3rem;
            font-weight: 700;
            margin-bottom: 1rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .hero-subtitle {
            font-size: 1.2rem;
            opacity: 0.9;
            margin-bottom: 2rem;
        }
        
        /* Category buttons */
        .category-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 3rem;
        }
        
        .category-button {
            background: white;
            padding: 1.5rem;
            border-radius: 15px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            border: none;
            font-size: 1.1rem;
            font-weight: 500;
            color: #333;
        }
        
        .category-button:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.15);
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        /* News cards */
        .news-card {
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            margin-bottom: 2rem;
            height: 100%;
        }
        
        .news-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 35px rgba(0,0,0,0.2);
        }
        
        .news-card-image {
            width: 100%;
            height: 200px;
            object-fit: cover;
            border-radius: 15px 15px 0 0;
        }
        
        .news-card-content {
            padding: 1.5rem;
        }
        
        .news-card-title {
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: #333;
            text-decoration: none;
            line-height: 1.4;
        }
        
        .news-card-title:hover {
            color: #667eea;
        }
        
        .news-card-description {
            color: #666;
            line-height: 1.6;
            margin-bottom: 1rem;
        }
        
        .news-card-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.9rem;
            color: #888;
        }
        
        /* Featured section */
        .featured-section {
            margin-bottom: 3rem;
        }
        
        .section-title {
            font-size: 2.5rem;
            font-weight: 700;
            color: #333;
            margin-bottom: 2rem;
            text-align: center;
            position: relative;
        }
        
        .section-title::after {
            content: '';
            position: absolute;
            bottom: -10px;
            left: 50%;
            transform: translateX(-50%);
            width: 80px;
            height: 4px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 2px;
        }
        
        /* Business section */
        .business-section {
            background: white;
            padding: 2rem;
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            margin-bottom: 3rem;
        }
        
        .business-main {
            margin-bottom: 2rem;
        }
        
        .business-sidebar {
            background: #f8f9fa;
            padding: 1.5rem;
            border-radius: 15px;
        }
        
        .business-sidebar h3 {
            color: #333;
            margin-bottom: 1rem;
            font-weight: 600;
        }
        
        .business-links {
            list-style: none;
            padding: 0;
        }
        
        .business-links li {
            margin-bottom: 0.8rem;
            padding-left: 1rem;
            position: relative;
        }
        
        .business-links li::before {
            content: '▶';
            position: absolute;
            left: 0;
            color: #667eea;
            font-size: 0.8rem;
        }
        
        .business-links a {
            color: #555;
            text-decoration: none;
            transition: color 0.3s ease;
        }
        
        .business-links a:hover {
            color: #667eea;
        }
        
        /* Responsive design */
        @media (max-width: 768px) {
            .hero-title {
                font-size: 2rem;
            }
            
            .section-title {
                font-size: 2rem;
            }
            
            .main-container {
                padding: 1rem;
            }
        }
        
        /* Footer */
        .footer {
            text-align: center;
            padding: 2rem;
            background: #333;
            color: white;
            border-radius: 20px;
            margin-top: 3rem;
        }
        
        .footer-links {
            display: flex;
            justify-content: center;
            gap: 2rem;
            margin-bottom: 1rem;
        }
        
        .footer-links a {
            color: #ccc;
            text-decoration: none;
            transition: color 0.3s ease;
        }
        
        .footer-links a:hover {
            color: white;
        }
        
        /* Loading animation */
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        .loading {
            animation: pulse 2s infinite;
        }
        </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

    # Hero Banner
    st.markdown("""
    <div class="hero-banner">
        <h1 class="hero-title">🌟 Tin Tức 24/7</h1>
        <p class="hero-subtitle">Cập nhật thông tin nhanh chóng, chính xác và đáng tin cậy</p>
        <div style="display: flex; justify-content: center; gap: 1rem; margin-top: 2rem;">
            <span style="background: rgba(255,255,255,0.2); padding: 0.5rem 1rem; border-radius: 20px;">📱 Mobile Friendly</span>
            <span style="background: rgba(255,255,255,0.2); padding: 0.5rem 1rem; border-radius: 20px;">🔄 Cập nhật liên tục</span>
            <span style="background: rgba(255,255,255,0.2); padding: 0.5rem 1rem; border-radius: 20px;">🤖 AI Support</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Load dữ liệu với loading animation
    with st.spinner("🔄 Đang tải tin tức mới nhất..."):
        news_data = load_news_data()

    if len(news_data) < 11:
        st.error("⚠️ Dữ liệu không đủ bài viết để hiển thị. Vui lòng kiểm tra lại dữ liệu.")
        return

    # Shuffle để hiển thị ngẫu nhiên
    random.shuffle(news_data)

    # Danh mục với grid layout
    st.markdown('<div class="category-grid">', unsafe_allow_html=True)
    
    categories = [
        ("📰 Thời sự", "thoi_su", "📰"),
        ("💻 Công nghệ", "cong_nghe", "💻"),
        ("⚽ Thể thao", "the_thao", "⚽"),
        ("🎭 Giải trí", "giai_tri", "🎭"),
        ("🏥 Sức khỏe", "suc_khoe", "🏥"),
        ("🎓 Giáo dục", "giao_duc", "🎓"),
        ("📊 Phân tích xu hướng", "phan_tich_xu_huong", "📊"),
        ("🤖 Chatbot hỏi đáp", "page_chat_bot", "🤖"),
    ]

    # Tạo grid 4 cột cho categories
    cols = st.columns(4)
    for i, (label, page, icon) in enumerate(categories):
        with cols[i % 4]:
            if st.button(f"{icon} {label.split(' ', 1)[1]}", key=page, use_container_width=True):
                st.query_params["page"] = page
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # Bài nổi bật
    st.markdown('<h2 class="section-title">🔥 Bài Nổi Bật</h2>', unsafe_allow_html=True)
    
    highlight_cols = st.columns(3, gap="large")
    
    for i, col in enumerate(highlight_cols):
        with col:
            with st.container():
                # Image với style đẹp
                if news_data[i].get('image'):
                    show_image(news_data[i]['image'])
                else:
                    st.markdown(f"""
                    <div style="
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        height: 200px;
                        border-radius: 15px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        color: white;
                        font-size: 3rem;
                        margin-bottom: 1rem;
                    ">
                        📰
                    </div>
                    """, unsafe_allow_html=True)
                
                # Content với card style
                st.markdown(f"""
                <div class="news-card-content">
                    <h3 class="news-card-title">
                        <a href="{news_data[i]['url']}" target="_blank">{news_data[i]['title']}</a>
                    </h3>
                    <p class="news-card-description">{news_data[i]['description']}</p>
                    <div class="news-card-meta">
                        <span>📅 Hôm nay</span>
                        <span>👁️ {random.randint(100, 1000)} lượt xem</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # Separator
    st.markdown('<div style="margin: 3rem 0; border-top: 2px solid #eee;"></div>', unsafe_allow_html=True)

    # Tin tức khác
    st.markdown('<h2 class="section-title">📰 Tin Tức Mới Nhất</h2>', unsafe_allow_html=True)
    
    other_news = news_data[3:7]
    news_cols = st.columns(2, gap="large")
    
    for i in range(0, len(other_news), 2):
        for idx, col in enumerate(news_cols):
            if i + idx >= len(other_news):
                break
            article = other_news[i + idx]
            with col:
                with st.container():
                    st.markdown('<div class="news-card">', unsafe_allow_html=True)
                    
                    # Image
                    if article.get('image'):
                        show_image(article['image'])
                    else:
                        st.markdown(f"""
                        <div style="
                            background: linear-gradient(135deg, #ff7b7b 0%, #ff8e8e 100%);
                            height: 180px;
                            border-radius: 15px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            color: white;
                            font-size: 2rem;
                            margin-bottom: 1rem;
                        ">
                            📰
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Content
                    st.markdown(f"""
                    <div class="news-card-content">
                        <h4 class="news-card-title">
                            <a href="{article['url']}" target="_blank">{article['title']}</a>
                        </h4>
                        <p class="news-card-description">{article['description']}</p>
                        <div class="news-card-meta">
                            <span>🕒 {random.randint(1, 12)} giờ trước</span>
                            <span>💬 {random.randint(5, 50)} bình luận</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)

    # Separator
    st.markdown('<div style="margin: 3rem 0; border-top: 2px solid #eee;"></div>', unsafe_allow_html=True)

    # Chuyên mục Kinh Doanh
    st.markdown('<h2 class="section-title">💼 Chuyên Mục Kinh Doanh</h2>', unsafe_allow_html=True)
    
    st.markdown('<div class="business-section">', unsafe_allow_html=True)
    
    business_cols = st.columns([3, 1], gap="large")
    
    with business_cols[0]:
        st.markdown('<div class="business-main">', unsafe_allow_html=True)
        
        # Main business article
        if news_data[7].get('image'):
            show_image(news_data[7]['image'])
        else:
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%);
                height: 300px;
                border-radius: 15px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-size: 4rem;
                margin-bottom: 1rem;
            ">
                💼
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <h2 class="news-card-title" style="font-size: 1.8rem; margin-bottom: 1rem;">
            <a href="{news_data[7]['url']}" target="_blank">{news_data[7]['title']}</a>
        </h2>
        <p class="news-card-description" style="font-size: 1.1rem; line-height: 1.8;">
            {news_data[7]['description']}
        </p>
        <div class="news-card-meta" style="margin-top: 1.5rem;">
            <span>📈 Kinh doanh</span>
            <span>⭐ Bài viết nổi bật</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with business_cols[1]:
        st.markdown('<div class="business-sidebar">', unsafe_allow_html=True)
        
        st.markdown('<h3>📋 Bài viết liên quan</h3>', unsafe_allow_html=True)
        st.markdown('<ul class="business-links">', unsafe_allow_html=True)
        
        for j in range(8, min(11, len(news_data))):
            st.markdown(f"""
            <li>
                <a href="{news_data[j]['url']}" target="_blank">
                    {news_data[j]['title'][:60]}...
                </a>
            </li>
            """, unsafe_allow_html=True)
        
        st.markdown('</ul>', unsafe_allow_html=True)
        
        # Thêm widget thống kê
        st.markdown("""
        <div style="
            margin-top: 2rem;
            padding: 1rem;
            background: white;
            border-radius: 10px;
            border: 1px solid #eee;
        ">
            <h4 style="margin-bottom: 1rem; color: #333;">📊 Thống kê hôm nay</h4>
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                <span>👥 Lượt truy cập:</span>
                <strong>1,234</strong>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                <span>📰 Bài viết mới:</span>
                <strong>15</strong>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span>💬 Bình luận:</span>
                <strong>89</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

    # Footer
    st.markdown("""
    <div class="footer">
        <div class="footer-links">
            <a href="#">Giới thiệu</a>
            <a href="#">Liên hệ</a>
            <a href="#">Chính sách</a>
            <a href="#">RSS</a>
        </div>
        <p>© 2024 Tin Tức 24/7. Tất cả quyền được bảo lưu.</p>
        <p style="font-size: 0.9rem; opacity: 0.8;">
            🚀 Powered by AI Technology | 📱 Mobile Optimized | 🔒 Secure & Fast
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Thêm floating action button
    st.markdown("""
    <div style="
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 50%;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        cursor: pointer;
        z-index: 1000;
        font-size: 1.2rem;
        transition: all 0.3s ease;
    " onclick="window.scrollTo(0, 0);" title="Về đầu trang">
        ⬆️
    </div>
    """, unsafe_allow_html=True)

    # JavaScript cho smooth scroll
    st.markdown("""
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        // Smooth scroll for anchor links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                document.querySelector(this.getAttribute('href')).scrollIntoView({
                    behavior: 'smooth'
                });
            });
        });
    });
    </script>
    """, unsafe_allow_html=True)