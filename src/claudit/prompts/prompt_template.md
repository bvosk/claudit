# System Prompt
{% if system %}
{% for prompt in system %}
{% if prompt.type == 'text' %}
```
{{ prompt.text }}
```
{% endif %}
{% endfor -%}
{% else %}
No system prompts captured.
{% endif %}

# Tools

{% if tools %}
{% for tool in tools %}
## {{ tool.name }}

**Description:**

```
{{ tool.description }}
```

**Schema:**
```json
{{ tool.input_schema | tojson(indent=2) }}
```

{% endfor %}
{% else %}
No tools available.
{% endif %}
