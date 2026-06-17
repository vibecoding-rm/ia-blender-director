import sys
from pathlib import Path

scripts_blender_dir = Path(__file__).resolve().parent
if str(scripts_blender_dir) not in sys.path:
    sys.path.insert(0, str(scripts_blender_dir))

from ai_director.render import main

if __name__ == "__main__":
    raise SystemExit(main())
