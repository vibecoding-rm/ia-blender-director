import sys
sys.path.insert(0, "src")

from ai_blender_director.planner import plan_scene, write_shot_plan
from pathlib import Path

prompt = "calle cyberpunk con lluvia y personaje misterioso"
print("Planificando escena...")
scene = plan_scene(prompt, n_shots=3)
print("Titulo:", scene["title"])
print("Narracion:", scene.get("narration_text", "N/A"))
for i, shot in enumerate(scene["shots"], 1):
    cam = shot["camera"]["movement"]
    trans = shot["transition"]["type"]
    print(f"  Plano {i}: {shot['scene']} | cam={cam} | lens={shot['camera']['lens_mm']}mm | trans={trans}")

# Write the shots to disk
out_dir = Path("generated/shots/test_cyberpunk")
paths = write_shot_plan(prompt, out_dir, n_shots=3, precomputed_shots=scene["shots"])
print("\nPlanos guardados en:")
for p in paths:
    print(" ", p.name)
