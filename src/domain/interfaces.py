"""RAX JARV — Domain interfaces (ABCs, sin implementaciones)"""
from abc import ABC, abstractmethod
from typing import Optional
from .entities import Transcript, Response


class PCMTranscriber(ABC):
    """Transcribe audio PCM float32 directamente"""
    @abstractmethod
    def transcribe_pcm(self, audio: list[float],
                       sample_rate: int = 16000) -> Transcript:
        ...


class LLMClient(ABC):
    """Cliente para consultar el LLM (Hermes)"""
    @abstractmethod
    def ask(self, prompt: str) -> str:
        ...


class TTSEngine(ABC):
    """Convierte texto a voz"""
    @abstractmethod
    def synthesize(self, text: str) -> Optional[bytes]:
        ...

    @abstractmethod
    def synthesize_and_play(self, text: str) -> None:
        """Sintetiza y reproduce en el parlante local"""


class MarkdownCleaner(ABC):
    """Limpia markdown para texto plano / TTS"""
    @abstractmethod
    def clean(self, text: str) -> str:
        ...
