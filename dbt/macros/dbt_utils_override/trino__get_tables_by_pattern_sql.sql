{% macro trino__get_tables_by_pattern_sql(schema_pattern, table_pattern, exclude='', database=target.database) %}
    select distinct
        table_schema as {{ adapter.quote('table_schema') }},
        table_name as {{ adapter.quote('table_name') }},
        case table_type
            when 'BASE TABLE' then 'table'
            when 'EXTERNAL TABLE' then 'external'
            when 'MATERIALIZED VIEW' then 'materializedview'
            else lower(table_type)
        end as {{ adapter.quote('table_type') }}
    from {{ database }}.information_schema.tables
    where table_schema like '{{ schema_pattern }}'
      and table_name like '{{ table_pattern }}'
      and table_name not like '{{ exclude }}'
{% endmacro %}
