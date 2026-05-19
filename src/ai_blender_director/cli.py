from __future__ import annotations

import argparse
import sys

from .commands import generation, management, pipeline, post_processing, render
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

    args = parser.parse_args(argv)

    try:
        # Generation
        if args.command == "validate":
            return generation.handle_validate(args)
        if args.command == "generate":
            return generation.handle_generate(args)
        if args.command == "create":
            return generation.handle_create(args)
            
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
            
        # Post Processing
        if args.command == "comfy-render":
            return post_processing.handle_comfy_render(args)
        if args.command == "critic":
            return post_processing.handle_critic(args)
            
        # Pipeline
        if args.command == "auto-director":
            return pipeline.handle_auto_director(args)
            
    except AssetValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except ShotValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
