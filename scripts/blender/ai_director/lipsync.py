"""Aplica lip-sync por audio dentro de Blender.

Recibe una pista de apertura de boca (frame → radianes) generada desde los
visemas de Rhubarb y la aplica al hueso `Beak` de La Cotorra. Para personajes
con shape keys de visemas (boca de malla) hay un fallback que los conduce.

El módulo es tolerante: si no encuentra ni hueso `Beak` ni shape keys, no hace
nada y deja la animación embebida (acción Talk) intacta.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import bpy

JAW_BONE_CANDIDATES = ("Beak", "Jaw", "jaw", "MouthOpen")

# Visemas de Rhubarb → apertura de boca 0..1 (idéntico a lipsync.py del host).
VISEME_OPENNESS = {
    "X": 0.0, "A": 0.05, "B": 0.22, "C": 0.45, "D": 0.85,
    "E": 0.50, "F": 0.30, "G": 0.28, "H": 0.62,
}
MAX_OPEN_RAD = math.radians(45)  # apertura máxima del pico (coincide con la acción Talk)


def load_jaw_track_from_json(
    json_path: str, fps: int, *, start_offset: float = 0.0, max_open_rad: float = MAX_OPEN_RAD
) -> list[tuple[int, float]]:
    """Lee un JSON de Rhubarb y construye la pista (frame, radianes) del pico."""
    path = Path(json_path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        cues = json.load(f).get("mouthCues", [])
    track: list[tuple[int, float]] = []
    for cue in cues:
        try:
            start = float(cue["start"]) - start_offset
            value = str(cue["value"]).upper()
        except (KeyError, ValueError, TypeError):
            continue
        if start < 0:
            continue
        frame = max(1, round(start * fps) + 1)
        track.append((frame, VISEME_OPENNESS.get(value, 0.0) * max_open_rad))
    return track


def find_armature(subject: bpy.types.Object) -> bpy.types.Object | None:
    if subject is None:
        return None
    if subject.type == "ARMATURE":
        return subject
    for child in subject.children_recursive:
        if child.type == "ARMATURE":
            return child
    return None


def apply_jaw_track(
    subject: bpy.types.Object, jaw_track: list[tuple[int, float]], *, frame_end: int
) -> bool:
    """Keyframea la apertura del pico/mandíbula. Devuelve True si aplicó algo."""
    if not jaw_track:
        return False
    armature = find_armature(subject)
    if armature is None:
        return False

    bone_name = next((b for b in JAW_BONE_CANDIDATES if b in armature.pose.bones), None)
    if bone_name is None:
        return _apply_shapekey_track(subject, jaw_track, frame_end=frame_end)

    pose_bone = armature.pose.bones[bone_name]
    pose_bone.rotation_mode = "XYZ"
    if armature.animation_data is None:
        armature.animation_data_create()
    action = armature.animation_data.action
    if action is None:
        action = bpy.data.actions.new(name="Lipsync")
        armature.animation_data.action = action

    data_path = f'pose.bones["{bone_name}"].rotation_euler'
    # Quita keyframes previos del beak (de la acción Talk) en este eje.
    for fc in [fc for fc in action.fcurves if fc.data_path == data_path and fc.array_index == 0]:
        action.fcurves.remove(fc)
    fcurve = action.fcurves.new(data_path=data_path, index=0)

    keys = [(1, 0.0)] + [(f, v) for f, v in jaw_track if 1 <= f <= frame_end]
    fcurve.keyframe_points.add(len(keys))
    for i, (frame, value) in enumerate(keys):
        fcurve.keyframe_points[i].co = (frame, value)
        fcurve.keyframe_points[i].interpolation = "BEZIER"
    fcurve.update()
    print(f"  lip-sync: {len(keys)} keyframes en '{bone_name}'.")
    return True


def _apply_shapekey_track(
    subject: bpy.types.Object, jaw_track: list[tuple[int, float]], *, frame_end: int
) -> bool:
    """Fallback: conduce un shape key 'mouth_open' por la apertura de boca."""
    meshes = [o for o in ([subject] + list(subject.children_recursive)) if o.type == "MESH"]
    applied = False
    for mesh in meshes:
        keys = mesh.data.shape_keys
        if not keys:
            continue
        target = next(
            (kb for kb in keys.key_blocks if kb.name.lower() in ("mouth_open", "open", "aa", "jaw")),
            None,
        )
        if target is None:
            continue
        max_v = max((v for _, v in jaw_track), default=0.0) or 1.0
        for frame, value in jaw_track:
            if 1 <= frame <= frame_end:
                target.value = max(0.0, min(1.0, value / max_v))
                target.keyframe_insert("value", frame=frame)
        applied = True
    return applied
