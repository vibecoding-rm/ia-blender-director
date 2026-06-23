#!/usr/bin/env bash
# Monta ComfyUI para la estilización AI (workflow stylization_v1: SD1.5 img2img
# + ControlNet depth) en una instancia GPU de Vast.ai con imagen base
# vastai/base-image (Python 3.12 en /venv/main).
#
# Resuelve las trampas encontradas en producción:
#  - La red de algunos hosts corta descargas grandes: bajamos los wheels de
#    torch/CUDA y los modelos con `wget -c` (reanuda) y luego instalamos OFFLINE.
#  - ComfyUI master importa torchaudio (modelos de audio que NO usamos) y su
#    extensión nativa pide libcudart.so.13 (CUDA 13) incompatible con torch
#    cu124 -> lo reemplazamos por un stub importable.
#  - comfy-kitchen (acelerador fp8/fp4) exige cu130 -> lo desinstalamos.
#
# Uso (en la instancia, dentro del repo):  bash scripts/setup_comfy_gpu.sh
set -uo pipefail

PY=/venv/main/bin/python
[ -x "$PY" ] || PY=python3
TORCH_VER="2.6.0"
TV_VER="0.21.0"
CUDA="cu124"
W=/tmp/wheels
SP="$($PY -c 'import site,sys; print(site.getsitepackages()[0])')"

dl() {  # dl <url> <destino>  — wget con reanudación, reintentos infinitos hasta completar
  local url="$1" dest="$2"
  for t in $(seq 1 40); do
    wget -c -q --timeout=60 --tries=5 --waitretry=5 -O "$dest" "$url" && return 0
    echo "   reintento $t: $(basename "$dest")"
  done
  return 1
}

echo "==> [1/6] ComfyUI"
cd ~
[ -d ComfyUI ] || git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git
cd ~/ComfyUI
mkdir -p "$W" models/checkpoints models/controlnet

echo "==> [2/6] torch ${TORCH_VER}+${CUDA} (wheel con resume + deps offline)"
B="https://download.pytorch.org/whl/${CUDA}"
dl "$B/torch-${TORCH_VER}%2B${CUDA}-cp312-cp312-linux_x86_64.whl"        "$W/torch-${TORCH_VER}+${CUDA}-cp312-cp312-linux_x86_64.whl"
dl "$B/torchvision-${TV_VER}%2B${CUDA}-cp312-cp312-linux_x86_64.whl"     "$W/torchvision-${TV_VER}+${CUDA}-cp312-cp312-linux_x86_64.whl"
T="$W/torch-${TORCH_VER}+${CUDA}-cp312-cp312-linux_x86_64.whl"
TV="$W/torchvision-${TV_VER}+${CUDA}-cp312-cp312-linux_x86_64.whl"
# Resuelve las URLs de dependencias (nvidia-*, triton, etc.) y bájalas con resume.
$PY -m pip install --dry-run --report /tmp/rep.json "$T" "$TV" >/dev/null 2>&1
$PY -c "import json;d=json.load(open('/tmp/rep.json'));[print(p['download_info']['url']) for p in d['install'] if p['download_info']['url'].startswith('http')]" > /tmp/urls.txt
while read -r u; do [ -z "$u" ] && continue; dl "$u" "$W/$(basename "$u")"; done < /tmp/urls.txt
$PY -m pip install --no-index --find-links "$W" "$T" "$TV"
$PY -c 'import torch;assert torch.cuda.is_available();print(">>> torch",torch.__version__,"cuda OK")'

echo "==> [3/6] requirements ComfyUI + saneamiento"
for i in $(seq 1 8); do $PY -m pip install --retries 10 --timeout 300 -r requirements.txt && break; echo "  req reintento $i"; done
# comfy-kitchen exige cu130: fuera.
$PY -m pip uninstall -y comfy-kitchen >/dev/null 2>&1 || true
# torchaudio: stub importable (su extensión nativa pide libcudart.so.13).
$PY -m pip uninstall -y torchaudio >/dev/null 2>&1 || true
rm -rf "$SP/torchaudio" "$SP"/torchaudio-*.dist-info "$SP/torchaudio.py"
cat > "$SP/torchaudio.py" <<'PYEOF'
class _Missing:
    def __getattr__(self, n):
        raise RuntimeError('torchaudio stub: audio no soportado en este entorno')
functional = _Missing(); transforms = _Missing(); __version__ = '0.0.0-stub'
PYEOF
$PY -c 'import torchaudio; assert torchaudio.__version__=="0.0.0-stub"; print(">>> torchaudio stub OK")'

echo "==> [4/6] modelos del workflow (resume)"
dl 'https://huggingface.co/Lykon/DreamShaper/resolve/main/DreamShaper_8_pruned.safetensors' models/checkpoints/dreamshaper_8.safetensors
dl 'https://huggingface.co/lllyasviel/ControlNet-v1-1/resolve/main/control_v11f1p_sd15_depth.pth' models/controlnet/control_v11f1p_sd15_depth.pth
ls -lah models/checkpoints/dreamshaper_8.safetensors models/controlnet/control_v11f1p_sd15_depth.pth

echo "==> [5/6] arranco servidor ComfyUI (persistente con setsid)"
pkill -9 -f 'ComfyUI/main.py' 2>/dev/null || true; sleep 2
setsid bash -c "$PY main.py --listen 127.0.0.1 --port 8188 > /root/comfy.log 2>&1" < /dev/null > /dev/null 2>&1 &

echo "==> [6/6] espero a que responda en 127.0.0.1:8188"
for i in $(seq 1 40); do
  c=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8188/system_stats 2>/dev/null)
  [ "$c" = 200 ] && { echo ">>> COMFYUI LISTO (200) en intento $i"; break; }
  sleep 5
done
curl -s http://127.0.0.1:8188/object_info/CheckpointLoaderSimple >/dev/null 2>&1 \
  && echo ">>> checkpoint endpoint OK" || { echo "!! ComfyUI no respondió; revisa /root/comfy.log"; tail -15 /root/comfy.log; exit 1; }
echo "✓ ComfyUI listo. Render estilizado: añade --workflow stylization_v1 (sin --no-comfy)."
