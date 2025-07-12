import os
import json
import pandas as pd
from pymongo import MongoClient
from datetime import datetime
import logging

# Import Airflow BaseHook để lấy Connection (nếu bạn muốn sử dụng Airflow Connections)
try:
    from airflow.hooks.base import BaseHook
    AIRFLOW_HOOKS_AVAILABLE = True
except ImportError:
    AIRFLOW_HOOKS_AVAILABLE = False
    logging.warning("Airflow BaseHook not available. MongoDB connection string must be provided directly.")

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_mongo_connection_string(conn_id: str = "mongo_atlas_connection") -> str:
    """
    Lấy MongoDB connection string từ Airflow Connections.
    Args:
        conn_id: ID của MongoDB Connection trong Airflow UI.
    Returns:
        str: MongoDB connection string.
    Raises:
        ValueError: Nếu Airflow Hook không khả dụng hoặc Connection không tồn tại.
    """
    if not AIRFLOW_HOOKS_AVAILABLE:
        raise ValueError("Airflow BaseHook không khả dụng. Vui lòng cung cấp connection string trực tiếp.")
    
    try:
        conn = BaseHook.get_connection(conn_id)
        
        # Ưu tiên lấy URI nếu Airflow đã tự động tạo nó
        if conn.host and conn.host.startswith("mongodb"):
            logger.info(f"Đã lấy URI từ Airflow Connection '{conn_id}' (trường host): {conn.host}")
            return conn.host
        
        # Nếu không có URI, xây dựng nó từ các trường
        # Đối với MongoDB Atlas, định dạng thường là mongodb+srv://user:password@host/database_name?retryWrites=true&w=majority
        # Schema (database_name) là tùy chọn trong URI, nếu không có thì mặc định là 'admin' hoặc không có database cụ thể
        
        username = conn.login
        password = conn.password
        host = conn.host
        
        if not username or not password or not host:
            raise ValueError(f"Các thông tin cần thiết (username, password, host) không đầy đủ trong Airflow Connection ID: {conn_id}")

        # Thêm các tham số Atlas mặc định nếu cần
        # Ví dụ: ?retryWrites=true&w=majority
        params = ""
        if conn.extra_dejson and isinstance(conn.extra_dejson, dict):
            extra_params = conn.extra_dejson.get("uri_params")
            if extra_params:
                params = "?" + extra_params # Ví dụ: "retryWrites=true&w=majority"
        
        # Nếu schema (database name) có trong Airflow Connection
        database_part = f"/{conn.schema}" if conn.schema else ""

        connection_string = f"mongodb+srv://{username}:{password}@{host}{database_part}{params}"
        logger.info(f"Đã xây dựng connection string từ Airflow Connection '{conn_id}': {connection_string}")
        return connection_string

    except Exception as e:
        raise ValueError(f"Không thể lấy hoặc xây dựng Airflow Connection '{conn_id}': {e}")


def upload_articles_to_mongodb(
    articles_data: list,
    connection_string: str,
    database_name: str = "processed_data",
    collection_name: str = "main_data"
) -> bool:
    """
    Đẩy danh sách các bài viết đã xử lý lên MongoDB.
    Mỗi bài viết sẽ là một document riêng biệt.
    
    Args:
        articles_data: Danh sách các dict bài viết.
        connection_string: MongoDB connection string.
        database_name: Tên database.
        collection_name: Tên collection.
    
    Returns:
        bool: True nếu thành công, False nếu thất bại.
    """
    
    if not connection_string:
        logger.error("Connection string không được để trống.")
        return False
    
    if not articles_data:
        logger.info("Không có dữ liệu bài viết để upload.")
        return True # Coi như thành công nếu không có gì để upload
    
    client = None
    try:
        # Quan trọng: MongoClient sẽ phân tích mongodb+srv URI đúng cách.
        # Đảm bảo pymongo được cập nhật.
        client = MongoClient(connection_string) 
        db = client[database_name]
        collection = db[collection_name]
        
        client.admin.command('ping')
        logger.info("Kết nối MongoDB thành công.")

        # Thêm trường timestamp vào mỗi document trước khi insert
        timestamp = datetime.now()
        for article in articles_data:
            article['upload_timestamp'] = timestamp
        
        # Insert nhiều documents cùng lúc
        insert_result = collection.insert_many(articles_data, ordered=False) # ordered=False để tiếp tục insert nếu có lỗi 1 document
        logger.info(f"Đã insert {len(insert_result.inserted_ids)} bài viết mới vào collection '{collection_name}'.")
        
        # Có thể thêm logic tạo index tại đây nếu cần
        # Ví dụ: collection.create_index("id", unique=True)
        # collection.create_index("time_posted")
        
        return True
        
    except Exception as e:
        logger.error(f"Lỗi khi upload dữ liệu lên MongoDB: {e}")
        return False
        
    finally:
        if client:
            client.close()
            logger.info("Đã đóng kết nối MongoDB.")

