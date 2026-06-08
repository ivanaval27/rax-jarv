"""RAX JARV — Infrastructure: Cliente Hermes (LLM)"""
import subprocess

from ..config import config
from ..domain.interfaces import LLMClient


class HermesClient(LLMClient):
    """Cliente para Hermes CLI vía subprocess"""

    def __init__(self, timeout: int = None):
        self._timeout = timeout or config.hermes_timeout

    def ask(self, prompt: str) -> str:
        if not prompt.strip():
            return ""

        full_prompt = f"{prompt}\n\n{config.hermes_response_instruction}"

        print("🤖 RAX pensando...", end=" ", flush=True)
        try:
            result = subprocess.run(
                ["hermes", "chat", "-q", full_prompt, "-Q"],
                capture_output=True, text=True, timeout=self._timeout,
            )
            response = result.stdout.strip()
            # Quitar línea de session_id si existe
            if response.startswith("session_id:"):
                lines = response.split("\n", 1)
                response = lines[1].strip() if len(lines) > 1 else ""

            if not response:
                response = "No entendí bien, ¿puedes repetirlo?"

            print(f"💬 {response[:80]}...", flush=True)
            return response

        except subprocess.TimeoutExpired:
            return "Lo siento, estoy procesando, un momento."
        except Exception as e:
            print(f"⚠️ Error RAX: {e}", flush=True)
            return "Disculpa, tuve un problema técnico."
