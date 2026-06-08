"""RAX JARV — Application: orquestador del asistente de voz"""
import re
import threading
from typing import Optional
from ..config import config
from ..domain.entities import Transcript, Response
from ..domain.interfaces import (
    PCMTranscriber, LLMClient, TTSEngine, MarkdownCleaner
)


class MarkdownCleanerImpl(MarkdownCleaner):
    """Limpia markdown para texto plano / TTS"""

    def clean(self, text: str) -> str:
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'```[\s\S]*?```', '', text)
        text = re.sub(r'`(.+?)`', r'\1', text)
        text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^[\s]*[-*+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^[\s]*\d+\.\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^[-_]{3,}\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()


class VoiceAssistant:
    """Orquestador principal del asistente de voz"""

    def __init__(
        self,
        transcriber: PCMTranscriber,
        llm: LLMClient,
        tts: TTSEngine,
        cleaner: Optional[MarkdownCleaner] = None,
    ):
        self._transcriber = transcriber
        self._llm = llm
        self._tts = tts
        self._cleaner = cleaner or MarkdownCleanerImpl()

    def process_pcm_audio(
        self,
        audio: list[float],
        sample_rate: int = 16000,
    ) -> Response:
        """Procesa audio PCM y retorna respuesta completa"""
        transcript = self._transcriber.transcribe_pcm(audio, sample_rate)
        if transcript.is_empty:
            return Response(text="")

        return self.process_text(transcript.text)

    def process_text(self, text: str) -> Response:
        """Procesa texto y retorna respuesta"""
        response_text = self._llm.ask(text)
        cleaned = self._cleaner.clean(response_text)
        audio = self._tts.synthesize(cleaned)
        return Response(text=cleaned, audio_bytes=audio)

    def process_and_speak(self, audio: list[float],
                          sample_rate: int = 16000) -> None:
        """Procesa audio y reproduce por parlante"""
        response = self.process_pcm_audio(audio, sample_rate)
        if not response.is_empty:
            self._tts.synthesize_and_play(response.text)

    def process_text_and_speak(self, text: str) -> None:
        """Procesa texto y reproduce por parlante"""
        response = self.process_text(text)
        if not response.is_empty:
            self._tts.synthesize_and_play(response.text)

    def ask_rax(self, prompt: str) -> str:
        """Solo consulta al LLM sin TTS"""
        if not prompt.strip():
            return ""
        response = self._llm.ask(prompt)
        return self._cleaner.clean(response)
