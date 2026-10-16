{# Round a whole-unit amount to the currency's decimal places. Spark's round needs a fixed scale, so the rounding is done by hand there. #}
{% macro round_major(amount_expr, places_expr) %}
    {%- if target.type == 'databricks' -%}
    round({{ amount_expr }} * power(10, {{ places_expr }})) / power(10, {{ places_expr }})
    {%- else -%}
    round({{ amount_expr }}, {{ places_expr }})
    {%- endif -%}
{% endmacro %}
