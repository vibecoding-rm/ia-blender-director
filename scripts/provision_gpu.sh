#!/usr/bin/env bash
# Aprovisiona una caja Linux con GPU (p.ej. Vast.ai) para renderizar el
# noticiero en MÁXIMA CALIDAD con Blender EEVEE acelerado por GPU.
#
# Uso (en la instancia, como root o con sudo):
#   bash scripts/provision_gpu.sh
#
# Después crea tu .env (con OPENROUTER_API_KEY etc.) y corre:
#   PYTHONPATH=src python3 -m ai_blender_director.cli auto-director \
#     "La Cotorra presenta una noticia urgente del régimen" \
#     --shots 4 --duration 4 --vertical --profile final --no-comfy \
#     --hook "ULTIMA HORA" --narration "Buenas noches, soy La Cotorra..."
#
# IMPORTANTE: destruye la instancia al terminar para no pagar almacenamiento.
set -euo pipefail

BLENDER_VER="4.2.3"
RHUBARB_VER="1.14.0"
OPT="/opt"

echo "==> [1/6] Paquetes del sistema"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
  wget curl xz-utils unzip git ffmpeg python3 python3-pip python3-venv \
  libxi6 libxxf86vm1 libxfixes3 libxrender1 libgl1 libegl1 libsm6 \
  libxkbcommon0 libgomp1 >/dev/null

echo "==> [2/6] Blender ${BLENDER_VER} LTS"
if [ ! -x "${OPT}/blender/blender" ]; then
  cd /tmp
  wget -q "https://download.blender.org/release/Blender4.2/blender-${BLENDER_VER}-linux-x64.tar.xz"
  tar -xf "blender-${BLENDER_VER}-linux-x64.tar.xz"
  rm -rf "${OPT}/blender" && mv "blender-${BLENDER_VER}-linux-x64" "${OPT}/blender"
fi
ln -sf "${OPT}/blender/blender" /usr/local/bin/blender

echo "==> [3/6] Rhubarb ${RHUBARB_VER} (lip-sync)"
if [ ! -x "${OPT}/rhubarb/rhubarb" ]; then
  cd /tmp
  wget -q "https://github.com/DanielSWolf/rhubarb-lip-sync/releases/download/v${RHUBARB_VER}/Rhubarb-Lip-Sync-${RHUBARB_VER}-Linux.zip"
  unzip -q "Rhubarb-Lip-Sync-${RHUBARB_VER}-Linux.zip"
  rm -rf "${OPT}/rhubarb" && mv "Rhubarb-Lip-Sync-${RHUBARB_VER}-Linux" "${OPT}/rhubarb"
fi
ln -sf "${OPT}/rhubarb/rhubarb" /usr/local/bin/rhubarb

echo "==> [4/6] Paquete Python + Director Agent"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"
pip3 install -q -e ".[director]"
pip3 install -q piper-tts

echo "==> [5/6] Voz piper en español"
mkdir -p assets/voices
VOICE="assets/voices/es_MX-claude-high.onnx"
if [ ! -f "${VOICE}" ]; then
  base="https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX/ald/medium"
  curl -sL "${base}/es_MX-ald-medium.onnx"      -o "${VOICE}"
  curl -sL "${base}/es_MX-ald-medium.onnx.json" -o "${VOICE}.json"
fi

echo "==> [6/6] .env (rellena tus claves)"
if [ ! -f .env ]; then
  cp .env.example .env
  echo "BLENDER_EXECUTABLE=/usr/local/bin/blender" >> .env
  echo ">> Edita .env y pon OPENROUTER_API_KEY (y VAST_API_KEY si lo necesitas)."
fi

echo ""
echo "✓ Listo. Verifica: blender --version ; rhubarb --version ; ffmpeg -version | head -1"
echo "✓ Render máx. calidad: añade --profile final --vertical al comando auto-director."
echo "⚠ Destruye la instancia al terminar (evita cargos de almacenamiento)."
