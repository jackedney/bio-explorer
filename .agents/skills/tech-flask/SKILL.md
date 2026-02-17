---
name: tech-flask
description: Reference guide for Flask — web framework, template rendering, static file serving
user-invocable: false
---

# Flask

> Purpose: Web framework, template rendering, static file serving
> Docs: https://flask.palletsprojects.com/en/stable/
> Version researched: 3.1+

## Quick Start

```python
from flask import Flask, request, jsonify, render_template, abort

app = Flask(__name__)

if __name__ == "__main__":
    app.run(debug=True)
```

Run with `python app.py` or `flask --app app run --debug`.

## Common Patterns

### Route with query parameter and JSON response

```python
@app.get("/api/items")
def list_items():
    q = request.args.get("q", "")
    if not q:
        abort(400)
    results = fetch_items(q)
    return jsonify({"results": results})
```

### Returning a dict directly (auto-serialised to JSON since Flask 2.2+)

```python
@app.get("/api/status")
def status():
    return {"ok": True, "version": "1.0"}
```

### Rendering a Jinja2 template

```python
@app.get("/")
def index():
    return render_template("index.html", title="Bio Explorer")
```

Templates live in `templates/` relative to the app package.

### Custom error handlers

```python
@app.errorhandler(400)
def bad_request(e):
    return jsonify({"error": str(e)}), 400

@app.errorhandler(502)
def bad_gateway(e):
    return jsonify({"error": "upstream service unavailable"}), 502
```

### Aborting with a specific status

```python
from flask import abort

abort(400)          # raises 400 immediately
abort(502, "GBIF unreachable")
```

## Gotchas & Pitfalls

- `request.args.get("key")` returns `None` if missing; use `.get("key", default)` or check and `abort(400)`.
- Returning a plain `dict` or `list` from a view auto-calls `jsonify`. Do NOT wrap in `jsonify(dict(...))` — that double-encodes.
- `app.run()` is single-threaded by default. Add `threaded=True` if concurrent requests are expected (fine for a demo; use a real server in production).
- Flask's built-in static serving (`/static/<path:filename>`) works out of the box. Do not configure a separate static route unless you need custom logic.
- Debug mode (`debug=True`) must NEVER be used in production — it exposes an interactive debugger with remote code execution.
- `abort()` raises an exception; code after it does not run.

## Idiomatic Usage

Prefer `@app.get` / `@app.post` over `@app.route(..., methods=[...])` for readability:

```python
# Good
@app.get("/api/species/search")
def species_search():
    ...

# Avoid
@app.route("/api/species/search", methods=["GET"])
def species_search():
    ...
```

Return dicts directly rather than calling `jsonify` explicitly:

```python
# Good
return {"points": coords, "total": total, "returned": len(coords)}

# Avoid (redundant wrapping)
return jsonify({"points": coords, "total": total, "returned": len(coords)})
```

Keep views thin — move GBIF API calls and business logic into separate functions or modules; views should only handle HTTP concerns (parse input, call service, return response).
