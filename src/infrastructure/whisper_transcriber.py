"""RAX JARV — Infrastructure: Transcripción con Whisper"""
import os
import subprocess
import tempfile
from typing import Optional
import numpy as np
from scipy import signal as sg
from faster_whisper import WhisperModel

from ..config import config
from ..domain.entities import Transcript
from ..domain.interfaces import PCMTranscriber


class WhisperTranscriber(PCMTranscriber):
    """Transcripción de audio usando faster-whisper"""

    def __init__(self, model_name: Optional[str] = None):
        model_name = model_name or config.whisper_model
        print(f"🎙️  Cargando Whisper {model_name}...", flush=True)
        import time
        start = time.time()
        self._model = WhisperModel(
            model_name, device="cpu",
            compute_type=config.whisper_compute_type,
            cpu_threads=config.whisper_cpu_threads,
            num_workers=config.whisper_num_workers,
        )
        print(f"✅ Whisper {model_name} en {time.time()-start:.1f}s", flush=True)

    def transcribe_pcm(
        self,
        audio: list[float],
        sample_rate: int = 16000,
    ) -> Transcript:
        audio_np = np.array(audio, dtype=np.float32)

        if len(audio_np) < config.whisper_sample_rate * 0.5:
            return Transcript(text="", duration=len(audio_np)/sample_rate)

        print(f"🗣️ Transcribiendo PCM ({len(audio_np)/sample_rate:.1f}s)...",
              end=" ", flush=True)

        segments, info = self._model.transcribe(
            audio_np, language=config.whisper_language,
            beam_size=config.whisper_beam_size,
            condition_on_previous_text=False,
        )
        text = " ".join(s.text.strip() for s in segments)
        print(f"📝 {text}", flush=True)
        return Transcript(
            text=text,
            language=config.whisper_language,
            duration=len(audio_np)/sample_rate,
        )

    def transcribe_webm(self, webm_bytes: bytes) -> Transcript:
        """Transcribe audio WebM/opus usando ffmpeg como puente"""
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
            webm_path = f.name
            f.write(webm_bytes)

        try:
            wav_path = webm_path + ".wav"
            result = subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error",
                 "-i", webm_path,
                 "-ar", "16000", "-ac", "1", wav_path],
                check=False, timeout=15, capture_output=True,
            )
            if result.returncode != 0:
                print(f"⚠️ ffmpeg error: {result.stderr.decode()[:200]}",
                      flush=True)
                return Transcript(text="")

            import wave
            with wave.open(wav_path, 'rb') as wf:
                raw = wf.readframes(wf.getnframes())
                sampwidth = wf.getsampwidth()
                nchannels = wf.getnchannels()

            if sampwidth == 2:
                audio = (np.frombuffer(raw, dtype=np.int16)
                         .astype(np.float32) / 32768.0)
            elif sampwidth == 4:
                audio = (np.frombuffer(raw, dtype=np.int32)
                         .astype(np.float32) / 2147483648.0)
            else:
                return Transcript(text="")

            if nchannels > 1:
                audio = audio.reshape(-1, nchannels).mean(axis=1)

            if len(audio) < 8000:
                return Transcript(text="")

            return self.transcribe_pcm(audio.tolist(), 16000)

        finally:
            for p in [webm_path, wav_path]:
                try:
                    os.unlink(p)
                except Exception:
                    pass
