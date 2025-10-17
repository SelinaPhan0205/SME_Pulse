{#
 ===================================================
 Macro: generate_schema_name (OVERRIDE)
 ===================================================
 Mục đích: 
   - Override default dbt behavior
   - Thay vì tạo schema: public_silver, public_gold
   - Chỉ dùng custom schema: silver, gold
 
 Default behavior (dbt built-in):
   - Dev: {target_schema}_{custom_schema} 
     VD: public_silver, public_gold
   - Prod: {custom_schema}
     VD: silver, gold
 
 Custom behavior (macro này):
   - Dev & Prod đều dùng: {custom_schema}
     VD: silver, gold
 ===================================================
#}

{% macro generate_schema_name(custom_schema_name, node) -%}

    {%- set default_schema = target.schema -%}
    
    {#- 
        Nếu không có custom_schema_name 
        → Dùng default schema (public)
    -#}
    {%- if custom_schema_name is none -%}
        {{ default_schema }}

    {#- 
        Nếu có custom_schema_name
        → Dùng TRỰC TIẾP custom_schema_name
        (Không nối với target.schema)
    -#}
    {%- else -%}
        {{ custom_schema_name | trim }}

    {%- endif -%}

{%- endmacro %}
