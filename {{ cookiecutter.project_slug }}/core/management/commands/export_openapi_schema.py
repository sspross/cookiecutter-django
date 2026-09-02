"""Export the ninja OpenAPI document as JSON, offline.

`api.get_openapi_schema()` introspects the API in-process: no running server
and no database connection (settings need `SECRET_KEY` + `DATABASE_URL`, and
the URL is parsed, never dialed). That is what lets the schema-freshness guard
run in CI against a throwaway sqlite URL.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from core.api import api


class Command(BaseCommand):
    help = "Export the ninja OpenAPI schema as JSON (offline; no running server)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "-o",
            "--output",
            default="-",
            help="Destination file path, or '-' for stdout (default).",
        )

    def handle(self, *args, **options) -> None:
        schema = api.get_openapi_schema()
        text = json.dumps(schema, indent=2)
        output = options["output"]
        if output == "-":
            self.stdout.write(text)
        else:
            Path(output).write_text(text + "\n", encoding="utf-8")
            self.stderr.write(f"Wrote OpenAPI schema to {output}")
