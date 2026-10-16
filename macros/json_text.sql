{# A JSON field as text. DuckDB and Databricks name this function differently. #}
{% macro json_text(column, path) %}
    {%- if target.type == 'databricks' -%}
    get_json_object({{ column }}, '{{ path }}')
    {%- else -%}
    json_extract_string({{ column }}, '{{ path }}')
    {%- endif -%}
{% endmacro %}
