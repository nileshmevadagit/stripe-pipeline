-- Guard for the public dashboard. Fails (returns rows) if any model tagged 'public' has a
-- personal column in the warehouse. It checks the real table columns, so an untagged new
-- column is caught too. Personal names come from pii tags in the YAML plus a fixed list.
{% set public_models = [] %}
{% set pii_columns = [
    'email', 'name', 'phone', 'address_line1', 'address_line2', 'postal_code',
    'customer_id', 'customer_key', 'last4', 'fingerprint', 'description', 'metadata'
] %}
{% for node in graph.nodes.values() %}
  {% if node.resource_type == 'model' and 'public' in node.tags %}
    {% do public_models.append(node.name) %}
  {% endif %}
  {% for column_name, column in node.columns.items() %}
    {% if column.meta.get('pii') and column_name not in pii_columns %}
      {% do pii_columns.append(column_name) %}
    {% endif %}
  {% endfor %}
{% endfor %}

select table_name, column_name
from information_schema.columns
where table_schema = 'main'
  and table_name in ({% for m in public_models %}'{{ m }}'{% if not loop.last %}, {% endif %}{% endfor %})
  and lower(column_name) in ({% for c in pii_columns %}'{{ c }}'{% if not loop.last %}, {% endif %}{% endfor %})
