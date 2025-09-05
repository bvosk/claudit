# Claude Code Prompt Log

**Timestamp:** {{ timestamp }}
**Model:** {{ model }}
{% if duration %}**Duration:** {{ duration }} ms{% endif %}

## System Prompt

{% for prompt in system %}
{% if prompt.type == 'text' %}
{{ prompt.text }}

---

{% endif %}
{% endfor %}

## Tools

{% if tools %}
{% for tool in tools %}
### {{ tool.name }}

**Description:**
{{ tool.description }}

**Schema:**
```json
{{ tool.input_schema | tojson(indent=2) }}
```

---

{% endfor %}
{% else %}
No tools available.
{% endif %}

## User Messages

{% if messages %}
{% for message in messages %}
### {{ message.role | title }}

{% for content in message.content %}
{% if content.type == 'text' %}
{{ content.text }}
{% endif %}
{% endfor %}

---

{% endfor %}
{% else %}
No user messages.
{% endif %}

## Response Information

{% if response %}
**Status Code:** {{ response.status_code }}
**Content Type:** {{ response.headers.get('Content-Type', 'N/A') }}
**Rate Limits:**
- Input Tokens Remaining: {{ response.headers.get('anthropic-ratelimit-input-tokens-remaining', 'N/A') }}
- Output Tokens Remaining: {{ response.headers.get('anthropic-ratelimit-output-tokens-remaining', 'N/A') }}
- Requests Remaining: {{ response.headers.get('anthropic-ratelimit-requests-remaining', 'N/A') }}
{% endif %}
