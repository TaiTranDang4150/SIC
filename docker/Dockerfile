# docker/Dockerfile

# --- Base Image ---
# Sử dụng phiên bản Airflow và Python được chỉ định
ARG AIRFLOW_VERSION=2.10.5
ARG PYTHON_VERSION=3.10
FROM apache/airflow:${AIRFLOW_VERSION}-python${PYTHON_VERSION}

# --- Switch to root to install system packages ---
USER root

# Cài đặt các gói hệ thống cần thiết cho Google Chrome
RUN apt-get update && \
    apt-get install -y gosu && \
    rm -rf /var/lib/apt/lists/*

# Bỏ qua cài đặt gosu vì base image của Airflow đã có
RUN apt-get update && \
    apt-get install -yq --no-install-recommends \
        curl \
        unzip \
        libnss3 \
        libxss1 \
        libappindicator1 \
        libappindicator3-1 \
        fonts-liberation \
        xdg-utils \
        gnupg && \
    # Thêm key và repo để cài Google Chrome
    curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable && \
    apt-get clean && rm -rf /var/lib/apt/lists/* # Đảm bảo dọn dẹp cache

# --- Switch to Airflow user to install Python packages ---
USER airflow 

# Sao chép requirements.txt vào image và cài đặt
# ĐÂY LÀ PHẦN QUAN TRỌNG CẦN ĐƯA TRỞ LẠI!
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Đảm bảo các thư mục cần thiết tồn tại và có quyền
# Các thư mục này cũng sẽ được volume mount từ host
# RUN mkdir -p /opt/airflow/dags /opt/airflow/logs /opt/airflow/plugins /opt/airflow/output /opt/airflow/sic_project && \
#     chown -R airflow:airflow /opt/airflow/dags /opt/airflow/logs /opt/airflow/plugins /opt/airflow/output /opt/airflow/sic_project

# Chuyển về user root để đảm bảo entrypoint của Airflow hoạt động đúng
# Airflow entrypoint sẽ tự chuyển đổi người dùng nếu cần thiết
USER root