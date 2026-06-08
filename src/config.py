"""RAX JARV — Fuente única de configuración"""
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Config:
    # ─── Whisper ────────────────────────────────────────────────
    whisper_model: str = "small"
    whisper_cpu_threads: int = 4
    whisper_num_workers: int = 2
    whisper_compute_type: str = "int8"
    whisper_beam_size: int = 5
    whisper_language: str = "es"

    # ─── Audio ──────────────────────────────────────────────────
    record_sample_rate: int = 44100
    whisper_sample_rate: int = 16000
    vad_threshold: float = 0.015
    silence_timeout: float = 1.2
    min_audio_len: float = 0.8

    # ─── Edge TTS ───────────────────────────────────────────────
    edge_tts_voice: str = "es-CO-GonzaloNeural"
    tts_timeout: int = 30

    # ─── Network ────────────────────────────────────────────────
    web_port: int = 4433
    ws_http_port: int = 8766
    tcp_listen_port: int = 12345

    # ─── Paths ──────────────────────────────────────────────────
    project_dir: Path = field(default_factory=lambda: Path.home() / "rax-jarvis")
    web_dir: Path = field(default_factory=lambda: Path.home() / "rax-jarvis" / "web")
    ssl_cert: Path = field(default_factory=lambda: Path("/tmp/rax-cert.pem"))
    ssl_key: Path = field(default_factory=lambda: Path("/tmp/rax-key.pem"))

    # ─── Security ───────────────────────────────────────────────
    pin_code: str = "2727"

    # ─── Wake Words ─────────────────────────────────────────────
    wake_words: tuple = ("rax", "oye", "jarvis", "bro")
    wake_word_enabled: bool = False  # True = solo responde si detecta wake word

    # ─── Hermes ─────────────────────────────────────────────────
    hermes_timeout: int = 60
    hermes_response_instruction: str = (
        "(Responde breve, máximo 2 oraciones, sin markdown. Solo texto plano.)"
    )

    # ─── Assistant Identity ─────────────────────────────────────
    assistant_name: str = "RAX"
    assistant_version: str = "2.1"
    assistant_tagline: str = "Parece Virtual, Es Real"

    @property
    def hermes_cmd(self) -> list[str]:
        return ["hermes", "chat", "-q", "{prompt}", "-Q"]

    @property
    def ffplay_cmd(self) -> list[str]:
        return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "{file}"]


# Instancia global compartida
config = Config()
