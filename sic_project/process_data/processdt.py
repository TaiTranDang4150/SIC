import sys
import os

# ==== Cân nhắc về sys.path.append ====
# Giữ lại dòng này nếu bạn muốn file này chạy độc lập.
# Trong môi trường Airflow Docker đã được cấu hình với volume mount
# và sys.path.append trong DAG, dòng này có thể không cần thiết
# hoặc có thể gây ra đường dẫn phức tạp.
# Tuy nhiên, để đảm bảo tính độc lập, ta có thể giữ lại.
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import json
from pathlib import Path
from typing import Optional, Dict
import re
import dateparser

# ==== Quan trọng: Đảm bảo import từ đúng vị trí sau khi sys.path được cập nhật ====
# Nếu sys.path.append ở trên đã chạy, thì import này sẽ tìm 'sic_project' từ thư mục root.
# Nếu không, nó sẽ tìm từ thư mục dags/sic_project/model...
# Với cấu hình docker-compose và sys.path.append trong DAG, import này là chính xác.
# from model.VPhoBertTaggermaster.vphoberttagger.predictor import extract
from model.VPhoBertTaggermaster.test import extract_entities, predict_ner


# ==== Chuẩn hóa thời gian ====
def normalize_time(raw_time: str) -> Optional[str]:
    try:
        dt = dateparser.parse(
            raw_time,
            languages=['vi'],
            settings={
                'TIMEZONE': 'Asia/Ho_Chi_Minh',
                'RETURN_AS_TIMEZONE_AWARE': True,
                'PREFER_DAY_OF_MONTH': 'first'
            }
        )
        return dt.isoformat() if dt else None
    except Exception as e:
        print(f"⚠️ Lỗi khi chuẩn hóa thời gian '{raw_time}': {e}") # Thêm raw_time vào log
        return None

# Xử lý tác giả
def safe_author(author):
    if isinstance(author, list):
        return ", ".join(author)
    elif isinstance(author, str):
        return author.strip()
    else:
        return ""


# ==== Làm sạch nội dung ====
def clean_content(text: str, author: Optional[str] = None) -> str:
    if not text:
        return ""

    text = text.replace('\\"', ' ').replace("\\'", " ").replace("\"", " ")
    text = re.sub(r"-\s*\n\s*", "-", text)
    text = re.sub(r"\n\d{1,3}\s*$", "", text)
    text = re.sub(r"\n?(Ảnh|Photo):.*", "", text)

    if author:
        # Sử dụng re.escape để xử lý các ký tự đặc biệt trong tên tác giả
        pattern = re.escape(author.strip())
        text = re.sub(rf"^{pattern}\s*\n*(Nhà báo|Phóng viên)?\s*\n*", "", text, flags=re.IGNORECASE)
        text = re.sub(rf"\n?{pattern}\s*$", "", text)

    text = re.sub(r"\n\s*\n+", "\n", text)
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()

# ==== Xử lý tags ====
def clean_tags(tags):
    if not tags:
        return []
    return [tag.strip() for tag in tags if tag.strip() != '']


# ==== Lấy NER tags ====
def get_ner_tag(content):
    try:
        if not content or not content.strip():
            return []
        
        tokens, labels = predict_ner(content)
        entities = extract_entities(tokens, labels)
        return entities
    except Exception as e:
        print(f"⚠️ Lỗi khi trích xuất NER: {e}")
        return []


# ==== Tiền xử lý 1 bài ====
def preprocess_article(article: Dict) -> Dict:
    try:
        author = safe_author(article.get("author"))
        cleaned_content = clean_content(article.get("content", ""), author)

        return {
            "id": article.get("id"),
            "title": article.get("title", "").strip(),
            "url": article.get("url"),
            "author": author,
            "tags": clean_tags(article.get("tags", [])),
            "time_posted": normalize_time(article.get("time_posted", "")),
            "content": cleaned_content,
            "description": article.get("description", "").strip(),
            "image": article.get("image"),
            "popular_tags": get_ner_tag(cleaned_content)
        }
    except Exception as e:
        print(f"⚠️ Lỗi khi xử lý bài viết ID {article.get('id', 'Unknown')}: {e}")
        return None

