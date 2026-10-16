{# Stripe sends Unix seconds in UTC. Return a UTC timestamp without a timezone. #}
{# Databricks: timestamp_seconds gives an instant; the session time zone must be UTC for the cast below. #}
{% macro unix_to_utc(seconds_text) %}
    {%- if target.type == 'databricks' -%}
    cast(timestamp_seconds(cast({{ seconds_text }} as bigint)) as timestamp_ntz)
    {%- else -%}
    (to_timestamp(cast({{ seconds_text }} as bigint)) at time zone 'UTC')
    {%- endif -%}
{% endmacro %}
