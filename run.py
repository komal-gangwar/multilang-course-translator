"""
============================================================
  Application Entry Point
  File: run.py
============================================================
"""

import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")
    port = int(os.getenv("PORT", 5000))
    print(f"""
╔══════════════════════════════════════════════════════════╗
║   Multi-language Course Content Translator Agent         ║
║   IBM Watsonx.ai + Granite | Flask + RAG                 ║
║                                                          ║
║   Running at: http://localhost:{port:<28}║
╚══════════════════════════════════════════════════════════╝
    """)
    app.run(host="0.0.0.0", port=port, debug=debug)
