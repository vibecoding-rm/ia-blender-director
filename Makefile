.PHONY: test validate blender-command smoke-render

PYTHONPATH := src
SHOT ?= examples/shots/cyberpunk_orbit.json
SMOKE_SHOT := examples/shots/smoke_test.json

test:
	PYTHONPATH=$(PYTHONPATH) python3 -m unittest discover -s tests

validate:
	PYTHONPATH=$(PYTHONPATH) python3 -m ai_blender_director.cli validate $(SHOT)

blender-command:
	PYTHONPATH=$(PYTHONPATH) python3 -m ai_blender_director.cli blender-command $(SHOT) --output renders/previews

smoke-render:
	blender --background --python scripts/blender/render_shot.py -- $(SMOKE_SHOT) renders/previews
