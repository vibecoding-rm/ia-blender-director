#!/usr/bin/env bash
# Busca en Vast.ai la GPU más BARATA con buen rendimiento para renderizar el
# noticiero en Blender 4.2 EEVEE (rasterización: prioriza VRAM + red, no CUDA).
#
# Uso:
#   bash scripts/find_gpu.sh                 # RTX 3090, 24GB, top 10 más baratas
#   GPU=RTX_4090 bash scripts/find_gpu.sh    # otra GPU
#   GPU='RTX_3090,RTX_4090,RTX_3060' bash scripts/find_gpu.sh   # comparar tiers
#   MAX_DPH=0.25 bash scripts/find_gpu.sh    # tope de $/hora
#
# Requisitos: pip install vastai ; vastai set api-key TU_KEY
# Después, alquila con:  vastai create instance <ID> --image ... (ver más abajo)
set -euo pipefail

GPU="${GPU:-RTX_3090}"          # nombre(s) de GPU; coma para varias
RELIABILITY="${RELIABILITY:-0.98}"
INET_DOWN="${INET_DOWN:-200}"   # Mbps de bajada mínimos (descargas rápidas)
DISK="${DISK:-40}"              # GB de disco mínimos
LIMIT="${LIMIT:-10}"
MAX_DPH="${MAX_DPH:-}"          # tope opcional de dólares/hora

if ! command -v vastai >/dev/null 2>&1; then
  echo "✗ Falta la CLI de vast. Instala con:  pip install --upgrade vastai" >&2
  exit 1
fi

# Construye el predicado de búsqueda.
if [[ "${GPU}" == *,* ]]; then
  gpu_pred="gpu_name in [${GPU}]"
else
  gpu_pred="gpu_name=${GPU}"
fi

query="${gpu_pred} num_gpus=1 reliability>${RELIABILITY} inet_down>${INET_DOWN} disk_space>${DISK} rentable=true verified=true"
if [[ -n "${MAX_DPH}" ]]; then
  query="${query} dph_total<${MAX_DPH}"
fi

echo "==> Buscando: ${query}"
echo "    (ordenado por \$/hora ascendente; las más baratas arriba)"
echo ""

# Tabla legible para humanos.
vastai search offers "${query}" -o 'dph+' --limit "${LIMIT}"

echo ""
echo "Para alquilar una (usa el ID de la columna izquierda):"
echo "  vastai create instance <ID> \\"
echo "    --image nvidia/cuda:12.4.1-runtime-ubuntu22.04 \\"
echo "    --disk ${DISK} --ssh"
echo ""
echo "Luego dentro de la instancia: bash scripts/provision_gpu.sh"
echo "⚠ Al terminar:  bash scripts/destroy_gpu.sh   (evita cargos)"
