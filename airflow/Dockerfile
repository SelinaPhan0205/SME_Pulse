# ===================================================
# Custom Airflow Image with dbt pre-installed
# ===================================================
FROM apache/airflow:2.9.3-python3.11

USER airflow
# Cài dbt-core và dbt-postgres với airflow user
RUN pip install --no-cache-dir \
    dbt-core \
    dbt-postgres==1.8.2

# Copy dbt project vào image từ build context (parent directory)
COPY --chown=airflow:airflow ./dbt /opt/dbt

# Thêm dbt vào PATH để bash tìm thấy
ENV PATH="/home/airflow/.local/bin:${PATH}"

# Verify installation
RUN dbt --version
