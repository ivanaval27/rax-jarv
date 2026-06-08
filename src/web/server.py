"""RAX JARV — Web: Servidor aiohttp con HTTPS + WebSocket"""
import asyncio
import json
import os
import ssl
import subprocess
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

from aiohttp import web, WSMsgType

from ..config import config

if TYPE_CHECKING:
    from ..application.voice_assistant import VoiceAssistant


class WebServer:
    """Servidor web con página, WebSocket y login PIN"""

    def __init__(self, assistant: 'VoiceAssistant'):
        self._assistant = assistant
        self._transcriber = assistant._transcriber
        self._app = web.Application()
        self._setup_routes()
        self._ensure_ssl_certs()

    def _setup_routes(self):
        self._app.router.add_get('/', self._handle_index)
        self._app.router.add_post('/login', self._handle_login)
        self._app.router.add_get('/rax-jarv.apk', self._handle_apk)
        self._app.router.add_get('/rax-jarvis.apk', self._handle_apk)
        self._app.router.add_get('/ws', self._handle_ws)

    def _ensure_ssl_certs(self):
        if not config.ssl_cert.exists() or not config.ssl_key.exists():
            print("🔐 Generando certificados SSL...", flush=True)
            subprocess.run([
                "openssl", "req", "-x509", "-newkey", "rsa:4096",
                "-keyout", str(config.ssl_key),
                "-out", str(config.ssl_cert),
                "-days", "3650", "-nodes",
                "-subj", "/CN=192.168.2.24",
            ], check=True, capture_output=True)

    async def _handle_index(self, request):
        html_path = config.web_dir / "index.html"
        if html_path.exists():
            return web.FileResponse(html_path)
        return web.Response(text="<h1>RAX JARV</h1><p>Cargando...</p>",
                            content_type="text/html")

    async def _handle_login(self, request):
        try:
            data = await request.json()
            pin = str(data.get("pin", ""))
            if pin == config.pin_code:
                return web.json_response(
                    {"ok": True, "message": "Acceso concedido"})
            return web.json_response(
                {"ok": False, "message": "PIN incorrecto"}, status=401)
        except Exception as e:
            return web.json_response(
                {"ok": False, "message": str(e)}, status=400)

    async def _handle_apk(self, request):
        apk_path = config.web_dir / "rax-jarv.apk"
        if apk_path.exists():
            return web.FileResponse(apk_path)
        apk_path2 = config.web_dir / "rax-jarvis.apk"
        if apk_path2.exists():
            return web.FileResponse(apk_path2)
        return web.Response(text="APK no encontrada", status=404)

    async def _handle_ws(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        print(f"\n📱 Cliente web conectado!", flush=True)
        await ws.send_str("✅ Conectado a RAX JARVIS")

        try:
            async for msg in ws:
                if msg.type == WSMsgType.BINARY:
                    audio_data = msg.data
                    print(f"📦 Audio recibido: {len(audio_data)} bytes",
                          flush=True)
                    await ws.send_str("[LOG] 📦 Audio recibido, procesando...")

                    import numpy as np

                    if (len(audio_data) > 5
                            and audio_data[:3] == b'PCM'):
                        sample_rate = int.from_bytes(
                            audio_data[3:5], 'little')
                        pcm_bytes = audio_data[5:]
                        audio = (np.frombuffer(pcm_bytes, dtype=np.int16)
                                 .astype(np.float32) / 32768.0)
                        duracion = (len(audio) / sample_rate
                                    if sample_rate > 0 else 0)
                        await ws.send_str(
                            f"[LOG] 🎵 Audio: {duracion:.1f}s "
                            f"@ {sample_rate}Hz")

                        if len(audio) < 4000:
                            await ws.send_str(
                                "❌ Muy corto, habla un poco más")
                            continue

                        await ws.send_str(
                            "[LOG] 🗣️ Transcribiendo con Whisper...")
                        response = self._assistant.process_pcm_audio(
                            audio.tolist(), sample_rate)
                    else:
                        await ws.send_str(
                            "[LOG] 🗣️ Procesando audio...")
                        transcript = self._transcriber.transcribe_webm(
                            audio_data)
                        if transcript.is_empty:
                            await ws.send_str("❌ No te escuché bien")
                            continue
                        response = self._assistant.process_text(
                            transcript.text)

                    if response.is_empty:
                        await ws.send_str("❌ No te escuché bien")
                        continue

                    await ws.send_str(
                        f"📝 Dijiste: \"{response.text}\"")
                    await ws.send_str("[LOG] 🔊 Generando audio...")

                    if response.audio_bytes:
                        await ws.send_bytes(response.audio_bytes)
                        await ws.send_str(f"🤖 {response.text}")
                        await ws.send_str("[LOG] ✅ Listo")
                        self._play_locally(response.audio_bytes)

                elif msg.type == WSMsgType.TEXT:
                    print(f"📝 Texto: {msg.data}", flush=True)

        except Exception as e:
            print(f"⚠️ Error WS: {e}", flush=True)
        finally:
            print("📱 Cliente desconectado", flush=True)

        return ws

    def _play_locally(self, mp3_bytes: bytes):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            local_path = f.name
        try:
            with open(local_path, 'wb') as f:
                f.write(mp3_bytes)
            subprocess.run(
                ["ffplay", "-nodisp", "-autoexit",
                 "-volume", "100", "-loglevel", "quiet", local_path],
                check=True, timeout=60,
            )
        except Exception:
            pass
        finally:
            try:
                os.unlink(local_path)
            except Exception:
                pass

    async def run(self):
        ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_ctx.load_cert_chain(str(config.ssl_cert), str(config.ssl_key))

        runner = web.AppRunner(self._app)
        await runner.setup()

        site = web.TCPSite(runner, "0.0.0.0", config.web_port,
                           ssl_context=ssl_ctx)
        await site.start()

        site_ws = web.TCPSite(runner, "0.0.0.0", config.ws_http_port)
        await site_ws.start()

        print(f"""
╔══════════════════════════════════════╗
║     🤖 {config.assistant_name} JARVIS v{config.assistant_version}          ║
║     Web: habla desde tu celular      ║
╚══════════════════════════════════════╝
  🌐 https://192.168.2.24:{config.web_port}
  🔊 Voz: {config.edge_tts_voice}
  🎙️ Abre desde el navegador de tu celu
  📱 APK: /rax-jarv.apk
""", flush=True)

        await asyncio.Event().wait()
