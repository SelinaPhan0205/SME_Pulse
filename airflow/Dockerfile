# ===================================================
# Custom Airflow Image with dbt pre-installed
# ===================================================
FROM apache/airflow:2.9.3-python3.11

USER airflow
# Cài dbt-core và dbt-trino cho Lakehouse stack
RUN pip install --no-cache-dir \
    dbt-core \
    dbt-trino==1.8.1 \
    boto3 \
    openpyxl \
    pyarrow \
    minio \
    requests \
    pandas \
    mlflow \
    prophet \
    scikit-learn \
    trino

# Copy dbt project vào image từ build context (parent directory)
COPY --chown=airflow:airflow ./dbt /opt/dbt

# Copy ops folder (ML scripts) vào image
COPY --chown=airflow:airflow ./ops /opt/ops

# Thêm dbt và ops vào PATH để bash tìm thấy
ENV PATH="/home/airflow/.local/bin:${PATH}"
ENV PYTHONPATH="/opt:${PYTHONPATH}"

# Verify installation
RUN dbt --version
