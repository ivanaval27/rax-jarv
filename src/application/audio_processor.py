"""RAX JARV — Application: procesamiento de audio (VAD, buffer, resample)"""
import time
from typing import Optional
import numpy as np
from scipy import signal as sg
from ..config import config
from ..domain.interfaces import VADDetector


class AudioProcessor:
    """Procesa audio: VAD, bufferización, resample, segmentación"""

    def __init__(self):
        self.voice_buffer: list[np.ndarray] = []
        self.is_recording: bool = False
        self.last_voice_time: float = 0.0
        import threading
        self._lock = threading.Lock()

    def resample_to_16k(self, audio_44k: np.ndarray) -> np.ndarray:
        """Resamplea de 44.1kHz a 16kHz"""
        if len(audio_44k) == 0:
            return np.array([], dtype=np.float32)
        target_len = int(len(audio_44k) * config.whisper_sample_rate
                         / config.record_sample_rate)
        return sg.resample(audio_44k, target_len).astype(np.float32)

    def detect_voice(self, chunk: bytes) -> tuple[bool, np.ndarray]:
        """Detecta actividad de voz por energía RMS"""
        audio = (np.frombuffer(chunk, dtype=np.int16)
                 .astype(np.float32) / 32768.0)
        energy = np.sqrt(np.mean(audio ** 2))
        return energy > config.vad_threshold, audio

    def feed_chunk(self, chunk: bytes) -> Optional[np.ndarray]:
        """Alimenta un chunk de audio, retorna el segmento si hay uno listo"""
        has_voice, audio = self.detect_voice(chunk)
        now = time.time()

        with self._lock:
            if has_voice:
                if not self.is_recording:
                    print("🎤 [grabando]", end=" ", flush=True)
                    self.is_recording = True
                    self.voice_buffer = [audio]
                else:
                    self.voice_buffer.append(audio)
                self.last_voice_time = now
                return None

            if self.is_recording and self.voice_buffer:
                if now - self.last_voice_time > config.silence_timeout:
                    audio_completo = np.concatenate(self.voice_buffer)
                    duracion = len(audio_completo) / config.record_sample_rate
                    print(f" ({duracion:.1f}s)", flush=True)
                    self.is_recording = False
                    self.voice_buffer = []
                    if duracion >= config.min_audio_len:
                        return audio_completo
        return None

    def check_timeout(self) -> np.ndarray | None:
        """Verifica timeout de silencio (para socket timeout)"""
        now = time.time()
        with self._lock:
            if self.is_recording and self.voice_buffer:
                if now - self.last_voice_time > config.silence_timeout:
                    audio_completo = np.concatenate(self.voice_buffer)
                    duracion = len(audio_completo) / config.record_sample_rate
                    print(f" ({duracion:.1f}s)", flush=True)
                    self.is_recording = False
                    self.voice_buffer = []
                    if duracion >= config.min_audio_len:
                        return audio_completo
        return None

    def reset(self):
        with self._lock:
            self.voice_buffer = []
            self.is_recording = False
            self.last_voice_time = 0.0

    def has_wake_word(self, text: str, wake_words: tuple = None) -> bool:
        """Verifica si el texto contiene una palabra de activación"""
        if wake_words is None:
            wake_words = config.wake_words
        txt = text.lower().strip()
        return any(w in txt for w in wake_words)
