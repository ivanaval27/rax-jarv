#!/bin/bash
# RAX JARVIS v2.1 — Script de inicio
cd "$(dirname "$0")"
source bin/activate

echo "🚀 Iniciando RAX JARVIS..."
echo ""

# Elegir modo: web (default), tcp, o client IP PORT
MODE="${1:-web}"

python main.py "$MODE" "$2" "$3"