# ==== Xử lý toàn bộ file (đây sẽ là hàm main cho Airflow) ====
def main(input_filename: str = "all_news_combined.json", output_filename: str = "processed_all_news_combined.json"):
    """
    Hàm chính để tiền xử lý dữ liệu.
    Nhận tên file input và output, xử lý từ thư mục 'data' tương đối.
    """
    # Đường dẫn data trong môi trường Docker của Airflow
    # /opt/airflow/dags/sic_project/data/
    base_data_path = "/opt/airflow/sic_project/data"
    input_path = os.path.join(base_data_path, input_filename)
    output_path = os.path.join(base_data_path, output_filename)


    if not Path(input_path).exists():
        print(f"❌ Không tìm thấy file input: {input_path}")
        return False

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Lỗi đọc file JSON '{input_path}': {e}")
        return False
    except Exception as e:
        print(f"❌ Lỗi khi mở file '{input_path}': {e}")
        return False

    print(f"🔍 Đọc {len(raw_data)} bài viết từ {input_path}")

    cleaned_data = []
    processed_count = 0
    skipped_count = 0
    for article in raw_data:
        # Kiểm tra nội dung trước khi xử lý
        if article.get("content") and article.get("content").strip():
            processed = preprocess_article(article)
            if processed:
                cleaned_data.append(processed)
                processed_count += 1
            else:
                print(f"⚠️ Bỏ qua bài viết ID {article.get('id', 'Unknown')} do lỗi xử lý.")
                skipped_count += 1
        else:
            print(f"ℹ️ Bỏ qua bài viết ID {article.get('id', 'Unknown')} do không có nội dung.")
            skipped_count += 1

    print(f"✅ Đã xử lý thành công {processed_count} bài viết. Bỏ qua {skipped_count} bài.")
    print(f"Tổng số bài viết sau xử lý: {len(cleaned_data)}")


    try:
        # Tạo thư mục output nếu chưa tồn tại
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Đã lưu dữ liệu chuẩn hóa vào: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Lỗi khi lưu file '{output_path}': {e}")
        return False


if __name__ == "__main__":
    # Khi chạy độc lập, vẫn giả định cấu trúc thư mục từ project root
    # Đảm bảo sys.path.append ở đầu file được kích hoạt nếu chạy độc lập
    
    # Đối với môi trường dev/test độc lập trên máy local,
    # có thể cần điều chỉnh đường dẫn này nếu cấu trúc thư mục khác với Airflow Docker
    
    # Giả định chạy từ PROJECT_ROOT/sic_project/process_data/
    # input_path và output_path phải trỏ đúng đến ../data/
    
    # sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))) # Đã uncomment nếu cần
    
    # Để đơn giản và nhất quán, bạn có thể gọi hàm main() với các tham số mặc định
    # hoặc truyền đường dẫn đầy đủ nếu bạn biết nó ở đâu trong môi trường độc lập.
    # Ví dụ nếu chạy từ project root:
    # main(input_filename="sic_project/data/all_news_combined.json", 
    #      output_filename="sic_project/data/processed_all_news_combined.json")

    # Giữ nguyên như cũ nếu bạn chỉ chạy độc lập từ chính thư mục process_data và muốn nó tự tìm đường dẫn.
    # Tuy nhiên, để test hàm main() như nó sẽ được gọi từ Airflow, nên dùng:
    print("Running processdt.py in standalone mode (for testing)...")
    success = main(input_filename="all_news_combined.json", output_filename="processed_all_news_combined.json")

    if success:
        print("✅ Xử lý thành công trong chế độ độc lập.")
    else:
        print("❌ Xử lý thất bại trong chế độ độc lập.")