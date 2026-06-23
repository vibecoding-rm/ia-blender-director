"""Cola de producción por lotes: renderiza varios episodios en secuencia.

Pensado para correr de madrugada: un archivo JSONL define la semana de
episodios y `batch` los produce uno a uno (esta máquina solo aguanta un
Blender a la vez). Es reanudable: los episodios cuyo video final ya existe
se saltan, así que si el lote se interrumpe basta relanzarlo.

Formato del archivo (una línea JSON por episodio):

    {"id": "ep001", "prompt": "la cotorra presenta...", "hook": "TITULAR",
     "narration": "guion...", "shots": 6, "duration": 3, "fps": 12,
     "vertical": true, "voice_character": "cotorra_v1"}

Campos obligatorios: id, prompt. El resto tiene defaults de episodio Short.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = ("id", "prompt")
DEFAULTS: dict[str, Any] = {
    "shots": 6,
    "duration": 3,
    "fps": 12,
    "vertical": True,
    "hook": None,
    "narration": None,
    "voice": None,
    "voice_character": None,
}


def register_parsers(subparsers: argparse._SubParsersAction) -> None:
    batch_parser = subparsers.add_parser(
        "batch",
        help="Produce en secuencia todos los episodios de un archivo JSONL (cola nocturna).",
    )
    batch_parser.add_argument("episodes", type=Path, help="Archivo .jsonl con un episodio por línea.")
    batch_parser.add_argument("--output-dir", type=Path, default=Path("renders/episodios"))
    batch_parser.add_argument("--shot-output-dir", type=Path, default=Path("generated/shots"))
    batch_parser.add_argument("--output-root", type=Path, default=Path("renders/previews"))
    batch_parser.add_argument("--index", type=Path, default=Path("renders/index.jsonl"))
    batch_parser.add_argument("--dry-run", action="store_true",
                              help="Validar y listar los episodios sin renderizar.")
    batch_parser.add_argument("--force", action="store_true",
                              help="Re-renderizar aunque el video final ya exista.")


def load_episodes(path: Path) -> list[dict[str, Any]]:
    """Lee y valida el JSONL. Lanza ValueError con la línea problemática."""
    episodes: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"línea {line_number}: JSON inválido ({exc})") from exc
        for field in REQUIRED_FIELDS:
            if not data.get(field):
                raise ValueError(f"línea {line_number}: falta el campo obligatorio '{field}'")
        if data["id"] in seen_ids:
            raise ValueError(f"línea {line_number}: id duplicado '{data['id']}'")
        seen_ids.add(data["id"])
        episodes.append({**DEFAULTS, **data})
    return episodes


def handle_batch(args: argparse.Namespace) -> int:
    if not args.episodes.exists():
        print(f"error: no existe {args.episodes}", file=sys.stderr)
        return 2
    try:
        episodes = load_episodes(args.episodes)
    except ValueError as exc:
        print(f"error en {args.episodes}: {exc}", file=sys.stderr)
        return 2
    if not episodes:
        print("error: el archivo no contiene episodios", file=sys.stderr)
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    print(f"batch: {len(episodes)} episodio(s) en cola\n")

    results: list[tuple[str, str, float]] = []
    for i, episode in enumerate(episodes, start=1):
        output_video = args.output_dir / f"{episode['id']}.mp4"
        print(f"=== EPISODIO {i}/{len(episodes)}: {episode['id']} ===")
        print(f"  prompt: {episode['prompt']}")
        if episode.get("hook"):
            print(f"  hook:   {episode['hook']}")

        if output_video.exists() and not args.force:
            print(f"  ya existe {output_video} — saltando (usa --force para repetir)\n")
            results.append((episode["id"], "saltado", 0.0))
            continue
        if args.dry_run:
            print(f"  [dry-run] produciría: {output_video}\n")
            results.append((episode["id"], "dry-run", 0.0))
            continue

        started = time.monotonic()
        code = _produce_episode(episode, output_video, args)
        elapsed = time.monotonic() - started
        status = "ok" if code == 0 else f"FALLO (código {code})"
        results.append((episode["id"], status, elapsed))
        print(f"  resultado: {status} en {elapsed/60:.1f} min\n")

    print("=== RESUMEN DEL LOTE ===")
    failures = 0
    for episode_id, status, elapsed in results:
        marker = "✗" if status.startswith("FALLO") else "✓"
        failures += status.startswith("FALLO")
        timing = f"  ({elapsed/60:.1f} min)" if elapsed else ""
        print(f"  {marker} {episode_id}: {status}{timing}")
    return 1 if failures else 0


def _produce_episode(episode: dict[str, Any], output_video: Path, args: argparse.Namespace) -> int:
    """Ejecuta el pipeline multi-shot completo para un episodio."""
    from .pipeline import _handle_multi_shot

    episode_args = argparse.Namespace(
        prompt=episode["prompt"],
        shots=int(episode["shots"]),
        duration=int(episode["duration"]),
        fps=int(episode["fps"]),
        vertical=bool(episode["vertical"]),
        hook=episode.get("hook"),
        narration=episode.get("narration"),
        voice=Path(episode["voice"]) if episode.get("voice") else None,
        voice_character=episode.get("voice_character"),
        output_video=output_video,
        shot_output_dir=args.shot_output_dir,
        output_root=args.output_root,
        index=args.index,
        workflow="stylization_v1",
        comfy_url=None,
        no_comfy=True,
        no_subtitles=bool(episode.get("no_subtitles", False)),
        no_sfx=bool(episode.get("no_sfx", False)),
    )
    try:
        return _handle_multi_shot(episode_args)
    except Exception as exc:  # noqa: BLE001 — un episodio roto no debe matar el lote
        print(f"  error inesperado: {exc}", file=sys.stderr)
        return 1
