#!/usr/bin/env bash
# Renderiza un episodio del Noticiero de La Cotorra en MÁXIMA CALIDAD.
# Pensado para correr DENTRO de la instancia GPU ya provisionada
# (ver scripts/provision_gpu.sh). Vertical 9:16, EEVEE GPU, sin ComfyUI.
#
# Uso (desde la raíz del repo en la instancia):
#   bash scripts/render_noticiero.sh
#
# Personaliza la noticia con variables de entorno:
#   PROMPT='La Cotorra reporta apagones en La Habana' \
#   HOOK='APAGÓN TOTAL' \
#   NARRATION='Buenas noches, otra vez sin luz...' \
#   bash scripts/render_noticiero.sh
#
# Otras palancas: SHOTS, DURATION, VOICE, VOICE_CHARACTER, OUT
set -euo pipefail

PROMPT="${PROMPT:-La Cotorra presenta una noticia urgente del régimen}"
HOOK="${HOOK:-ULTIMA HORA}"
NARRATION="${NARRATION:-Buenas noches, soy La Cotorra, y esto es lo que no quieren que sepas.}"
SHOTS="${SHOTS:-4}"
DURATION="${DURATION:-4}"
VOICE_CHARACTER="${VOICE_CHARACTER:-cotorra_v1}"
VOICE="${VOICE:-assets/voices/es_MX-claude-high.onnx}"
OUT="${OUT:-renders/noticiero_final_vertical.mp4}"

# Corre desde la raíz del repo, sin importar desde dónde se invoque.
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"

if [[ ! -f "${VOICE}" ]]; then
  echo "⚠ No existe la voz ${VOICE}. ¿Corriste scripts/provision_gpu.sh?" >&2
  echo "  El render seguirá con la voz piper por defecto si está disponible." >&2
fi

echo "==> Renderizando noticiero (perfil final, vertical)"
echo "    Prompt : ${PROMPT}"
echo "    Hook   : ${HOOK}"
echo "    Planos : ${SHOTS} x ${DURATION}s"
echo "    Salida : ${OUT}"
echo ""

PYTHONPATH=src python3 -m ai_blender_director.cli auto-director \
  "${PROMPT}" \
  --shots "${SHOTS}" --duration "${DURATION}" \
  --vertical --profile final --no-comfy \
  --hook "${HOOK}" \
  --narration "${NARRATION}" \
  --voice-character "${VOICE_CHARACTER}" \
  --voice "${VOICE}" \
  --output-video "${OUT}"

echo ""
echo "✓ Render listo: ${OUT}"
echo "  Bájalo a tu PC:  scp -P <PORT> root@<HOST>:$(basename "${REPO_DIR}")/${OUT} ."
echo "⚠ Al terminar, destruye la instancia:  bash scripts/destroy_gpu.sh <ID>"
