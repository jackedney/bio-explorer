---
name: tech-jinja2
description: Reference guide for Jinja2 — server-side HTML template rendering (bundled with Flask)
user-invocable: false
---

# Jinja2

> Purpose: Server-side HTML template rendering
> Docs: https://jinja.palletsprojects.com/en/stable/templates/
> Version researched: 3.1+ (bundled with Flask 3.1+)

## Quick Start

Jinja2 is included with Flask — no separate install needed. Place templates in the `templates/` directory alongside `app.py`. Render from a route with `render_template`.

```python
# app.py
from flask import render_template

@app.get("/")
def index():
    return render_template("index.html", title="Bio Explorer", api_base="/api")
```

```html
{# templates/index.html #}
<!DOCTYPE html>
<html>
  <head><title>{{ title }}</title></head>
  <body>{% block content %}{% endblock %}</body>
</html>
```

## Common Patterns

### Template inheritance

```html
{# templates/base.html #}
<!DOCTYPE html>
<html>
  <head>
    <title>{% block title %}Bio Explorer{% endblock %}</title>
    {% block head %}{% endblock %}
  </head>
  <body>
    {% block content %}{% endblock %}
  </body>
</html>

{# templates/index.html #}
{% extends "base.html" %}
{% block title %}Species Explorer{% endblock %}
{% block content %}
  <div id="map"></div>
{% endblock %}
```

### Variable output and escaping

```html
{# Auto-escaped in HTML templates (safe against XSS) #}
{{ species_name }}

{# Explicitly mark trusted HTML safe (avoid unless you control the value) #}
{{ html_snippet|safe }}

{# Access dict keys or object attributes uniformly #}
{{ config.api_base }}
{{ config['api_base'] }}
```

### Injecting Python values into JavaScript

Pass server-side config to the frontend via a `<script>` block:

```html
{% block scripts %}
<script>
  const CONFIG = {
    apiBase: {{ api_base | tojson }},
    maxPoints: {{ max_points | tojson }}
  };
</script>
{% endblock %}
```

`tojson` (Flask adds this filter) serialises the value as valid JSON, including proper quoting and escaping. Always use `tojson` when embedding Python values inside `<script>` tags.

### Filters

```html
{{ name | upper }}
{{ description | truncate(100) }}
{{ items | join(', ') }}
{{ value | default('N/A') }}
```

### Conditional and loop

```html
{% if user %}
  <p>Welcome, {{ user.name }}.</p>
{% else %}
  <p>Not logged in.</p>
{% endif %}

{% for result in results %}
  <li>{{ loop.index }}. {{ result.scientificName }}</li>
{% else %}
  <li>No results.</li>
{% endfor %}
```

## Gotchas & Pitfalls

- Flask enables **auto-escaping** for `.html`, `.htm`, `.xml`, and `.svg` templates. Output is HTML-escaped by default — this is the desired behaviour. Do not use `|safe` unless the value is trusted HTML you constructed yourself.
- `tojson` is a Flask-added filter (not standard Jinja2). It is the correct way to embed Python data into `<script>` tags; do not use `str()` or `json.dumps()` directly in templates.
- Undefined variables in templates raise `UndefinedError` at render time by default. Pass all required variables from the view, or use `{{ var | default('') }}` for optional ones.
- Template files are cached after first load in production. In development, set `TEMPLATES_AUTO_RELOAD = True` or use `--debug` mode to pick up changes automatically.
- Jinja2 block names must be unique within a template chain. Reusing the same block name in a child template replaces (not appends) the parent block.

## Idiomatic Usage

Keep logic out of templates — compute derived values in the Python view and pass the results:

```python
# Good — compute in view
@app.get("/")
def index():
    return render_template("index.html", tile_url=build_tile_url(), max_points=10_000)

# Avoid — business logic in template
{# {{ "https://tiles.example.com/" + zoom + "/" + x + "/" + y }} #}
```

Use `tojson` for any Python value embedded in JavaScript:

```html
{# Good #}
const MAX = {{ max_points | tojson }};

{# Avoid — broken for strings, unsafe for untrusted input #}
const MAX = {{ max_points }};
```
