{# Stripe sends Unix seconds in UTC. Return a UTC timestamp without a timezone. #}
{% macro unix_to_utc(seconds_text) %}
    (to_timestamp(cast({{ seconds_text }} as bigint)) at time zone 'UTC')
{% endmacro %}
