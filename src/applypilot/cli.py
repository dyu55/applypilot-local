"""Command-line entry point."""

import argparse
import json
import sys
import webbrowser
from pathlib import Path

from applypilot import __version__
from applypilot.storage import Workspace


def main() -> None:
    parser = argparse.ArgumentParser(description="ApplyPilot Local job search workspace")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--data-dir", help="Private data directory (defaults to your OS application data)"
    )
    parser.add_argument("--profile", default="default", help="Isolated profile identifier")
    commands = parser.add_subparsers(dest="command")
    serve = commands.add_parser("serve", help="Open the local web workspace")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--no-browser", action="store_true")
    commands.add_parser("init", help="Initialize an empty private workspace")
    commands.add_parser("demo", help="Load fictional data into an empty profile")
    commands.add_parser("doctor", help="Check the environment without contacting external services")
    commands.add_parser("collect", help="Collect jobs from your enabled public sources")
    importing = commands.add_parser("import", help="Import jobs from CSV")
    importing.add_argument("file", type=Path)
    exporting = commands.add_parser("export", help="Export tracked jobs to standard output")
    exporting.add_argument("--format", choices=["csv", "json"], default="json")
    material = commands.add_parser("materials", help="Generate verified PDF materials for one job")
    material.add_argument("job_id")
    material.add_argument("--resume-id")
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return
    try:
        workspace = Workspace(args.data_dir, args.profile)
        if args.command == "serve":
            import uvicorn

            from applypilot.web import create_app

            url = f"http://127.0.0.1:{args.port}"
            print(f"ApplyPilot Local: {url}\nPrivate profile: {workspace.profile_id}")
            if not args.no_browser:
                import threading

                timer = threading.Timer(1.2, lambda: webbrowser.open(url))
                timer.daemon = True
                timer.start()
            uvicorn.run(
                create_app(workspace), host="127.0.0.1", port=args.port, log_level="warning"
            )
            return
        if args.command == "init":
            if not (workspace.path / "profile.json").exists():
                workspace.save_profile(workspace.profile())
            result = {"initialized": True, "data_directory": str(workspace.path)}
        elif args.command == "demo":
            from applypilot.demo import seed

            result = seed(workspace)
        elif args.command == "doctor":
            from applypilot.materials import _font

            result = {
                "python": sys.version.split()[0],
                "version": __version__,
                "storage": "ok",
                "pdf_font": _font(),
                "profile": workspace.profile_id,
                "model_enabled": workspace.profile().model.enabled,
                "network_contacted": False,
            }
        elif args.command == "collect":
            from applypilot.service import collect_jobs

            result = collect_jobs(workspace)
        elif args.command == "import":
            from applypilot.service import import_jobs
            from applypilot.sources import import_csv

            result = import_jobs(workspace, import_csv(args.file.read_text(encoding="utf-8-sig")))
        elif args.command == "export":
            from applypilot.service import export

            print(export(workspace, args.format))
            return
        else:
            from applypilot.materials import generate

            result = generate(workspace, args.job_id, args.resume_id)
        print(json.dumps(result, indent=2))
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
