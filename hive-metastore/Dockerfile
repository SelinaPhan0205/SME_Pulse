# ===================================================
# Custom Hive Metastore with PostgreSQL JDBC Driver + AWS S3 Support
# ===================================================
FROM apache/hive:4.0.0

USER root

# Copy PostgreSQL JDBC driver
COPY postgresql-42.7.1.jar /opt/hive/lib/postgresql-42.7.1.jar

# Copy Hadoop core-site.xml for S3A configuration
COPY core-site.xml /opt/hadoop/etc/hadoop/core-site.xml

# Copy AWS libraries from tools to common lib (already in image!)
RUN cp /opt/hadoop/share/hadoop/tools/lib/hadoop-aws-3.3.6.jar /opt/hadoop/share/hadoop/common/lib/ && \
    cp /opt/hadoop/share/hadoop/tools/lib/aws-java-sdk-bundle-1.12.367.jar /opt/hadoop/share/hadoop/common/lib/

USER hive

# Expose Metastore port
EXPOSE 9083
