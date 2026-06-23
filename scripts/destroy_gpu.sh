#!/usr/bin/env bash
# Apaga/destruye instancias de Vast.ai. Lo caro NO es renderizar: es olvidar
# la máquina prendida. Corre esto en cuanto termines de renderizar.
#
# Uso:
#   bash scripts/destroy_gpu.sh            # lista tus instancias y pregunta
#   bash scripts/destroy_gpu.sh <ID>       # destruye esa instancia
#   bash scripts/destroy_gpu.sh --all      # destruye TODAS (pide confirmación)
#
# Requisitos: pip install vastai ; vastai set api-key TU_KEY
set -euo pipefail

if ! command -v vastai >/dev/null 2>&1; then
  echo "✗ Falta la CLI de vast. Instala con:  pip install --upgrade vastai" >&2
  exit 1
fi

destroy_one() {
  local id="$1"
  echo "==> Destruyendo instancia ${id} ..."
  vastai destroy instance "${id}"
  echo "✓ Instancia ${id} destruida."
}

# --- Modo: destruir todas ---
if [[ "${1:-}" == "--all" ]]; then
  ids="$(vastai show instances --raw | python3 -c \
    'import sys,json; print(" ".join(str(i["id"]) for i in json.load(sys.stdin)))')"
  if [[ -z "${ids// }" ]]; then
    echo "No tienes instancias activas. Nada que destruir."
    exit 0
  fi
  echo "Instancias activas: ${ids}"
  read -r -p "¿Destruir TODAS? Escribe 'si' para confirmar: " ans
  [[ "${ans}" == "si" ]] || { echo "Cancelado."; exit 0; }
  for id in ${ids}; do destroy_one "${id}"; done
  exit 0
fi

# --- Modo: ID explícito ---
if [[ -n "${1:-}" ]]; then
  destroy_one "$1"
  echo ""
  echo "Verifica que no quede nada:"
  vastai show instances
  exit 0
fi

# --- Modo: interactivo (sin argumentos) ---
echo "==> Tus instancias activas:"
vastai show instances
echo ""
ids="$(vastai show instances --raw | python3 -c \
  'import sys,json; print(" ".join(str(i["id"]) for i in json.load(sys.stdin)))')"
if [[ -z "${ids// }" ]]; then
  echo "No tienes instancias activas. Nada que pagar. 🎉"
  exit 0
fi
read -r -p "ID a destruir (o 'todas'): " choice
if [[ "${choice}" == "todas" ]]; then
  for id in ${ids}; do destroy_one "${id}"; done
else
  destroy_one "${choice}"
fi
echo ""
echo "Estado final:"
vastai show instances
