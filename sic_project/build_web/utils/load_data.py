import pandas as pd
import pymongo
from pymongo import MongoClient
from typing import Optional, Dict, Any, List
import os
from datetime import datetime
import logging

# Cấu hình logging cơ bản
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Lấy CONNECTION_STRING từ biến môi trường
# Đây là cách an toàn hơn và linh hoạt hơn
# Đảm bảo bạn đã đặt biến môi trường MONGODB_CONNECTION_STRING
# Ví dụ: export MONGODB_CONNECTION_STRING="mongodb+srv://dekii2275:1234abcd@cluster0.gkgyn1q.mongodb.net/mydatabase?retryWrites=true&w=majority"
CONNECTION_STRING = os.getenv("MONGODB_CONNECTION_STRING")

# Kiểm tra nếu CONNECTION_STRING chưa được đặt
if not CONNECTION_STRING:
    # Cảnh báo và cung cấp giá trị mặc định (chỉ nên dùng cho mục đích phát triển/test cục bộ)
    default_conn_str = "mongodb+srv://dekii2275:1234abcd@cluster0.gkgyn1q.mongodb.net/"
    logger.warning(f"MONGODB_CONNECTION_STRING biến môi trường không được đặt. Sử dụng chuỗi kết nối mặc định: {default_conn_str}")
    CONNECTION_STRING = default_conn_str

