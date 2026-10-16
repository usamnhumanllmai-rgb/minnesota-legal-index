#!/usr/bin/env python3
import sqlite3
from flask import Flask, request, render_template_string

DB = "output/legal_index.db"
app = Flask(__name__)

PAGE = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Minnesota Legal Index Search</title>
<style>
body { font-family: system-ui, sans-serif; margin: 2rem; }
input { width: 60%; padding: .5rem; }
table { border-collapse: collapse; width: 100%; margin-top: 1rem; }
th, td { border: 1px solid #ccc; padding: .5rem; text-align: left; vertical-align: top; }
</style>
</head>
<body>
<h1>Minnesota Legal Index Search</h1>
<form method="get">
<input name="q" value="{{ q }}" placeholder="Search topic, statute, rule, or cross-reference">
<button>Search</button>
</form>

{% if results %}
<table>
<tr><th>Publication</th><th>Topic</th><th>Subtopic path</th><th>Type</th><th>Reference</th><th>Link</th></tr>
{% for row in results %}
<tr>
<td>{{ row['publication'] }}</td>
<td>{{ row['topic'] }}</td>
<td>{{ row['subtopic_path'] }}</td>
<td>{{ row['reference_type'] }}</td>
<td>{{ row['reference'] }}</td>
<td>{% if row['url'] %}<a href="{{ row['url'] }}" target="_blank">Open</a>{% else %}&mdash;{% endif %}</td>
</tr>
{% endfor %}
</table>
{% endif %}
</body>
</html>
"""


@app.route("/")
def search():
    query = request.args.get("q", "").strip()
    results = []

    if query:
        connection = sqlite3.connect(DB)
        connection.row_factory = sqlite3.Row
        results = connection.execute(
            """
            SELECT publication, topic, subtopic_path, reference_type,
                   reference, url
            FROM entries
            WHERE entries MATCH ?
            ORDER BY rank
            LIMIT 100
            """,
            (query,),
        ).fetchall()
        connection.close()

    return render_template_string(PAGE, q=query, results=results)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
