.PHONY: test validate generate blender-command smoke-render render

PYTHONPATH := src
SHOT ?= examples/shots/cyberpunk_orbit.json
SMOKE_SHOT := examples/shots/smoke_test.json
PROMPT ?= calle cyberpunk nocturna con lluvia y cámara orbitando al personaje

test:
	PYTHONPATH=$(PYTHONPATH) python3 -m unittest discover -s tests

validate:
	PYTHONPATH=$(PYTHONPATH) python3 -m ai_blender_director.cli validate $(SHOT)

generate:
	PYTHONPATH=$(PYTHONPATH) python3 -m ai_blender_director.cli generate "$(PROMPT)"

blender-command:
	PYTHONPATH=$(PYTHONPATH) python3 -m ai_blender_director.cli blender-command $(SHOT) --output renders/previews

render:
	blender --background --python scripts/blender/render_shot.py -- $(SHOT) renders/previews

smoke-render:
	blender --background --python scripts/blender/render_shot.py -- $(SMOKE_SHOT) renders/previews