class MongoDBConnector:
    """
    Lớp kết nối MongoDB Atlas và chuyển đổi dữ liệu thành DataFrame
    """
    
    def __init__(self, connection_string: str = CONNECTION_STRING):
        """
        Khởi tạo kết nối MongoDB Atlas
        
        Args:
            connection_string (str): Chuỗi kết nối MongoDB Atlas
        """
        self.connection_string = connection_string
        self.client = None
        self.db = None
        
    def connect(self):
        """Thiết lập kết nối đến MongoDB Atlas"""
        try:
            self.client = MongoClient(self.connection_string)
            # Test kết nối bằng cách gửi lệnh ping
            self.client.admin.command('ping')
            logger.info("Kết nối MongoDB Atlas thành công!")
            return True
        except pymongo.errors.ConnectionFailure as e:
            logger.error(f"Lỗi kết nối MongoDB Atlas: Không thể kết nối đến máy chủ. Vui lòng kiểm tra chuỗi kết nối và trạng thái mạng. Chi tiết: {e}")
            self.client = None # Đảm bảo client được đặt về None nếu kết nối thất bại
            return False
        except Exception as e:
            logger.error(f"Lỗi không xác định khi kết nối MongoDB Atlas: {e}")
            self.client = None
            return False
    
    def get_database(self, db_name: str):
        """
        Lấy database
        
        Args:
            db_name (str): Tên database
        """
        if self.client:
            self.db = self.client[db_name]
            logger.info(f"Đã chọn database: '{db_name}'")
            return self.db
        else:
            logger.error("Chưa kết nối đến MongoDB Atlas. Vui lòng gọi .connect() trước.")
            raise Exception("Chưa kết nối đến MongoDB Atlas")
    
    def collection_to_dataframe(self, 
                                 collection_name: str, 
                                 query: Optional[Dict[str, Any]] = None,
                                 projection: Optional[Dict[str, Any]] = None,
                                 limit: Optional[int] = None,
                                 sort: Optional[List[tuple]] = None) -> pd.DataFrame:
        """
        Chuyển đổi collection MongoDB thành DataFrame
        
        Args:
            collection_name (str): Tên collection
            query (dict, optional): Điều kiện truy vấn MongoDB
            projection (dict, optional): Các trường cần lấy
            limit (int, optional): Giới hạn số lượng bản ghi
            sort (list, optional): Sắp xếp dữ liệu [(field, direction)]
            
        Returns:
            pd.DataFrame: DataFrame chứa dữ liệu từ MongoDB
        """
        if self.db is None:
            logger.error("Chưa chọn database. Vui lòng gọi .get_database() trước.")
            return pd.DataFrame() # Trả về DataFrame rỗng thay vì raise Exception ở đây
            
        try:
            collection = self.db[collection_name]
            
            # Xây dựng truy vấn
            cursor = collection.find(query or {}, projection)
            
            # Áp dụng sắp xếp nếu có
            if sort:
                cursor = cursor.sort(sort)
            
            # Áp dụng limit nếu có
            if limit:
                cursor = cursor.limit(limit)
            
            # Chuyển đổi thành list và sau đó thành DataFrame
            data = list(cursor)
            
            if data:
                df = pd.DataFrame(data)
                # Chuyển đổi ObjectId thành string nếu có
                if '_id' in df.columns:
                    df['_id'] = df['_id'].astype(str)
                logger.info(f"Đã tải {len(df)} bản ghi từ collection '{collection_name}'.")
                return df
            else:
                logger.info(f"Collection '{collection_name}' trống hoặc không có bản ghi nào khớp với truy vấn.")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Lỗi khi chuyển đổi collection '{collection_name}' thành DataFrame: {e}")
            return pd.DataFrame()
    
    def aggregate_to_dataframe(self, 
                                 collection_name: str, 
                                 pipeline: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Thực hiện aggregation và chuyển thành DataFrame
        
        Args:
            collection_name (str): Tên collection
            pipeline (list): Pipeline aggregation của MongoDB
            
        Returns:
            pd.DataFrame: DataFrame chứa kết quả aggregation
        """
        if self.db is None:
            logger.error("Chưa chọn database. Vui lòng gọi .get_database() trước.")
            return pd.DataFrame() # Trả về DataFrame rỗng thay vì raise Exception
            
        try:
            collection = self.db[collection_name]
            cursor = collection.aggregate(pipeline)
            data = list(cursor)
            
            if data:
                df = pd.DataFrame(data)
                # Chuyển đổi ObjectId thành string nếu có
                if '_id' in df.columns:
                    df['_id'] = df['_id'].astype(str)
                logger.info(f"Aggregation trên collection '{collection_name}' trả về {len(df)} bản ghi.")
                return df
            else:
                logger.info(f"Aggregation trên collection '{collection_name}' không trả về kết quả nào.")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Lỗi khi thực hiện aggregation trên collection '{collection_name}': {e}")
            return pd.DataFrame()
    
    def close_connection(self):
        """Đóng kết nối"""
        if self.client:
            self.client.close()
            logger.info("Đã đóng kết nối MongoDB Atlas")

# Hàm tiện ích để load dữ liệu nhanh
def get_mongodb_data(db_name: str, 
                     collection_name: str,
                     query: Optional[Dict[str, Any]] = None,
                     projection: Optional[Dict[str, Any]] = None,
                     limit: Optional[int] = None,
                     sort: Optional[List[tuple]] = None) -> pd.DataFrame:
    """
    Hàm tiện ích để lấy dữ liệu từ MongoDB và chuyển thành DataFrame
    
    Args:
        db_name (str): Tên database
        collection_name (str): Tên collection
        query (dict, optional): Điều kiện truy vấn MongoDB
        projection (dict, optional): Các trường cần lấy
        limit (int, optional): Giới hạn số lượng bản ghi
        sort (list, optional): Sắp xếp dữ liệu [(field, direction)]
        
    Returns:
        pd.DataFrame: DataFrame chứa dữ liệu
        
    Ví dụ sử dụng:
        # Lấy tất cả dữ liệu
        df = get_mongodb_data("mydb", "users")
        
        # Lấy dữ liệu với điều kiện
        df = get_mongodb_data("mydb", "users", query={"age": {"$gte": 18}})
        
        # Lấy với giới hạn và sắp xếp
        df = get_mongodb_data("mydb", "users", limit=100, sort=[("created_at", -1)])
    """
    connector = MongoDBConnector()
    
    try:
        if not connector.connect(): # Nếu kết nối thất bại
            logger.error("Không thể kết nối đến MongoDB. Trả về DataFrame rỗng.")
            return pd.DataFrame() # Trả về DataFrame rỗng ngay lập tức
        
        connector.get_database(db_name)
        df = connector.collection_to_dataframe(
            collection_name=collection_name,
            query=query,
            projection=projection,
            limit=limit,
            sort=sort
        )
        connector.close_connection()
        return df
    except Exception as e:
        logger.error(f"Lỗi tổng quát khi lấy dữ liệu từ MongoDB: {e}")
        return pd.DataFrame()

# Load data từ Mongo
def load_news_data():
    df = get_mongodb_data("processed_data", "main_data", sort=[("time_posted", -1)])
    if df.empty:
        return []
    return df.to_dict(orient="records")


# --- Phần chạy thử nghiệm ---
if __name__ == "__main__":
    logger.info("Bắt đầu chạy thử nghiệm MongoDBConnector...")

    # Ví dụ: Lấy dữ liệu từ database "test_processed_data" và collection "test_main_data"
    # Đảm bảo database và collection này tồn tại trong MongoDB Atlas của bạn
    # và chứa dữ liệu.
    data = get_mongodb_data("test_processed_data", "test_main_data")
    
    if not data.empty:
        logger.info("Dữ liệu đã tải thành công:")
        print(data.head()) # In ra 5 dòng đầu
        logger.info(f"Tổng số bản ghi: {len(data)}")
    else:
        logger.warning("Không có dữ liệu được tải. Vui lòng kiểm tra:")
        logger.warning("- Chuỗi kết nối MongoDB Atlas (username, password, host)")
        logger.warning("- Tên database ('test_processed_data')")
        logger.warning("- Tên collection ('test_main_data')")
        logger.warning("- Dữ liệu có tồn tại trong collection đó không?")
        logger.warning("- Cài đặt quyền truy cập IP trong MongoDB Atlas (cho phép IP của bạn)")
    
    logger.info("Kết thúc chạy thử nghiệm.")