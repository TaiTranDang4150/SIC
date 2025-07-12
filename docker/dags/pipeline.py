import sys
import os

# --- Bắt đầu phần quản lý đường dẫn (ĐÃ SỬA) ---
# Đường dẫn tới thư mục gốc của mã nguồn dự án trong container
# Đảm bảo đường dẫn này KHỚP với vị trí bạn mount 'sic_project' trong docker-compose.yaml
project_code_root = '/opt/airflow/sic_project'
if project_code_root not in sys.path:
    sys.path.insert(0, project_code_root) # Thêm vào đầu sys.path để ưu tiên

# --- KẾT THÚC phần quản lý đường dẫn ---


# Import các modules cần thiết từ Airflow và Python chuẩn
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.task_group import TaskGroup

# --- Import các modules từ dự án sic_project của bạn (ĐÃ SỬA) ---
# Vì 'project_code_root' (/opt/airflow/sic_project) đã được thêm vào sys.path,
# bạn import trực tiếp từ các thư mục con của nó.
# KHÔNG CẦN tiền tố 'sic_project' ở đây nữa.
from crawl_data.crawl_data import crawl_all_sites
from process_data.processdt import main as process_main
from process_data.connect_mongo import main as connect_mongo_main # Tên file là connect_mongo.py, hàm là connect_mongo_main

