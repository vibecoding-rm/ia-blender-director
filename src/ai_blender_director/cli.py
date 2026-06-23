from __future__ import annotations

import argparse
import sys

from .commands import batch, generation, management, pipeline, post_processing, render
from .assets import AssetValidationError
from .models import ShotValidationError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ai-blender-director")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generation.register_parsers(subparsers)
    render.register_parsers(subparsers)
    management.register_parsers(subparsers)
    post_processing.register_parsers(subparsers)
    pipeline.register_parsers(subparsers)
    batch.register_parsers(subparsers)

    serve_parser = subparsers.add_parser("serve", help="Start the FastAPI web server.")
    serve_parser.add_argument("--host", default=None, help="Override server host from config.")
    serve_parser.add_argument("--port", type=int, default=None, help="Override server port from config.")

    args = parser.parse_args(argv)

    try:
        # Generation
        if args.command == "validate":
            return generation.handle_validate(args)
        if args.command == "generate":
            return generation.handle_generate(args)
        if args.command == "create":
            return generation.handle_create(args)
        if args.command == "plan":
            return generation.handle_plan(args)

        # Render
        if args.command == "blender-command":
            return render.handle_blender_command(args)
        if args.command == "render":
            return render.handle_render(args)

        # Management
        if args.command == "jobs":
            return management.handle_jobs(args)
        if args.command == "show":
            return management.handle_show(args)
        if args.command == "assets":
            return management.handle_assets(args)
        if args.command == "validate-assets":
            return management.handle_validate_assets(args)
        if args.command == "preflight":
            return management.handle_preflight(args)

        # Post Processing
        if args.command == "comfy-render":
            return post_processing.handle_comfy_render(args)
        if args.command == "critic":
            return post_processing.handle_critic(args)

        # Pipeline
        if args.command == "auto-director":
            return pipeline.handle_auto_director(args)
        if args.command == "batch":
            return batch.handle_batch(args)

        # Server
        if args.command == "serve":
            return _handle_serve(args)

    except AssetValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except ShotValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    parser.error(f"Unknown command: {args.command}")
    return 2


def _handle_serve(args: argparse.Namespace) -> int:
    import uvicorn
    from .server import app
    from .config import settings

    host = args.host or settings.server_host
    port = args.port or settings.server_port
    print(f"Starting AI Blender Director server at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