def main(input_filename: str = "processed_all_news_combined.json", 
          airflow_mongo_conn_id: str = "mongo_atlas_connection", # Đảm bảo đúng ID này
          database_name: str = "processed_data", 
          collection_name: str = "main_data",
          connection_string: str = None,
          data_path: str = None) -> bool:
    """
    Hàm chính để đọc file JSON đã xử lý và upload lên MongoDB.
    Args:
        input_filename: Tên file JSON chứa dữ liệu đã xử lý.
        airflow_mongo_conn_id: ID của MongoDB Connection trong Airflow UI.
        database_name: Tên database MongoDB.
        collection_name: Tên collection MongoDB.
        connection_string: MongoDB connection string (dùng khi chạy độc lập).
        data_path: Đường dẫn đến thư mục chứa file data (tùy chọn).
    Returns:
        bool: True nếu upload thành công, False nếu thất bại.
    """
    # Xác định đường dẫn data dựa trên cấu trúc thư mục thực tế
    if data_path is None:
        # Kiểm tra xem có đang chạy trong môi trường Airflow không
        if os.environ.get('AIRFLOW_HOME'):
            # Trong Airflow Docker container
            base_data_path = "/opt/airflow/sic_project/data"
        else:
            # Chạy độc lập - từ process_data/ lên sic_project/data/
            current_dir = os.path.dirname(os.path.abspath(__file__))
            base_data_path = os.path.join(current_dir, "../data")
    else:
        base_data_path = data_path
    
    json_file_path = os.path.join(base_data_path, input_filename)
    
    # Log thông tin debug
    logger.info(f"Đang tìm file tại: {json_file_path}")
    logger.info(f"Thư mục hiện tại: {os.getcwd()}")
    logger.info(f"Thư mục data: {base_data_path}")
    
    if not os.path.exists(json_file_path):
        logger.error(f"Không tìm thấy file JSON đầu vào: {json_file_path}")
        # Liệt kê các file trong thư mục để debug
        if os.path.exists(base_data_path):
            logger.info(f"Các file có trong thư mục {base_data_path}:")
            for file in os.listdir(base_data_path):
                logger.info(f"   - {file}")
        else:
            logger.error(f"Thư mục data không tồn tại: {base_data_path}")
        return False
    
    data = []
    try:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        logger.info(f"Đã đọc thành công {len(data)} bài viết từ file: {json_file_path}")
    except json.JSONDecodeError as e:
        logger.error(f"Lỗi khi đọc file JSON '{json_file_path}': {e}")
        return False
    except Exception as e:
        logger.error(f"Lỗi không xác định khi đọc file: {e}")
        return False
    
    try:
        # Lấy connection string
        if connection_string:
            # Sử dụng connection string được cung cấp trực tiếp (dùng cho test/dev)
            mongo_conn_str = connection_string
            logger.info("Sử dụng connection string được cung cấp trực tiếp.")
        else:
            # Lấy connection string từ Airflow Connection (dùng trong môi trường Airflow)
            mongo_conn_str = get_mongo_connection_string(airflow_mongo_conn_id)
            logger.info(f"Sử dụng connection string từ Airflow Connection '{airflow_mongo_conn_id}'.")
        
        # Upload dữ liệu lên MongoDB
        success = upload_articles_to_mongodb(
            articles_data=data,
            connection_string=mongo_conn_str,
            database_name=database_name,
            collection_name=collection_name
        )

        # Xóa file local sau khi upload thành công
        if success:
            try:
                os.remove(json_file_path)
                logger.info(f"Đã xóa file input: {json_file_path}")
            except OSError as e:
                logger.warning(f"Không thể xóa file {json_file_path}: {e}")
        
        return success

    except ValueError as e: # Bắt lỗi từ get_mongo_connection_string
        logger.error(f"Lỗi cấu hình MongoDB Connection: {e}")
        return False
    except Exception as e:
        logger.error(f"Lỗi tổng quát trong hàm main: {e}")
        return False


if __name__ == "__main__":
    logger.info("Chạy connect_mongo.py trong chế độ độc lập (để kiểm thử)...")
    
    # Tạo thư mục data nếu chưa có - đường dẫn từ process_data/ lên sic_project/data/
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(current_dir, "../data")
    
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        logger.info(f"Đã tạo thư mục data: {data_dir}")
    
    # Tạo một file dummy để test nếu chưa có
    dummy_input_path = os.path.join(data_dir, "processed_all_news_combined.json")
    if not os.path.exists(dummy_input_path):
        dummy_data = [
            {"id": "test1", "title": "Test Article 1", "content": "This is a test content.", "original_url": "http://example.com/1", "source": "test_source"},
            {"id": "test2", "title": "Test Article 2", "content": "Another test content.", "original_url": "http://example.com/2", "source": "test_source"}
        ]
        with open(dummy_input_path, "w", encoding="utf-8") as f:
            json.dump(dummy_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Đã tạo file dummy '{dummy_input_path}' để kiểm thử.")

    # Lấy connection string từ biến môi trường hoặc hardcode cho mục đích test
    # Đảm bảo connection string này khớp với MongoDB Atlas của bạn
    # Ví dụ: "mongodb+srv://<username>:<password>@cluster0.gkgyn1q.mongodb.net/testdb?retryWrites=true&w=majority"
    mongo_conn_str = os.environ.get("MONGODB_CONNECTION_STRING", "mongodb+srv://dekii2275:1234abcd@cluster0.gkgyn1q.mongodb.net/")

    success = main(
        input_filename="processed_all_news_combined.json",
        airflow_mongo_conn_id="mongo_atlas_connection", # Đảm bảo đúng ID này
        connection_string=mongo_conn_str,
        database_name="test_processed_data",
        collection_name="test_main_data"
    )

    if success:
        logger.info("✅ Upload thành công trong chế độ độc lập.")
    else:
        logger.error("❌ Upload thất bại trong chế độ độc lập.")