# Định nghĩa các arguments mặc định
default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Tạo DAG
# CHỈ SỬ DỤNG KHỐI `with DAG(...) as dag:` để định nghĩa TẤT CẢ các task và task group
with DAG(
    dag_id='data_pipeline_dag',
    default_args=default_args,
    description='Pipeline để crawl data, xử lý và lưu vào MongoDB',
    schedule_interval=timedelta(hours=6),  # Chạy mỗi 6 giờ
    catchup=False,
    max_active_runs=1,
    tags=['data', 'pipeline', 'etl']
) as dag: # <-- Bắt đầu ngữ cảnh của DAG

    # Hàm wrapper cho crawl_data (giữ nguyên)
    def run_crawl_data(**context):
        """
        Chạy quá trình crawl dữ liệu từ tất cả các trang báo
        """
        try:
            print("Bắt đầu crawl dữ liệu từ tất cả các trang báo...")
            # Crawl từ tất cả các trang với limit 50 bài/trang
            results = crawl_all_sites(limit=50)

            # Kiểm tra kết quả
            success_count = 0
            total_articles = 0

            for site, result in results.items():
                if result["success"]:
                    success_count += 1
                    total_articles += result["count"]
                    print(f"✅ {site}: {result['count']} bài báo")
                else:
                    print(f"❌ {site}: {result['error']}")

            print(f"📊 Tổng kết: {success_count}/{len(results)} trang thành công, {total_articles} bài báo")
            
            # Trả về kết quả cho các task tiếp theo
            context['task_instance'].xcom_push(key='crawl_results', value=results)
            context['task_instance'].xcom_push(key='total_articles', value=total_articles)
            
            return results
            
        except Exception as e:
            print(f"Lỗi khi crawl data: {str(e)}")
            raise

    # Hàm wrapper cho process_data (giữ nguyên)
    def run_process_data(**context):
        """
        Chạy quá trình xử lý dữ liệu
        """
        try:
            print("Bắt đầu xử lý dữ liệu...")
            
            # Lấy kết quả từ task crawl_data (chỉ để in ra log hoặc kiểm tra, không nhất thiết phải dùng nếu hàm process_main đọc từ file)
            crawl_results = context['task_instance'].xcom_pull(task_ids='data_processing_group.crawl_data', key='crawl_results')
            total_articles = context['task_instance'].xcom_pull(task_ids='data_processing_group.crawl_data', key='total_articles')
            
            print(f"Nhận được {total_articles} bài báo từ crawl_data (nếu cần)")

            result = process_main() # Giả định process_main đọc từ file đã crawl
            print(f"Xử lý dữ liệu hoàn thành: {result}")
            
            # Push kết quả cho task tiếp theo
            context['task_instance'].xcom_push(key='process_results', value=result)
            
            return result
        except Exception as e:
            print(f"Lỗi khi xử lý dữ liệu: {str(e)}")
            raise

    # Hàm wrapper cho connect_mongo (giữ nguyên)
    def run_connect_mongo(**context):
        """
        Chạy quá trình kết nối và lưu dữ liệu vào MongoDB
        """
        try:
            print("Bắt đầu kết nối MongoDB và lưu dữ liệu...")

            result = connect_mongo_main( # Đảm bảo tên hàm đúng
                input_filename="processed_all_news_combined.json",
                airflow_mongo_conn_id="mongo_atlas_connection",
                database_name="processed_data",
                collection_name="main_data"
            )

            if result:
                print(f"Kết nối MongoDB hoàn thành và dữ liệu đã được lưu.")
            else:
                raise Exception("Upload dữ liệu lên MongoDB thất bại.")

            return result
        except Exception as e:
            print(f"Lỗi khi kết nối MongoDB: {str(e)}")
            raise

    # Cấu hình task groups (CHUYỂN VÀO BÊN TRONG KHỐI with DAG)
    with TaskGroup("data_processing_group") as data_group: # Bỏ 'dag=dag' ở đây, vì nó đã nằm trong ngữ cảnh của DAG
        # Task 1: Crawl Data
        crawl_data_task = PythonOperator(
            task_id='crawl_data',
            python_callable=run_crawl_data,
            doc_md="""
            ### Crawl Data Task
            
            Task này sẽ:
            - Crawl dữ liệu từ các nguồn đã định nghĩa
            - Lưu dữ liệu thô vào thư mục data
            - Tạo log cho quá trình crawl
            """,
        )

        # Task 2: Process Data
        process_data_task = PythonOperator(
            task_id='process_data',
            python_callable=run_process_data,
            doc_md="""
            ### Process Data Task
            
            Task này sẽ:
            - Xử lý dữ liệu thô từ bước crawl
            - Làm sạch và chuẩn hóa dữ liệu
            - Chuẩn bị dữ liệu cho việc lưu trữ
            """,
        )

        # Task 3: Connect MongoDB
        connect_mongo_task = PythonOperator(
            task_id='connect_mongo',
            python_callable=run_connect_mongo,
            doc_md="""
            ### Connect MongoDB Task
            
            Task này sẽ:
            - Kết nối tới MongoDB
            - Lưu dữ liệu đã xử lý vào database
            - Tạo index và optimize performance
            """,
        )

        # Định nghĩa dependencies NỘI BỘ trong nhóm
        crawl_data_task >> process_data_task >> connect_mongo_task

    # Task cleanup (CHUYỂN VÀO BÊN TRONG KHỐI with DAG, bỏ dag=dag vì nó tự động được gán)
    cleanup_task = BashOperator(
        task_id='cleanup_temp_files',
        bash_command="""
        # Dọn dẹp các file tạm nếu có
        # Đường dẫn này cần là đường dẫn TƯƠNG ĐỐI TỪ GỐC CONTAINER hoặc TUYỆT ĐỐI.
        # Nếu sic_project được mount vào /opt/airflow/sic_project, thì đường dẫn là:
        find /opt/airflow/sic_project/data -name "*.tmp" -delete
        find /opt/airflow/sic_project/logs -name "*.log" -mtime +7 -delete
        """,
    )

    # Task thông báo hoàn thành (CHUYỂN VÀO BÊN TRONG KHỐI with DAG, bỏ dag=dag)
    notification_task = PythonOperator(
        task_id='send_notification',
        python_callable=lambda **context: print("Pipeline hoàn thành thành công!"),
    )

    # Định nghĩa dependencies tổng thể của DAG (giữ nguyên)
    data_group >> cleanup_task >> notification_task

    # Thông tin thêm cho DAG (giữ nguyên)
    dag.doc_md = """
    # Data Pipeline DAG

    ## Mô tả
    DAG này thực hiện pipeline xử lý dữ liệu với các bước:
    1. **Crawl Data**: Thu thập dữ liệu từ các nguồn
    2. **Process Data**: Xử lý và làm sạch dữ liệu
    3. **Connect MongoDB**: Lưu dữ liệu vào MongoDB

    ## Cấu trúc thư mục
    """
# <-- Kết thúc ngữ cảnh của DAG