# ===================================================
# Custom Trino with S3/MinIO Support
# ===================================================
FROM trinodb/trino:latest

USER root

# Download Hadoop AWS libraries for S3A support
RUN curl -L https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.6/hadoop-aws-3.3.6.jar \
    -o /usr/lib/trino/plugin/iceberg/hadoop-aws-3.3.6.jar && \
    curl -L https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.367/aws-java-sdk-bundle-1.12.367.jar \
    -o /usr/lib/trino/plugin/iceberg/aws-java-sdk-bundle-1.12.367.jar && \
    curl -L https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.6/hadoop-aws-3.3.6.jar \
    -o /usr/lib/trino/plugin/hive/hadoop-aws-3.3.6.jar && \
    curl -L https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.367/aws-java-sdk-bundle-1.12.367.jar \
    -o /usr/lib/trino/plugin/hive/aws-java-sdk-bundle-1.12.367.jar

USER trino