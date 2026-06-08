"""RAX JARV v2 — Thin wrapper: mantiene compatibilidad con scripts existentes"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from main import mode_tcp

if __name__ == "__main__":
    mode_tcp()
