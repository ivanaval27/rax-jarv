"""RAX JARV — Infrastructure: Servidor TCP para WO Mic"""
import socket
import threading
import time
from typing import Callable, Optional, TYPE_CHECKING
import numpy as np

from ..config import config

if TYPE_CHECKING:
    from ..application.audio_processor import AudioProcessor


class TCPSocketServer:
    """Servidor TCP que recibe audio del teléfono (WO Mic / AudioRelay)"""

    def __init__(
        self,
        audio_processor: 'AudioProcessor',
        on_audio_segment: Callable[[np.ndarray], None],
        host: str = "0.0.0.0",
        port: Optional[int] = None,
    ):
        self._ap = audio_processor
        self._on_audio = on_audio_segment
        self._host = host
        self._port = port or config.tcp_listen_port
        self._running = False
        self._server: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _run(self):
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind((self._host, self._port))
        self._server.listen(1)
        self._server.settimeout(1.0)
        print(f"\n📡 TCP Server en puerto {self._port}...", flush=True)

        while self._running:
            try:
                conn, addr = self._server.accept()
                print(f"\n📱 Teléfono CONECTADO: {addr[0]}", flush=True)
                conn.settimeout(0.5)
                self._handle_client(conn, addr)
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    print(f"⚠️ Error servidor: {e}", flush=True)

        try:
            self._server.close()
        except Exception:
            pass

    def _handle_client(self, conn, addr):
        ap = self._ap

        try:
            while self._running:
                try:
                    data = conn.recv(4096)
                    if not data or len(data) < 100:
                        break

                    has_voice, audio = ap.detect_voice(data)

                    if has_voice:
                        if not ap.is_recording:
                            print("🎤 [grabando]", end=" ", flush=True)
                            ap.is_recording = True
                            ap.voice_buffer = [audio]
                        else:
                            ap.voice_buffer.append(audio)
                        ap.last_voice_time = time.time()
                    elif ap.is_recording and ap.voice_buffer:
                        if (time.time() - ap.last_voice_time
                                > config.silence_timeout):
                            self._flush_buffer(ap)

                except socket.timeout:
                    if ap.is_recording and ap.voice_buffer:
                        if (time.time() - ap.last_voice_time
                                > config.silence_timeout):
                            self._flush_buffer(ap)
                    continue
                except Exception as e:
                    print(f"⚠️ Error: {e}", flush=True)
                    break

        finally:
            conn.close()
            print(f"📱 Teléfono desconectado", flush=True)

    def _flush_buffer(self, ap):
        import numpy as np
        audio_completo = np.concatenate(ap.voice_buffer)
        duracion = len(audio_completo) / config.record_sample_rate
        print(f" ({duracion:.1f}s)", flush=True)
        if duracion >= config.min_audio_len:
            threading.Thread(
                target=self._on_audio,
                args=(audio_completo,),
                daemon=True,
            ).start()
        ap.is_recording = False
        ap.voice_buffer = []
