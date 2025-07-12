import streamlit as st
from datetime import datetime
from pages.chat_bot import build_qa_chain, ask_chatbot, get_query_results_debug
import time
from utils.load_data import load_news_data

def show_chat():
    """Hiển thị giao diện chat với RAG + GPT API"""
    
    # Ẩn navigation menu và custom CSS
    hide_navbar = """
    <style>
    [data-testid="stSidebarNav"] {
        display: none;
    }
    .stApp > header {
        background-color: transparent;
    }
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 10px;
        border-left: 4px solid #2196f3;
    }
    .user-message {
        background-color: #e3f2fd;
        border-left-color: #2196f3;
    }
    .bot-message {
        background-color: #f1f8e9;
        border-left-color: #4caf50;
    }
    .source-info {
        background-color: #fff3e0;
        padding: 0.8rem;
        border-radius: 8px;
        border-left: 3px solid #ff9800;
        margin-top: 1rem;
        font-size: 0.9rem;
    }
    .query-results {
        background-color: #fce4ec;
        padding: 1rem;
        border-radius: 8px;
        border-left: 3px solid #e91e63;
        margin: 1rem 0;
        max-height: 200px;
        overflow-y: auto;
    }
    .processing-step {
        background-color: #f5f5f5;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        margin: 0.3rem 0;
        border-left: 3px solid #9e9e9e;
    }
    .error-message {
        background-color: #ffebee;
        color: #c62828;
        padding: 1rem;
        border-radius: 8px;
        border-left: 3px solid #f44336;
        margin: 1rem 0;
    }
    .success-message {
        background-color: #e8f5e8;
        color: #2e7d32;
        padding: 1rem;
        border-radius: 8px;
        border-left: 3px solid #4caf50;
        margin: 1rem 0;
    }
    .stats-container {
        display: flex;
        justify-content: space-around;
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .stat-item {
        text-align: center;
        padding: 0.5rem;
    }
    .stat-number {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2196f3;
    }
    .stat-label {
        font-size: 0.9rem;
        color: #666;
    }
    .rag-status {
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.5rem 0;
        text-align: center;
        font-weight: bold;
    }
    .rag-found {
        background-color: #e8f5e8;
        color: #2e7d32;
        border: 1px solid #4caf50;
    }
    .rag-not-found {
        background-color: #fff3e0;
        color: #e65100;
        border: 1px solid #ff9800;
    }
    </style>
    """
    st.markdown(hide_navbar, unsafe_allow_html=True)

    # Header với thiết kế đẹp
    st.markdown("""
    <div class="main-header">
        <h1 style='color: white; text-align: center; margin: 0;'>
            🤖 Chatbot Hỏi Đáp Báo Chí Thông Minh
        </h1>
        <p style='color: white; text-align: center; margin: 0; opacity: 0.9;'>
            RAG + OpenAI GPT | Vector Search → AI Processing → Smart Answer
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar với thông tin và thống kê
    with st.sidebar:
        st.image("https://via.placeholder.com/150x100/667eea/white?text=AI+Bot", width=150)
        st.markdown("### 📰 Hệ Thống RAG + OpenAI")
        st.markdown("---")
        
        # Thống kê phiên chat
        total_questions = len(st.session_state.get('chat_history', []))
        rag_questions = sum(1 for chat in st.session_state.get('chat_history', []) if chat.get('has_rag_context', False))
        
        st.markdown(f"""
        <div class="stats-container">
            <div class="stat-item">
                <div class="stat-number">{total_questions}</div>
                <div class="stat-label">Tổng câu hỏi</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{rag_questions}</div>
                <div class="stat-label">Dùng RAG</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{datetime.now().strftime('%H:%M')}</div>
                <div class="stat-label">Thời gian</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### 🔄 Quy trình xử lý")
        st.markdown("""
        1. **🔍 Truy vấn RAG**: Tìm kiếm vector database
        2. **📊 Xử lý dữ liệu**: Tạo context từ kết quả RAG
        3. **🧠 OpenAI GPT**: Phân tích và tạo câu trả lời
        4. **✨ Kết quả**: Trả lời thông minh với nguồn
        """)
        
        st.markdown("---")
        st.markdown("### ⚙️ Cài đặt")
        
        # Tùy chọn hiển thị chi tiết
        show_rag_details = st.checkbox("Hiển thị chi tiết RAG", value=False)
        show_processing_steps = st.checkbox("Hiển thị các bước xử lý", value=True)
        show_source_details = st.checkbox("Hiển thị thông tin nguồn", value=True)
        
        # Tùy chọn số lượng kết quả truy vấn
        max_results = st.slider("Số kết quả RAG tối đa", 1, 10, 6)

    # Khởi tạo session state
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'qa_chain' not in st.session_state:
        st.session_state.qa_chain = None
    if 'system_ready' not in st.session_state:
        st.session_state.system_ready = False

    # Khởi tạo QA Chain (chatbot)
    if not st.session_state.system_ready:
        with st.spinner("🔄 Đang khởi tạo hệ thống RAG + OpenAI..."):
            try:
                st.session_state.qa_chain = build_qa_chain()
                st.session_state.system_ready = True
                st.success("✅ Hệ thống đã sẵn sàng!")
            except Exception as e:
                st.error(f"❌ Lỗi khởi tạo hệ thống: {str(e)}")
                st.stop()

    # Hiển thị lịch sử chat
    if st.session_state.chat_history:
        st.markdown("### 💬 Lịch sử hội thoại")
        
        # Hiển thị các tin nhắn theo thứ tự
        for i, chat_item in enumerate(st.session_state.chat_history):
            question = chat_item['question']
            answer = chat_item['answer']
            sources = chat_item.get('sources', [])
            source_count = chat_item.get('source_count', 0)
            has_rag_context = chat_item.get('has_rag_context', False)
            processing_time = chat_item.get('processing_time', 0)
            detailed_sources = chat_item.get('detailed_sources', [])
            
            # Tin nhắn người dùng
            st.markdown(f"""
            <div class="chat-message user-message">
                <strong>🧑 Bạn:</strong> {question}
            </div>
            """, unsafe_allow_html=True)
            
            # Hiển thị trạng thái RAG
            if has_rag_context:
                st.markdown(f"""
                <div class="rag-status rag-found">
                    ✅ Tìm thấy {source_count} nguồn từ RAG
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="rag-status rag-not-found">
                    ⚠️ Không tìm thấy dữ liệu RAG - Sử dụng kiến thức chung
                </div>
                """, unsafe_allow_html=True)
            
            # Tin nhắn bot
            st.markdown(f"""
            <div class="chat-message bot-message">
                <strong>🤖 Bot:</strong> {answer}
            </div>
            """, unsafe_allow_html=True)
            
            # Hiển thị thông tin nguồn nếu có
            if show_source_details and sources:
                st.markdown(f"""
                <div class="source-info">
                    <strong>📚 Nguồn tham khảo:</strong><br>
                    {chat_item.get('source_summary', 'Không có thông tin nguồn')}
                </div>
                """, unsafe_allow_html=True)
            
            # Thông tin chi tiết (có thể ẩn/hiện)
            with st.expander(f"📋 Chi tiết xử lý câu hỏi {i+1}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"**⏱️ Thời gian xử lý:** {processing_time:.2f}s")
                    st.markdown(f"**🔍 Trạng thái RAG:** {'✅ Có dữ liệu' if has_rag_context else '❌ Không có dữ liệu'}")
                
                with col2:
                    st.markdown(f"**📊 Số nguồn:** {source_count}")
                    st.markdown(f"**🕒 Thời gian:** {chat_item.get('timestamp', 'N/A')}")
                
                with col3:
                    st.markdown(f"**🧠 Model:** OpenAI GPT")
                    st.markdown(f"**📝 Có context:** {'Có' if has_rag_context else 'Không'}")
                
                # Hiển thị chi tiết nguồn nếu có
                if show_rag_details and detailed_sources:
                    st.markdown("**📚 Chi tiết nguồn tài liệu:**")
                    for j, source in enumerate(detailed_sources, 1):
                        with st.expander(f"Nguồn {j}: {source.get('title', 'N/A')}"):
                            st.markdown(f"**Tác giả:** {source.get('author', 'N/A')}")
                            st.markdown(f"**Thời gian:** {source.get('time_posted', 'N/A')}")
                            st.markdown(f"**Tags:** {source.get('tags', 'N/A')}")
                            st.markdown(f"**Similarity Score:** {source.get('similarity_score', 0):.4f}")
                            if source.get('url') and source.get('url') != 'N/A':
                                st.markdown(f"**URL:** {source.get('url')}")
                
                # Hiển thị query results nếu có
                if show_rag_details and chat_item.get('query_results'):
                    st.markdown("**📊 Kết quả truy vấn RAG:**")
                    for j, result in enumerate(chat_item['query_results'][:3], 1):
                        with st.expander(f"Kết quả {j}"):
                            st.text(result[:500] + "..." if len(result) > 500 else result)

    # Form nhập câu hỏi
    st.markdown("---")
    with st.form("chat_form", clear_on_submit=True):
        st.markdown("### 🔍 Đặt câu hỏi mới")
        
        # Input với các tùy chọn
        col1, col2 = st.columns([5, 1])
        
        with col1:
            query = st.text_input(
                "Nhập câu hỏi của bạn:",
                placeholder="Ví dụ: Tình hình kinh tế Việt Nam hiện tại như thế nào?",
                help="Hệ thống sẽ tìm kiếm trong RAG trước, sau đó sử dụng OpenAI GPT để trả lời"
            )
        
        with col2:
            submit_button = st.form_submit_button(
                "🚀 Gửi", 
                use_container_width=True,
                help="Nhấn để gửi câu hỏi"
            )

    # Xử lý khi có câu hỏi
    if submit_button and query:
        if query.strip():
            # Bắt đầu xử lý
            start_time = time.time()
            
            # Container cho quá trình xử lý
            processing_container = st.container()
            
            with processing_container:
                st.markdown("### 🔄 Đang xử lý câu hỏi...")
                
                # Hiển thị câu hỏi
                st.markdown(f"""
                <div class="chat-message user-message">
                    <strong>🧑 Bạn hỏi:</strong> {query}
                </div>
                """, unsafe_allow_html=True)
                
                # Progress bar và status
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    # Bước 1: Truy vấn RAG
                    if show_processing_steps:
                        st.markdown('<div class="processing-step">🔍 Bước 1: Truy vấn cơ sở dữ liệu RAG...</div>', unsafe_allow_html=True)
                    
                    status_text.text("🔍 Đang tìm kiếm trong vector database...")
                    progress_bar.progress(25)
                    
                    # Truy vấn RAG trực tiếp
                    rag_results = get_query_results_debug(query, k=max_results)
                    
                    # Kiểm tra kết quả RAG
                    has_rag_data = len(rag_results) > 0
                    
                    if has_rag_data:
                        st.markdown(f"""
                        <div class="rag-status rag-found">
                            ✅ Tìm thấy {len(rag_results)} kết quả từ RAG
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="rag-status rag-not-found">
                            ⚠️ Không tìm thấy dữ liệu RAG - Sẽ sử dụng kiến thức chung
                        </div>
                        """, unsafe_allow_html=True)
                    
                    progress_bar.progress(50)
                    
                    # Bước 2: Xử lý với OpenAI GPT
                    if show_processing_steps:
                        st.markdown('<div class="processing-step">🧠 Bước 2: Xử lý với OpenAI GPT...</div>', unsafe_allow_html=True)
                    
                    status_text.text("🤖 Đang xử lý với OpenAI GPT...")
                    progress_bar.progress(75)
                    
                    # Gọi ask_chatbot để xử lý
                    chatbot_result = ask_chatbot(query)
                    
                    # Xử lý kết quả
                    if isinstance(chatbot_result, dict):
                        answer = chatbot_result.get('answer', 'Xin lỗi, không thể tạo câu trả lời.')
                        sources = chatbot_result.get('sources', [])
                        source_summary = chatbot_result.get('source_summary', '')
                        source_count = chatbot_result.get('source_count', 0)
                        has_rag_context = chatbot_result.get('has_rag_context', False)
                        detailed_sources = chatbot_result.get('detailed_sources', [])
                        query_results = chatbot_result.get('query_results', [])
                    else:
                        answer = str(chatbot_result)
                        sources = []
                        source_summary = ''
                        source_count = 0
                        has_rag_context = False
                        detailed_sources = []
                        query_results = []
                    
                    progress_bar.progress(90)
                    
                    # Bước 3: Hoàn thành
                    if show_processing_steps:
                        st.markdown('<div class="processing-step">✨ Bước 3: Hoàn thành xử lý...</div>', unsafe_allow_html=True)
                    
                    status_text.text("✅ Hoàn thành xử lý!")
                    progress_bar.progress(100)
                    
                    # Tính thời gian xử lý
                    processing_time = time.time() - start_time
                    
                    # Hiển thị kết quả
                    st.markdown("### ✨ Câu trả lời:")
                    
                    # Hiển thị trạng thái RAG cuối cùng
                    if has_rag_context:
                        st.markdown(f"""
                        <div class="rag-status rag-found">
                            ✅ Câu trả lời dựa trên {source_count} nguồn từ RAG
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="rag-status rag-not-found">
                            ⚠️ Câu trả lời dựa trên kiến thức chung (không có dữ liệu RAG)
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Hiển thị câu trả lời
                    st.markdown(f"""
                    <div class="chat-message bot-message">
                        <strong>🤖 Bot:</strong> {answer}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Hiển thị thông tin bổ sung
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("⏱️ Thời gian", f"{processing_time:.2f}s")
                    with col2:
                        st.metric("🔍 RAG Status", "✅ Có dữ liệu" if has_rag_context else "❌ Không có")
                    with col3:
                        st.metric("📚 Nguồn", source_count)
                    with col4:
                        st.metric("🧠 Model", "OpenAI GPT")
                    
                    # Hiển thị thông tin nguồn
                    if show_source_details and source_summary:
                        st.markdown("### 📚 Nguồn tài liệu tham khảo:")
                        st.markdown(f"""
                        <div class="source-info">
                            {source_summary}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Hiển thị chi tiết RAG nếu được bật
                    if show_rag_details and has_rag_context:
                        st.markdown("### 📊 Chi tiết kết quả RAG:")
                        
                        # Hiển thị các nguồn chi tiết
                        if detailed_sources:
                            for i, source in enumerate(detailed_sources, 1):
                                with st.expander(f"Nguồn {i}: {source.get('title', 'N/A')} (Score: {source.get('similarity_score', 0):.4f})"):
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.markdown(f"**Tác giả:** {source.get('author', 'N/A')}")
                                        st.markdown(f"**Thời gian:** {source.get('time_posted', 'N/A')}")
                                    with col2:
                                        st.markdown(f"**Tags:** {source.get('tags', 'N/A')}")
                                        st.markdown(f"**Similarity:** {source.get('similarity_score', 0):.4f}")
                                    
                                    if source.get('url') and source.get('url') != 'N/A':
                                        st.markdown(f"**URL:** {source.get('url')}")
                        
                        # Hiển thị nội dung truy vấn
                        if query_results:
                            st.markdown("**📝 Nội dung được tìm thấy:**")
                            for i, result in enumerate(query_results[:3], 1):
                                with st.expander(f"Kết quả {i}"):
                                    st.text_area(f"Content {i}", result, height=150, disabled=True)
                    
                    # Lưu vào lịch sử
                    chat_item = {
                        'question': query,
                        'answer': answer,
                        'sources': sources,
                        'source_summary': source_summary,
                        'source_count': source_count,
                        'has_rag_context': has_rag_context,
                        'detailed_sources': detailed_sources,
                        'query_results': query_results,
                        'processing_time': processing_time,
                        'timestamp': datetime.now().strftime('%H:%M:%S %d/%m/%Y')
                    }
                    st.session_state.chat_history.append(chat_item)
                    
                    # Xóa progress bar
                    progress_bar.empty()
                    status_text.empty()
                    
                    # Hiển thị thông báo thành công
                    st.markdown(f"""
                    <div class="success-message">
                        ✅ Đã xử lý thành công câu hỏi trong {processing_time:.2f} giây!
                        {'Sử dụng RAG context' if has_rag_context else 'Sử dụng kiến thức chung'}
                    </div>
                    """, unsafe_allow_html=True)
                    
                except Exception as e:
                    st.markdown(f"""
                    <div class="error-message">
                        ❌ Lỗi khi xử lý câu hỏi: {str(e)}
                    </div>
                    """, unsafe_allow_html=True)
                    progress_bar.empty()
                    status_text.empty()
        else:
            st.warning("⚠️ Vui lòng nhập câu hỏi!")

    # Footer và các nút điều khiển
    st.markdown("---")
    
    # Nút điều khiển
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.session_state.chat_history:
            if st.button("🗑️ Xóa lịch sử chat", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()
    
    with col2:
        if st.button("🔄 Khởi tạo lại hệ thống", use_container_width=True):
            st.session_state.qa_chain = None
            st.session_state.system_ready = False
            st.rerun()
    
    with col3:
        if st.button("💾 Xuất lịch sử", use_container_width=True):
            if st.session_state.chat_history:
                # Tạo dữ liệu xuất
                export_data = []
                for item in st.session_state.chat_history:
                    export_data.append({
                        'Câu hỏi': item['question'],
                        'Câu trả lời': item['answer'],
                        'Có RAG': 'Có' if item.get('has_rag_context') else 'Không',
                        'Số nguồn': item.get('source_count', 0),
                        'Thời gian xử lý': f"{item.get('processing_time', 0):.2f}s",
                        'Thời gian': item['timestamp'],
                        'Nguồn': item.get('source_summary', 'Không có')
                    })
                
                # Tạo nội dung file
                import json
                export_content = json.dumps(export_data, ensure_ascii=False, indent=2)
                
                st.download_button(
                    label="📥 Tải file JSON",
                    data=export_content,
                    file_name=f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )

    # Footer
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 1rem;'>
        <p>🤖 Powered by RAG + OpenAI GPT | 🔍 Vector Search | 📊 Smart Context Processing</p>
        <p style='font-size: 0.8rem;'>Hệ thống truy vấn vector database và xử lý AI thông minh</p>
    </div>
    """, unsafe_allow_html=True)


# Chạy ứng dụng
# if __name__ == "__main__":
#     # Cấu hình trang
#     st.set_page_config(
#         page_title="RAG + OpenAI Chatbot", 
#         page_icon="🤖",
#         layout="wide",
#         initial_sidebar_state="expanded",
#         menu_items={
#             'Get Help': 'https://github.com/your-repo',
#             'Report a bug': 'https://github.com/your-repo/issues',
#             'About': 'RAG + OpenAI Chatbot - Hệ thống hỏi đáp thông minh với vector search'
#         }
#     )
    
#     show_chat()