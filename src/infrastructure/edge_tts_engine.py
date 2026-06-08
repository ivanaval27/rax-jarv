"""RAX JARV — Infrastructure: Edge-TTS para voz"""
import os
import subprocess
import tempfile
from typing import Optional

from ..config import config
from ..domain.interfaces import TTSEngine


class EdgeTTSEngine(TTSEngine):
    """Sintetizador de voz usando edge-tts CLI"""

    def __init__(self, voice: Optional[str] = None):
        self._voice = voice or config.edge_tts_voice

    def synthesize(self, text: str) -> Optional[bytes]:
        if not text.strip():
            return None

        print(f"🔊 Generando voz...", end=" ", flush=True)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            mp3_path = f.name

        try:
            subprocess.run(
                ["edge-tts", "--voice", self._voice,
                 "--text", text, "--write-media", mp3_path],
                check=True, capture_output=True, timeout=config.tts_timeout,
            )
            with open(mp3_path, 'rb') as f:
                data = f.read()
            print(f"{len(data)} bytes", flush=True)
            return data
        except Exception as e:
            print(f"⚠️ TTS error: {e}", flush=True)
            return None
        finally:
            try:
                os.unlink(mp3_path)
            except Exception:
                pass

    def synthesize_and_play(self, text: str) -> None:
        if not text.strip():
            return

        print(f"🔊 RAX: {text[:100]}", flush=True)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            audio_file = f.name

        try:
            subprocess.run(
                ["edge-tts", "--voice", self._voice,
                 "--text", text, "--write-media", audio_file],
                check=True, capture_output=True, timeout=config.tts_timeout,
            )
            subprocess.run(
                ["ffplay", "-nodisp", "-autoexit",
                 "-volume", "80", "-loglevel", "quiet", audio_file],
                check=True, timeout=60,
            )
        except Exception:
            pass
        finally:
            try:
                os.unlink(audio_file)
            except Exception:
                pass
