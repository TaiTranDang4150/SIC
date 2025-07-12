import os
import json
import functools
import shutil
from typing import List, Dict, Any
from dotenv import load_dotenv

# LangChain split văn bản
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Các module đã tách riêng
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma

# Schema của LangChain
from langchain.schema import Document

# Giao diện
import streamlit as st
from pathlib import Path

# Load data từ cơ sở dữ liệu MongoDB
from utils.load_data import load_news_data # Keep this import

class RAGChatbot:
    """
    Lớp RAG Chatbot được tối ưu hóa cho dữ liệu tin tức.
    """
    def __init__(self, db_name: str = "vector_db_optimized"): # Removed data_path from here
        """
        Khởi tạo RAG Chatbot.

        Args:
            db_name (str): Tên thư mục lưu vector database.
        """
        load_dotenv(override=True)
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY không được tìm thấy trong biến môi trường.")

        # self.data_path = data_path # No longer needed here
        self.db_name = db_name

        # --- CẢI TIẾN: Cấu hình Embedding và LLM tối ưu ---
        self.embedding_model = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=self.openai_api_key,
            chunk_size=1000,
            max_retries=3,
            request_timeout=60
        )
        self.llm_model = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.2,  # Giảm nhiệt độ để câu trả lời bám sát sự thật
            api_key=self.openai_api_key
        )
        self.vectorstore = None

    def check_and_fix_embedding_dimension(self):
        """
        Kiểm tra và xử lý lỗi không tương thích dimension của embedding.
        Tự động đề xuất tạo lại database nếu có lỗi.
        """
        if os.path.exists(self.db_name):
            try:
                st.info("Đang kiểm tra vector database hiện có...")
                temp_vectorstore = Chroma(
                    persist_directory=self.db_name,
                    embedding_function=self.embedding_model
                )
                temp_vectorstore.similarity_search("test", k=1)
                self.vectorstore = temp_vectorstore
                st.success("✅ Sử dụng vector database hiện có thành công!")
                return True
            except Exception as e:
                error_msg = str(e)
                if "dimension" in error_msg.lower():
                    st.warning(f"⚠️ Phát hiện lỗi không tương thích dimension: {error_msg}")
                    if st.button("Xóa và tạo lại vector database"):
                        return self.rebuild_vectorstore()
                    else:
                        st.info("Nhấn nút trên để tạo lại database với model embedding mới.")
                        return False
                else:
                    st.error(f"Lỗi không xác định khi tải database: {error_msg}")
                    return False
        else:
            st.info("Vector database chưa tồn tại. Bắt đầu quá trình tạo mới.")
            return self.rebuild_vectorstore()

    def rebuild_vectorstore(self):
        """
        Xóa và xây dựng lại toàn bộ vector database từ đầu.
        """
        try:
            if os.path.exists(self.db_name):
                shutil.rmtree(self.db_name)
                st.info("Đã xóa vector database cũ.")
            self.build_vectorstore()
            return True
        except Exception as e:
            st.error(f"Lỗi nghiêm trọng khi tạo lại vector database: {e}")
            return False

    # Removed the functools.lru_cache(maxsize=None) load_news_data method from here

    def create_documents_from_news(self, news_data: List[Dict[str, Any]]) -> List[Document]:
        """Tạo đối tượng Document từ dữ liệu tin tức với metadata chi tiết."""
        documents = []
        for item in news_data:
            content = item.get('content', '')
            if not content:
                continue

            metadata = {
                "id": str(item.get('id', '')),
                "title": item.get('title', 'N/A'),
                "url": item.get('url', ''),
                "author": item.get('author', 'N/A'),
                "tags": ', '.join(item.get('tags', [])),
                "time_posted": item.get('time_posted', 'N/A'),
                # "source_file": os.path.basename(self.data_path) # No longer rely on data_path directly
            }
            doc = Document(page_content=content.strip(), metadata=metadata)
            documents.append(doc)
        return documents

    # --- CẢI TIẾN: Chiến lược chunking tối ưu hơn ---
    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """
        Chia nhỏ documents thành các chunks với kích thước và overlap hợp lý.
        """
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=700,
            chunk_overlap=150,
            length_function=len,
            separators=["\n\n", "\n", ". ", "!", "?", " ", ""]
        )
        chunked_docs = text_splitter.split_documents(documents)

        # Lọc bỏ các chunk quá ngắn, thường không chứa nhiều thông tin hữu ích
        filtered_chunks = [doc for doc in chunked_docs if len(doc.page_content) > 50]

        st.write(f"Đã chia {len(documents)} bài báo thành {len(filtered_chunks)} chunks.")
        return filtered_chunks

    def build_vectorstore(self) -> None:
        """Xây dựng vector store từ dữ liệu, với batch processing và progress bar."""
        # Use the imported load_news_data function
        news_data = load_news_data() # Call the external function here
        if not news_data:
            raise ValueError("Không thể tải dữ liệu từ cơ sở dữ liệu.")

        documents = self.create_documents_from_news(news_data)
        if not documents:
            raise ValueError("Không có document hợp lệ để tạo vector store.")

        chunked_docs = self.chunk_documents(documents)
        if not chunked_docs:
            st.warning("Không có chunk nào được tạo. Vui lòng kiểm tra lại dữ liệu đầu vào.")
            return

        st.info(f"Bắt đầu tạo vector database từ {len(chunked_docs)} chunks...")
        batch_size = 50
        batches = [chunked_docs[i:i + batch_size] for i in range(0, len(chunked_docs), batch_size)]

        # Khởi tạo vectorstore với batch đầu tiên
        self.vectorstore = Chroma.from_documents(
            documents=batches[0],
            embedding=self.embedding_model,
            persist_directory=self.db_name
        )

        # Thêm các batch còn lại với progress bar
        progress_bar = st.progress(1 / len(batches), text=f"Đang xử lý batch 1/{len(batches)}")
        for i, batch in enumerate(batches[1:], 1):
            try:
                self.vectorstore.add_documents(batch)
                progress_bar.progress((i + 1) / len(batches), text=f"Đang xử lý batch {i+1}/{len(batches)}")
            except Exception as e:
                st.warning(f"Lỗi khi thêm batch {i+1}: {e}")
                continue

        self.vectorstore.persist()
        st.success("🎉 Hoàn thành tạo vector database!")

    # --- CẢI TIẾN: Sử dụng truy vấn MMR để đa dạng hóa kết quả ---
    def get_query_results(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Truy vấn RAG sử dụng Maximal Marginal Relevance (MMR) để tăng sự đa dạng.
        """
        if not self.vectorstore:
            if not self.check_and_fix_embedding_dimension():
                return []

        try:
            retriever = self.vectorstore.as_retriever(
                search_type="mmr",
                search_kwargs={'k': k, 'fetch_k': 20}
            )
            docs = retriever.get_relevant_documents(query)

            return [{
                "content": doc.page_content,
                "metadata": doc.metadata,
                "similarity_score": "N/A (MMR)"
            } for doc in docs]
        except Exception as e:
            st.error(f"Lỗi khi truy vấn vector database: {e}")
            return []

    def create_context_from_results(self, query_results: List[Dict[str, Any]]) -> str:
        """Tạo context string từ kết quả truy vấn để đưa vào prompt."""
        if not query_results:
            return ""

        context_parts = []
        for i, result in enumerate(query_results, 1):
            metadata = result["metadata"]
            context_entry = (
                f"[Nguồn {i}]\n"
                f"Tiêu đề: {metadata.get('title', 'N/A')}\n"
                f"Nội dung: {result['content']}\n"
                f"Tác giả: {metadata.get('author', 'N/A')}\n"
                f"Thời gian: {metadata.get('time_posted', 'N/A')}\n"
                f"---"
            )
            context_parts.append(context_entry)

        return "\n\n".join(context_parts)

    # --- CẢI TIẾN: Prompt chặt chẽ và rõ ràng hơn ---
    def create_prompt_template(self, question: str, context: str) -> str:
        """Tạo prompt template hiệu quả cho LLM."""
        if context:
            return f"""Bạn là một trợ lý AI phân tích tin tức.
**CHỈ được phép sử dụng thông tin từ các tài liệu được cung cấp dưới đây để trả lời câu hỏi.** Không được sử dụng bất kỳ kiến thức bên ngoài nào. Nếu thông tin không có trong tài liệu, hãy trả lời rằng "Thông tin không có trong tài liệu được cung cấp.".

TÀI LIỆU:
---
{context}
---

CÂU HỎI: {question}

HƯỚNG DẪN:
- Trả lời bằng tiếng Việt, chi tiết, rõ ràng.
- Trích dẫn nguồn (ví dụ: [Nguồn 1], [Nguồn 2]) trong câu trả lời khi sử dụng thông tin từ đó.

TRẢ LỜI:"""
        else:
            return f"""Bạn là một trợ lý AI thông minh. Trả lời câu hỏi sau bằng kiến thức chung của bạn.

CÂU HỎI: {question}

TRẢ LỜI:"""

    def ask_question(self, question: str) -> Dict[str, Any]:
        """Quy trình hoàn chỉnh để hỏi và nhận câu trả lời từ chatbot."""
        try:
            query_results = self.get_query_results(question, k=5)
            context = self.create_context_from_results(query_results)
            prompt = self.create_prompt_template(question, context)

            response = self.llm_model.invoke(prompt)
            answer = response.content

            detailed_sources = [{
                "index": i + 1,
                "title": r["metadata"].get("title", "N/A"),
                "url": r["metadata"].get("url", ""),
            } for i, r in enumerate(query_results)]

            return {
                "answer": answer,
                "detailed_sources": detailed_sources,
                "has_rag_context": bool(query_results),
                "context_used": context
            }
        except Exception as e:
            st.error(f"Lỗi khi xử lý câu hỏi: {e}")
            return {
                "answer": "Xin lỗi, đã có lỗi xảy ra. Vui lòng thử lại.",
                "detailed_sources": [],
                "has_rag_context": False,
                "context_used": ""
            }

# --- Cấu hình Streamlit và Singleton Pattern ---
@st.cache_resource
def get_chatbot():
    """Tạo và cache singleton chatbot instance."""

    # --- CẢI TIẾN: Sử dụng đường dẫn tương đối ---
    # Đảm bảo file data `ok_vnnet.json` nằm trong thư mục con `data`
    # của thư mục chứa file python này.
    # Cấu trúc thư mục:
    # /your_project_folder
    #   |- app.py (file này)
    #   |- /data
    #       |- ok_vnnet.json

    # current_dir = Path(__file__).parent # No longer needed for data path
    # DATA_PATH_STR = "C:\\Users\\Admin\\PyCharmMiscProject\\sic_project\\data\\ok_vnnet.json" # No longer needed
    DB_NAME = "vector_db_optimized"

    # DATA_PATH_OBJ = Path(DATA_PATH_STR) # No longer needed
    # if not DATA_PATH_OBJ.exists(): # No longer needed for file check
    #     st.error(f"Không tìm thấy file dữ liệu tại: {DATA_PATH_OBJ}")
    #     st.stop()

    chatbot = RAGChatbot(db_name=DB_NAME) # Pass only db_name
    return chatbot

def build_qa_chain():
    """Khởi tạo hệ thống RAG và trả về chatbot instance."""
    chatbot = get_chatbot()
    if not chatbot.vectorstore:
        with st.spinner("Đang khởi tạo hệ thống RAG..."):
            chatbot.check_and_fix_embedding_dimension()
    return chatbot

# --- Các hàm tiện ích ---
def ask_chatbot(question: str) -> Dict[str, Any]:
    """Hàm tiện ích để đặt câu hỏi cho chatbot."""
    chatbot = get_chatbot()
    return chatbot.ask_question(question)

def get_query_results_debug(question: str, k: int = 5):
    """Hàm tiện ích để debug, xem trực tiếp kết quả truy vấn RAG."""
    chatbot = get_chatbot()
    return chatbot.get_query_results(question, k)