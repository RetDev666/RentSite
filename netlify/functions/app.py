from __future__ import annotations

import sys
from pathlib import Path

# Add project root directory to sys.path so saunacore is importable
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import serverless_wsgi
from saunacore import create_app

app = create_app()


def handler(event, context):
    return serverless_wsgi.handle_request(app, event, context)
