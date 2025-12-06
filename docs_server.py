import http.server
import socketserver
import os
import markdown
from pathlib import Path

PORT = 5000
DOCS_DIR = Path("docs")

class DocsHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "":
            self.send_index()
        elif self.path.endswith(".md"):
            self.send_markdown()
        else:
            super().do_GET()

    def send_index(self):
        html = self.generate_index()
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(html.encode())

    def send_markdown(self):
        file_path = DOCS_DIR / self.path.lstrip("/")
        if file_path.exists():
            with open(file_path, "r") as f:
                content = f.read()
            html = self.render_markdown(content, file_path.name)
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(html.encode())
        else:
            self.send_error(404, "File not found")

    def generate_index(self):
        files = self.collect_docs()
        nav_items = []
        for category, docs in files.items():
            nav_items.append(f"<h3>{category}</h3><ul>")
            for doc in docs:
                nav_items.append(f'<li><a href="/{doc}">{doc}</a></li>')
            nav_items.append("</ul>")
        
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Trading Algorithm Document Analyzer - Documentation</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
        h1 {{ color: #333; border-bottom: 2px solid #007acc; padding-bottom: 10px; }}
        h3 {{ color: #007acc; margin-top: 20px; }}
        ul {{ list-style: none; padding-left: 0; }}
        li {{ margin: 8px 0; }}
        a {{ color: #0066cc; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .container {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Trading Algorithm Document Analyzer</h1>
        <p>Enterprise documentation for the AI-powered document analysis application.</p>
        <hr>
        {"".join(nav_items)}
    </div>
</body>
</html>"""

    def collect_docs(self):
        categories = {}
        for item in sorted(DOCS_DIR.rglob("*.md")):
            rel_path = item.relative_to(DOCS_DIR)
            category = str(rel_path.parent) if rel_path.parent != Path(".") else "Root"
            if category not in categories:
                categories[category] = []
            categories[category].append(str(rel_path))
        return categories

    def render_markdown(self, content, title):
        try:
            html_content = markdown.markdown(content, extensions=['tables', 'fenced_code'])
        except:
            html_content = f"<pre>{content}</pre>"
        
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>{title} - Documentation</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
        .container {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1, h2, h3 {{ color: #333; }}
        h1 {{ border-bottom: 2px solid #007acc; padding-bottom: 10px; }}
        a {{ color: #0066cc; }}
        pre {{ background: #f4f4f4; padding: 15px; border-radius: 4px; overflow-x: auto; }}
        code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        th {{ background: #f0f0f0; }}
        .back {{ margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="back"><a href="/">&larr; Back to Index</a></div>
        {html_content}
    </div>
</body>
</html>"""

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)) or ".")
    with socketserver.TCPServer(("0.0.0.0", PORT), DocsHandler) as httpd:
        print(f"Documentation server running at http://0.0.0.0:{PORT}")
        httpd.serve_forever()
