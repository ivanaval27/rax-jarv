# 🤖 RAX JARV — Asistente de Voz en Tiempo Real

**RAX JARV** es el asistente de voz inteligente de **RAX Corp**. Escucha tu voz, la procesa con Whisper, consulta a DeepSeek a través de Hermes Agent, y responde con voz natural usando Edge-TTS.

> *"Parece Virtual, Es Real"* — RAX Corp

---

## 🎯 Características

- 🎤 **3 modos de uso**: Web (navegador), TCP (WO Mic desde teléfono), APK Android
- 🧠 **Whisper** — Transcripción de voz a texto local (modelo `small`)
- 🤖 **DeepSeek via Hermes** — Respuestas inteligentes y naturales
- 🔊 **Edge-TTS** — Voz natural en español latino (GonzaloNeural)
- 🔐 **PIN de acceso** — Seguridad con código 2727
- 📱 **APK Android** — App nativa con WebSocket encriptado
- 🏗️ **Clean Architecture** — Código limpio, mantenible y testeable

---

## 🏛️ Arquitectura

```
main.py                    ← Entry point (Factory + inyección de dependencias)
├── src/
│   ├── config.py          ← Fuente única de configuración
│   ├── domain/            ← Entidades (dataclasses) + Interfaces (ABCs)
│   ├── application/       ← Orquestador + Procesamiento de audio (VAD)
│   ├── infrastructure/    ← Whisper, Hermes CLI, Edge-TTS, TCP socket
│   └── web/               ← Servidor aiohttp HTTPS + WebSocket
```

Principios aplicados:
- ✅ **Inyección de dependencias** — Todo se construye desde `main.py`
- ✅ **Separación por capas** — Domain → Application → Infrastructure → Web
- ✅ **Sin código duplicado** — Una sola implementación de cada función
- ✅ **Interfaces ABC** — Fáciles de mockear para pruebas

---

## 🚀 Inicio Rápido

### Requisitos

- Python 3.11+
- ffmpeg
- edge-tts
- faster-whisper
- aiohttp

### Instalación

```bash
# Clonar el repo
git clone https://github.com/ivanaval27/rax-jarv.git
cd rax-jarv

# Crear y activar virtualenv
python -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install faster-whisper numpy scipy aiohttp edge-tts
```

### Modo Web (recomendado)

Abre desde el navegador de tu celular:

```bash
./start_jarvis.sh web
# o
python main.py web
```

Luego abre `https://[IP-DEL-PC]:4433` desde tu celular.
PIN: **2727**

### Modo TCP (WO Mic / AudioRelay)

```bash
./start_jarvis.sh tcp
# o
python main.py tcp
```

### Modo Cliente

```bash
./start_jarvis.sh client 192.168.2.15 12345
# o
python main.py client 192.168.2.15 12345
```

---

## 📱 APK Android

La APK `web/rax-jarv.apk` se conecta vía WebSocket seguro (`wss://`) al servidor.

- **PIN**: 2727 (validado localmente)
- **Conexión**: `wss://100.80.16.121:4433/ws` (Tailscale)
- **Permisos**: Micrófono + Internet

---

## 🌐 Endpoints Web

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/` | GET | Página principal con PIN + micrófono |
| `/login` | POST | Verifica PIN (enviar `{"pin":"2727"}`) |
| `/rax-jarv.apk` | GET | Descargar APK Android |
| `/ws` | WebSocket | Canal bidireccional de audio/TTS |

### Protocolo WebSocket

1. Cliente envía **BINARY** → Audio PCM (header `PCM` + sample rate + datos)
2. Servidor responde **TEXT** → Logs de estado `[LOG] ...`
3. Servidor responde **BINARY** → Audio MP3 (Edge-TTS)
4. Servidor responde **TEXT** → Texto de la respuesta

---

## ⚙️ Configuración

Toda la configuración está centralizada en `src/config.py`:

| Variable | Default | Descripción |
|----------|---------|-------------|
| `whisper_model` | `small` | Modelo de Whisper (tiny, base, small) |
| `edge_tts_voice` | `es-CO-GonzaloNeural` | Voz de Edge-TTS |
| `web_port` | `4433` | Puerto HTTPS |
| `ws_http_port` | `8766` | Puerto WebSocket sin SSL (para APK) |
| `tcp_listen_port` | `12345` | Puerto TCP (WO Mic) |
| `pin_code` | `2727` | PIN de acceso |
| `vad_threshold` | `0.015` | Sensibilidad de detección de voz |
| `silence_timeout` | `1.2` | Segundos de silencio para procesar |
| `min_audio_len` | `0.8` | Mínimo de audio para procesar |

---

## 🧠 Pipeline de Voz

```
🎤 Micrófono
    ↓ PCM raw (int16) o WebM
🔊 VAD (Voice Activity Detection)
    ↓ Segmento de voz
🗣️ Whisper (faster-whisper)
    ↓ Texto transcrito
🤖 Hermes → DeepSeek
    ↓ Respuesta en texto
🧹 clean_markdown()
    ↓ Texto limpio
🔊 Edge-TTS (GonzaloNeural)
    ↓ MP3 audio
📢 Parlante / WebSocket
```

---

## 🧪 Desarrollo

### Estructura del Proyecto

```
rax-jarv/
├── main.py                     # Entry point
├── src/
│   ├── config.py               # Configuración centralizada
│   ├── domain/
│   │   ├── entities.py         # Dataclasses (AudioChunk, Transcript, Response)
│   │   └── interfaces.py       # ABCs (PCMTranscriber, LLMClient, TTSEngine)
│   ├── application/
│   │   ├── audio_processor.py  # VAD, buffer, resample
│   │   └── voice_assistant.py  # Orquestador del asistente
│   ├── infrastructure/
│   │   ├── whisper_transcriber.py  # Transcripción con Whisper
│   │   ├── hermes_client.py        # Conexión a Hermes CLI
│   │   ├── edge_tts_engine.py      # Síntesis de voz
│   │   └── socket_server.py        # Servidor TCP
│   └── web/
│       └── server.py           # Servidor aiohttp + WebSocket
├── web/
│   ├── index.html              # Interfaz web
│   └── rax-jarv.apk            # APK Android
├── rax_jarvis.py               # Thin wrapper (modo TCP)
├── rax_jarvis_web.py           # Thin wrapper (modo web)
├── rax_jarvis_client.py        # Thin wrapper (modo cliente)
├── start_jarvis.sh             # Script de inicio
└── .gitignore
```

---

## 🧑‍💻 Equipo RAX

| Agente | Rol |
|--------|-----|
| **RAX (Hermes)** | Orquestador general |
| **Alan** | Auditor de Clean Architecture |
| **Scribe** | Version control y commits |
| **Sherlock** | Debugging e investigación |

---

## 📄 Licencia

MIT © RAX Corp — Creado por Ivan Nava

> RAX Corp — *"Parece Virtual, Es Real"*
