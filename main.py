"""RAX JARV v2.1 — Entry point con inyección de dependencias"""
import sys
import time
import threading
import asyncio
from pathlib import Path

# Asegurar que src/ está en el path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import config
from src.infrastructure.whisper_transcriber import WhisperTranscriber
from src.infrastructure.hermes_client import HermesClient
from src.infrastructure.edge_tts_engine import EdgeTTSEngine
from src.infrastructure.socket_server import TCPSocketServer
from src.application.voice_assistant import VoiceAssistant
from src.application.audio_processor import AudioProcessor


MODE = sys.argv[1] if len(sys.argv) > 1 else "web"


def print_banner():
    print(f"""
╔══════════════════════════════════════╗
║     🤖 {config.assistant_name} JARVIS v{config.assistant_version}              ║
║  {config.assistant_tagline}     ║
╚══════════════════════════════════════╝
  Modo: {MODE.upper()}
  Voz:  {config.edge_tts_voice}
""")


def make_assistant():
    """Factory: crea el asistente con todas las dependencias inyectadas"""
    llm = HermesClient()
    tts = EdgeTTSEngine()
    transcriber = WhisperTranscriber()
    return VoiceAssistant(transcriber=transcriber, llm=llm, tts=tts)


def mode_tcp():
    """Modo TCP: vortex1 es servidor, teléfono se conecta vía WO Mic"""
    print_banner()
    assistant = make_assistant()
    ap = AudioProcessor()

    def on_segment(audio_44k):
        audio_16k = ap.resample_to_16k(audio_44k)
        if len(audio_16k) < config.whisper_sample_rate * config.min_audio_len:
            return
        assistant.process_and_speak(audio_16k.tolist(), 16000)

    server = TCPSocketServer(
        audio_processor=ap,
        on_audio_segment=on_segment,
        port=config.tcp_listen_port,
    )
    server.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Apagando...", flush=True)
        server.stop()


def mode_web():
    """Modo Web: servidor HTTPS + WebSocket"""
    print_banner()
    from src.web.server import WebServer

    # Inyección de dependencias desde main.py
    assistant = make_assistant()
    server = WebServer(assistant=assistant)

    # Configurar logging
    import logging
    log_path = config.project_dir / "server.log"
    logging.basicConfig(
        filename=str(log_path),
        level=logging.INFO,
        format="%(asctime)s %(message)s",
        datefmt="%H:%M:%S",
    )

    import builtins
    _original_print = builtins.print
    def _logged_print(*args, **kwargs):
        msg = " ".join(str(a) for a in args)
        logging.info(msg)
        kwargs["flush"] = True
        _original_print(*args, **kwargs)
    builtins.print = _logged_print

    asyncio.run(server.run())


def mode_client():
    """Modo Cliente: vortex1 se conecta al teléfono (WO Mic servidor)"""
    if len(sys.argv) < 3:
        print(f"Uso: {sys.argv[0]} client <IP_DEL_TELEFONO> <PUERTO>")
        print(f"Ej: {sys.argv[0]} client 192.168.2.15 12345")
        sys.exit(1)

    phone_ip = sys.argv[2]
    phone_port = int(sys.argv[3])

    print_banner()
    print(f"  📱 Teléfono: {phone_ip}:{phone_port}")
    print()

    assistant = make_assistant()
    ap = AudioProcessor()

    import socket
    import time as _time

    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0)
            print(f"📱 Conectando a {phone_ip}:{phone_port}...", flush=True)
            sock.connect((phone_ip, phone_port))
            print(f"✅ Conectado!", flush=True)
            sock.settimeout(0.5)

            ap.reset()
            audio_data = b""

            while True:
                try:
                    data = sock.recv(4096)
                    if not data or len(data) < 50:
                        continue

                    audio_data += data
                    chunk_size = int(config.record_sample_rate * 0.1 * 2)

                    while len(audio_data) >= chunk_size:
                        chunk = audio_data[:chunk_size]
                        audio_data = audio_data[chunk_size:]

                        segment = ap.feed_chunk(chunk)
                        if segment is not None and len(segment) >= config.whisper_sample_rate * config.min_audio_len:
                            audio_16k = ap.resample_to_16k(segment)
                            threading.Thread(
                                target=assistant.process_and_speak,
                                args=(audio_16k.tolist(), 16000),
                                daemon=True,
                            ).start()

                except socket.timeout:
                    segment = ap.check_timeout()
                    if segment is not None and len(segment) >= config.whisper_sample_rate * config.min_audio_len:
                        audio_16k = ap.resample_to_16k(segment)
                        if ap.has_wake_word("") or True:  # Client mode: check wake word
                            threading.Thread(
                                target=assistant.process_and_speak,
                                args=(audio_16k.tolist(), 16000),
                                daemon=True,
                            ).start()
                    continue
                except Exception as e:
                    print(f"⚠️ Error: {e}", flush=True)
                    break

            sock.close()
            print("📱 Desconectado. Reconectando en 5s...", flush=True)
            _time.sleep(5)

        except (ConnectionRefusedError, socket.timeout) as e:
            print(f"⏳ No se pudo conectar ({e}), reintentando...",
                  flush=True)
            _time.sleep(3)
        except Exception as e:
            print(f"⚠️ Error: {e}, reintentando en 5s...", flush=True)
            _time.sleep(5)


if __name__ == "__main__":
    if MODE == "tcp":
        mode_tcp()
    elif MODE == "web":
        mode_web()
    elif MODE == "client":
        mode_client()
    else:
        print(f"Modos: web (default), tcp, client IP PORT")
        sys.exit(1)
