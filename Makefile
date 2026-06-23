.PHONY: test validate validate-assets generate create jobs show blender-command smoke-render render

PYTHONPATH := src
SHOT ?= examples/shots/cyberpunk_orbit.json
SMOKE_SHOT := examples/shots/smoke_test.json
PROMPT ?= calle cyberpunk nocturna con lluvia y cámara orbitando al personaje
PROFILE ?= preview
JOB ?=

test:
	PYTHONPATH=$(PYTHONPATH) python3 -m unittest discover -s tests

validate:
	PYTHONPATH=$(PYTHONPATH) python3 -m ai_blender_director.cli validate $(SHOT)

validate-assets:
	PYTHONPATH=$(PYTHONPATH) python3 -m ai_blender_director.cli validate-assets

generate:
	PYTHONPATH=$(PYTHONPATH) python3 -m ai_blender_director.cli generate "$(PROMPT)"

create:
	PYTHONPATH=$(PYTHONPATH) python3 -m ai_blender_director.cli create "$(PROMPT)" --render --profile $(PROFILE)

jobs:
	PYTHONPATH=$(PYTHONPATH) python3 -m ai_blender_director.cli jobs

show:
	PYTHONPATH=$(PYTHONPATH) python3 -m ai_blender_director.cli show $(JOB)

blender-command:
	PYTHONPATH=$(PYTHONPATH) python3 -m ai_blender_director.cli blender-command $(SHOT) --output renders/previews

render:
	PYTHONPATH=$(PYTHONPATH) python3 -m ai_blender_director.cli render $(SHOT) --profile $(PROFILE)

smoke-render:
	PYTHONPATH=$(PYTHONPATH) python3 -m ai_blender_director.cli render $(SMOKE_SHOT) --profile preview
