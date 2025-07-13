import os
import json
import functools
import shutil
from typing import List, Dict, Any
from dotenv import load_dotenv

# --- CẢI TIẾN: Thêm các import cần thiết cho việc tinh chỉnh ---
# LangChain split văn bản theo ngữ nghĩa
from langchain_experimental.text_splitter import SemanticChunker
# LangChain để kết hợp nhiều retriever
from langchain.retrievers import EnsembleRetriever

# Các module đã tách riêng
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma

# Schema của LangChain
from langchain.schema import Document

# Giao diện
import streamlit as st
from pathlib import Path

# Load data từ cơ sở dữ liệu MongoDB
from utils.load_data import load_news_data  # Keep this import


class RAGChatbot:
    """
    Lớp RAG Chatbot được tối ưu hóa cho dữ liệu tin tức.
    """

    def __init__(self, db_name: str = "vector_db_optimized_v2"):  # Đổi tên DB để tránh xung đột với DB cũ
        """
        Khởi tạo RAG Chatbot.

        Args:
            db_name (str): Tên thư mục lưu vector database.
        """
        load_dotenv(override=True)
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY không được tìm thấy trong biến môi trường.")

        self.db_name = db_name

        # --- Cấu hình Embedding và LLM vẫn giữ nguyên tối ưu cũ ---
        self.embedding_model = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=self.openai_api_key,
            chunk_size=1000,
            max_retries=3,
            request_timeout=60
        )
        self.llm_model = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.15,  # Giảm nhẹ nhiệt độ hơn nữa để câu trả lời bám sát sự thật
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
                # Tăng cường khả năng bắt lỗi dimension
                if "dimension" in error_msg.lower() or "dimensionality" in error_msg.lower():
                    st.warning(f"⚠️ Phát hiện lỗi không tương thích dimension: {error_msg}")
                    if st.button("Xóa và tạo lại vector database với cấu hình mới"):
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

    def create_documents_from_news(self, news_data: List[Dict[str, Any]]) -> List[Document]:
        documents = []
        for item in news_data:
            # --- KIỂM TRA VÀ ÉP KIỂU CONTENT ---
            content_raw = item.get('content', '')
            if not isinstance(content_raw, str):
                # Nếu content không phải là chuỗi, cố gắng chuyển nó thành chuỗi
                try:
                    content = str(content_raw)
                except Exception as e:
                    st.warning(
                        f"Không thể chuyển đổi nội dung thành chuỗi cho ID {item.get('id', 'N/A')}: {content_raw}. Bỏ qua bản ghi này. Lỗi: {e}")
                    continue  # Bỏ qua bản ghi này nếu không thể chuyển đổi
            else:
                content = content_raw

            if not content:  # Kiểm tra lại sau khi ép kiểu
                continue

            # ... (Phần xử lý tags đã được sửa ở lần trước, giữ nguyên) ...
            tags_value = item.get('tags')
            tags_str = "N/A"

            if isinstance(tags_value, list):
                tags_str = ', '.join(str(tag) for tag in tags_value if tag is not None)
            elif isinstance(tags_value, (str, float, int)):
                tags_str = str(tags_value)

            metadata = {
                "id": str(item.get('id', '')),
                "title": item.get('title', 'N/A'),
                "url": item.get('url', ''),
                "author": item.get('author', 'N/A'),
                "tags": tags_str,
                "time_posted": item.get('time_posted', 'N/A'),
            }
            # Gọi .strip() chỉ khi content đã chắc chắn là chuỗi
            doc = Document(page_content=content.strip(), metadata=metadata)
            documents.append(doc)
        return documents

    # --- CẢI TIẾN #1: Sử dụng Semantic Chunking ---
    # Chú thích: Thay vì chia văn bản theo số lượng ký tự một cách máy móc,
    # SemanticChunker sử dụng mô hình embedding để tìm ra những điểm ngắt tự nhiên
    # trong văn bản, nơi ngữ nghĩa thay đổi. Điều này giúp mỗi chunk chứa đựng
    # một ý tưởng hoặc một chủ đề trọn vẹn hơn, cung cấp context chất lượng cao hơn cho LLM.
    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """
        Chia nhỏ documents bằng Semantic Chunker để giữ trọn vẹn ngữ nghĩa.
        """
        st.info("Bắt đầu chia nhỏ văn bản theo ngữ nghĩa (Semantic Chunking)...")
        # Khởi tạo SemanticChunker với chính embedding model đang dùng
        text_splitter = SemanticChunker(
            self.embedding_model,
            breakpoint_threshold_type="percentile"
            # Ngưỡng để quyết định điểm ngắt, 'percentile' thường cho kết quả tốt.
        )

        all_chunks = []
        progress_bar = st.progress(0, text="Đang xử lý văn bản...")
        for i, doc in enumerate(documents):
            # SemanticChunker cần chạy trên từng document một
            chunks = text_splitter.create_documents([doc.page_content])
            # Gán lại metadata từ document gốc cho các chunk mới được tạo
            for chunk in chunks:
                chunk.metadata = doc.metadata.copy()
            all_chunks.extend(chunks)
            progress_bar.progress((i + 1) / len(documents), text=f"Đã xử lý {i + 1}/{len(documents)} bài báo")

        st.success(f"Đã chia {len(documents)} bài báo thành {len(all_chunks)} chunks theo ngữ nghĩa.")
        return all_chunks

    def build_vectorstore(self) -> None:
        """Xây dựng vector store từ dữ liệu, với batch processing và progress bar."""
        news_data_full = load_news_data()
        if not news_data_full:
            raise ValueError("Không thể tải dữ liệu từ cơ sở dữ liệu.")

        # Giới hạn số lượng bài báo để chunk (100 bài)
        limited_news_data = news_data_full[:100]
        st.info(f"Đang xử lý {len(limited_news_data)} bài báo để tạo vector database...")

        documents = self.create_documents_from_news(limited_news_data)
        if not documents:
            raise ValueError("Không có document hợp lệ để tạo vector store.")

        chunked_docs = self.chunk_documents(documents)
        if not chunked_docs:
            st.warning("Không có chunk nào được tạo. Vui lòng kiểm tra lại dữ liệu đầu vào.")
            return

        st.info(f"Bắt đầu tạo vector database từ {len(chunked_docs)} chunks...")
        batch_size = 50
        batches = [chunked_docs[i:i + batch_size] for i in range(0, len(chunked_docs), batch_size)]

        if not batches:
            st.warning("Không có batch nào để xử lý.")
            return

        self.vectorstore = Chroma.from_documents(
            documents=batches[0],
            embedding=self.embedding_model,
            persist_directory=self.db_name
        )

        progress_bar = st.progress(1 / len(batches), text=f"Đang xử lý batch 1/{len(batches)}")
        for i, batch in enumerate(batches[1:], 1):
            try:
                self.vectorstore.add_documents(batch)
                progress_bar.progress((i + 1) / len(batches), text=f"Đang xử lý batch {i + 1}/{len(batches)}")
            except Exception as e:
                st.warning(f"Lỗi khi thêm batch {i + 1}: {e}")
                continue

        self.vectorstore.persist()
        st.success("🎉 Hoàn thành tạo vector database!")

    # --- CẢI TIẾN #2: Sử dụng Ensemble Retriever ---
    def get_query_results(self, query: str, k: int = 6) -> List[Dict[str, Any]]:
        """
        Truy vấn RAG sử dụng Ensemble Retriever để kết hợp điểm mạnh của
        similarity search và MMR.
        """
        if not self.vectorstore:
            if not self.check_and_fix_embedding_dimension():
                return []

        try:
            similarity_retriever = self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={'k': k}
            )
            mmr_retriever = self.vectorstore.as_retriever(
                search_type="mmr",
                search_kwargs={'k': k, 'fetch_k': 20}
            )

            ensemble_retriever = EnsembleRetriever(
                retrievers=[similarity_retriever, mmr_retriever],
                weights=[0.5, 0.5]
            )

            docs = ensemble_retriever.get_relevant_documents(query)
            unique_docs = {doc.page_content: doc for doc in docs}.values()

            return [{
                "content": doc.page_content,
                "metadata": doc.metadata,
                "similarity_score": "N/A (Ensemble)"  # Có thể bổ sung logic tính toán điểm số tổng hợp nếu muốn
            } for doc in unique_docs]
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

    def create_prompt_template(self, question: str, context: str) -> str:
        """Tạo prompt template hiệu quả cho LLM với các kỹ thuật nâng cao."""
        if context:
            return f"""Bạn là một chuyên gia phân tích tin tức AI, có nhiệm vụ tổng hợp thông tin một cách khách quan và chính xác.
**NGUYÊN TẮC VÀNG: CHỈ được phép sử dụng thông tin từ các TÀI LIỆU NGUỒN được cung cấp dưới đây. NGHIÊM CẤM sử dụng kiến thức bên ngoài.** Nếu thông tin không có trong tài liệu, hãy trả lời rõ ràng là: "Thông tin này không có trong các tài liệu được cung cấp."

**TÀI LIỆU NGUỒN:**
---
{context}
---

**CÂU HỎI CỦA NGƯỜI DÙNG:** {question}

**QUY TRÌNH SUY LUẬN VÀ TRẢ LỜI (Hãy tuân thủ nghiêm ngặt):**
1.  **Phân tích câu hỏi:** Đọc kỹ câu hỏi để hiểu rõ yêu cầu.
2.  **Đối chiếu với tài liệu:** Lần lượt đọc qua từng [Nguồn]. Tìm kiếm các đoạn văn bản liên quan trực tiếp đến câu hỏi.
3.  **Tổng hợp và Trích dẫn:**
    * Tổng hợp các thông tin tìm được từ các nguồn khác nhau để tạo thành một câu trả lời mạch lạc, đầy đủ.
    * **BẮT BUỘC** phải trích dẫn nguồn ngay sau mỗi thông tin bạn đưa ra. Ví dụ: "Việt Nam có tốc độ tăng trưởng kinh tế ấn tượng trong quý 1 [Nguồn 1], [Nguồn 3]."
    * Nếu các nguồn có thông tin mâu thuẫn, hãy nêu rõ sự mâu thuẫn đó.
4.  **Định dạng câu trả lời:**
    * Sử dụng markdown (gạch đầu dòng, in đậm) để câu trả lời dễ đọc.
    * Bắt đầu bằng một câu trả lời trực tiếp, sau đó đi vào chi tiết.

**TRẢ LỜI (theo đúng quy trình trên):**"""
        else:
            return f"""Bạn là một trợ lý AI thông minh và hữu ích. Hãy trả lời câu hỏi sau bằng kiến thức chung của bạn. Nếu bạn không chắc chắn, hãy nói rằng bạn không biết.

CÂU HỎI: {question}

TRẢ LỜI:"""

    # --- THÊM HÀM MỚI: Đánh giá độ liên quan của Context ---
    def _evaluate_context_relevance(self, question: str, context: str) -> bool:
        """
        Sử dụng LLM để đánh giá xem ngữ cảnh được cung cấp có đủ thông tin
        để trả lời câu hỏi hay không.
        Trả về True nếu đủ, False nếu không.
        """
        if not context:
            return False  # Không có context thì chắc chắn là không đủ

        eval_prompt = f"""Bạn là một AI đánh giá. Nhiệm vụ của bạn là xác định liệu đoạn TEXT được cung cấp có chứa đủ thông tin để trả lời trọn vẹn CÂU HỎI hay không.

**CÂU HỎI:** {question}

**TEXT ĐƯỢC CUNG CẤP:**
---
{context}
---

**HƯỚNG DẪN:**
-   Nếu TEXT chứa đủ thông tin để trả lời CÂU HỎI, hãy trả lời "CÓ".
-   Nếu TEXT KHÔNG chứa đủ thông tin để trả lời CÂU HỎI (ví dụ: thông tin không liên quan, quá mơ hồ, thiếu chi tiết), hãy trả lời "KHÔNG".
-   KHÔNG giải thích, KHÔNG trả lời câu hỏi, CHỈ trả lời "CÓ" hoặc "KHÔNG".

**ĐÁP ÁN:**"""

        try:
            response = self.llm_model.invoke(eval_prompt)
            decision = response.content.strip().upper()
            st.info(f"LLM đánh giá context: {decision}")  # Debug info
            return decision == "CÓ"
        except Exception as e:
            st.warning(f"Lỗi khi LLM đánh giá context: {e}. Mặc định coi là không đủ.")
            return False  # Nếu có lỗi, mặc định coi là context không đủ tốt

    def ask_question(self, question: str) -> Dict[str, Any]:
        """Quy trình hoàn chỉnh để hỏi và nhận câu trả lời từ chatbot."""
        try:
            query_results = self.get_query_results(question, k=6)

            final_results = []
            context_for_llm = ""
            has_rag_context = False

            if query_results:
                # Giới hạn số lượng context đưa vào LLM để tối ưu hiệu suất và chi phí
                final_results = query_results[:5]
                context_for_llm = self.create_context_from_results(final_results)

                # --- SỬA ĐỔI TẠI ĐÂY: Thêm bước đánh giá ngữ cảnh ---
                # Chỉ sử dụng RAG context nếu LLM đánh giá là có liên quan
                if self._evaluate_context_relevance(question, context_for_llm):
                    prompt = self.create_prompt_template(question, context_for_llm)
                    has_rag_context = True
                    st.info("Sử dụng RAG context sau khi LLM đánh giá đủ chất lượng.")
                else:
                    # Nếu context RAG không đủ chất lượng, bỏ qua RAG và dùng kiến thức chung
                    context_for_llm = ""  # Đảm bảo context rỗng để prompt chọn nhánh else
                    prompt = self.create_prompt_template(question, context_for_llm)
                    st.info("RAG context không đủ chất lượng, chuyển sang kiến thức chung.")
            else:
                # Nếu không có kết quả truy vấn nào từ Retriever, mặc định dùng kiến thức chung
                context_for_llm = ""
                prompt = self.create_prompt_template(question, context_for_llm)
                st.info("Không tìm thấy RAG context nào từ Retriever, sử dụng kiến thức chung.")

            response = self.llm_model.invoke(prompt)
            answer = response.content

            # Đảm bảo detailed_sources được tạo đúng cách ngay cả khi không có RAG context
            detailed_sources = [{
                "index": i + 1,
                "title": r["metadata"].get("title", "N/A"),
                "url": r["metadata"].get("url", ""),
            } for i, r in enumerate(final_results)] if has_rag_context and final_results else []

            return {
                "answer": answer,
                "detailed_sources": detailed_sources,
                "has_rag_context": has_rag_context,
                "context_used": context_for_llm
            }
        except Exception as e:
            st.error(f"Lỗi khi xử lý câu hỏi: {e}")
            return {
                "answer": "Xin lỗi, đã có lỗi xảy ra. Vui lòng thử lại.",
                "detailed_sources": [],
                "has_rag_context": False,
                "context_used": ""
            }


# --- Cấu hình Streamlit và Singleton Pattern (Giữ nguyên) ---
@st.cache_resource
def get_chatbot():
    """Tạo và cache singleton chatbot instance."""
    DB_NAME = "vector_db_optimized_v2"
    chatbot = RAGChatbot(db_name=DB_NAME)
    return chatbot


def build_qa_chain():
    """Khởi tạo hệ thống RAG và trả về chatbot instance."""
    chatbot = get_chatbot()
    if not chatbot.vectorstore:
        with st.spinner("Đang khởi tạo hệ thống RAG... (Quá trình này có thể mất vài phút nếu tạo database lần đầu)"):
            chatbot.check_and_fix_embedding_dimension()
    return chatbot


# --- Các hàm tiện ích (Giữ nguyên) ---
def ask_chatbot(question: str) -> Dict[str, Any]:
    """Hàm tiện ích để đặt câu hỏi cho chatbot."""
    chatbot = get_chatbot()
    return chatbot.ask_question(question)


def get_query_results_debug(question: str, k: int = 5):
    """Hàm tiện ích để debug, xem trực tiếp kết quả truy vấn RAG."""
    chatbot = get_chatbot()
    return chatbot.get_query_results(question, k)