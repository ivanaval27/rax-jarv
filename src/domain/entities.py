"""RAX JARV — Domain entities (dataclasses puras, sin dependencias externas)"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AudioChunk:
    """Segmento de audio crudo (float32 normalizado)"""
    samples: list[float]
    sample_rate: int
    timestamp: float = 0.0

    @property
    def duration(self) -> float:
        return len(self.samples) / self.sample_rate if self.sample_rate > 0 else 0.0


@dataclass
class Transcript:
    """Resultado de transcripción de audio"""
    text: str
    language: str = "es"
    confidence: float = 0.0
    duration: float = 0.0

    @property
    def is_empty(self) -> bool:
        return not self.text.strip()


@dataclass
class Response:
    """Respuesta del asistente"""
    text: str = ""
    audio_bytes: Optional[bytes] = None

    @property
    def is_empty(self) -> bool:
        return not self.text.strip()


@dataclass
class VoiceSegment:
    """Segmento de voz detectado con VAD"""
    audio: list[float]
    sample_rate: int = 16000
    duration: float = 0.0
    has_wake_word: bool = False
