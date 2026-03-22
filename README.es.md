<p align="center">
  <img src="assets/cc-digest.jpg" width="640" alt="cc-digest">
  <h1 align="center">cc-digest</h1>
  <p align="center">
    Extrae, resume y busca tus sesiones de <a href="https://docs.anthropic.com/en/docs/claude-code">Claude Code</a> usando LLMs locales.
  </p>
  <p align="center">
    <a href="https://github.com/vayaSEO/cc-digest/actions/workflows/ci.yml"><img src="https://github.com/vayaSEO/cc-digest/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
    <img src="https://img.shields.io/pypi/pyversions/cc-digest" alt="Python">
    <img src="https://img.shields.io/github/license/vayaSEO/cc-digest" alt="Licencia">
  </p>
  <p align="center">
    <a href="README.md">English</a> · <a href="README.es.md">Español</a> · <a href="README.zh.md">中文</a> · <a href="README.ja.md">日本語</a>
  </p>
</p>

---

Convierte miles de líneas de transcripciones en resúmenes concisos y buscables — completamente offline, sin necesidad de API keys.

<p align="center">
  <video src="https://github.com/user-attachments/assets/15970642-2674-4497-9e8d-eb18d3c60c64" width="700" controls></video>
</p>

## Qué hace

1. **Extract** — lee los transcripts JSONL de Claude Code desde `~/.claude/projects/` y almacena datos estructurados de sesión
2. **Digest** — resume cada sesión en ~10 bullet points usando un LLM local vía [Ollama](https://ollama.com)
3. **Embed** — genera embeddings vectoriales de los resúmenes para búsqueda semántica
4. **Search** — encuentra sesiones pasadas por significado, no solo por palabras clave
5. **Stats** — resumen general de tu historial de sesiones

## Instalación

```bash
pip install cc-digest
```

O desde el código fuente:

```bash
git clone https://github.com/vayaSEO/cc-digest.git
cd cc-digest
pip install -e .
```

<details>
<summary>Opcional: backend MongoDB</summary>

```bash
pip install cc-digest[mongo]
```

Configura `STORAGE_BACKEND=mongo` y `MONGO_URI` en tu fichero `.env`.

</details>

## Inicio rápido

```bash
# 1. Extraer sesiones de los transcripts de Claude Code
cc-digest extract

# 2. Resumir con LLM local (requiere Ollama corriendo)
cc-digest digest

# 3. Generar embeddings para búsqueda semántica
cc-digest embed

# 4. Buscar en tus sesiones
cc-digest search "error CORS en FastAPI"

# 5. Ver estadísticas
cc-digest stats
```

## Requisitos

- **Python** >= 3.11
- **Ollama** (para digest y búsqueda) — [instalar](https://ollama.com/download)

```bash
# Descargar los modelos recomendados
ollama pull qwen3:14b          # resúmenes
ollama pull nomic-embed-text   # embeddings
```

## Comandos

### `cc-digest extract`

Lee transcripts JSONL y almacena las sesiones.

```bash
cc-digest extract                     # procesar todas las sesiones
cc-digest extract --session UUID      # una sola sesión
cc-digest extract --dry-run           # previsualizar sin escribir
cc-digest extract --export-md         # también guardar ficheros .md
cc-digest extract --min-messages 10   # saltar sesiones cortas
```

### `cc-digest digest`

Resume sesiones usando un LLM local.

```bash
cc-digest digest                      # resumir las no procesadas
cc-digest digest --force              # re-resumir todo
cc-digest digest --model gemma3:12b   # usar otro modelo
cc-digest digest --limit 10           # solo las primeras 10
cc-digest digest --export-md          # guardar resúmenes como .md
```

### `cc-digest embed`

Genera embeddings vectoriales para búsqueda semántica.

```bash
cc-digest embed                       # embeber los no procesados
cc-digest embed --force               # re-embeber todo
cc-digest embed --limit 10            # solo los primeros 10
```

### `cc-digest search`

Busca sesiones por consulta.

```bash
cc-digest search "problema docker compose"
cc-digest search "auth middleware" --project myapp
cc-digest search "deploy" --mode grep    # forzar búsqueda de texto
cc-digest search "pipeline" --top 10     # más resultados
```

### `cc-digest stats`

Resumen de tus datos de sesión.

```bash
cc-digest stats
cc-digest stats --project myapp
```

## Configuración

Copia `.env.example` a `.env` y ajusta según necesites:

```bash
cp .env.example .env
```

<details>
<summary>Todas las variables de configuración</summary>

| Variable | Por defecto | Descripción |
|---|---|---|
| `CLAUDE_PROJECTS_DIR` | `~/.claude/projects` | Donde Claude Code guarda los transcripts |
| `USER_DISPLAY_NAME` | `User` | Tu nombre en el markdown exportado |
| `STORAGE_BACKEND` | `sqlite` | `sqlite` (por defecto) o `mongo` |
| `OLLAMA_URL` | `http://localhost:11434` | URL del servidor Ollama |
| `DIGEST_MODEL` | `qwen3:14b` | Modelo LLM para resumir |
| `EMBED_MODEL` | `nomic-embed-text` | Modelo para embeddings |
| `MIN_MESSAGES` | `4` | Saltar sesiones con menos mensajes |

</details>

## Almacenamiento

**SQLite** (por defecto) — sin dependencias, todo en `~/.local/share/cc-digest/cc-digest.db`.

**MongoDB** (opcional) — instala con `pip install cc-digest[mongo]`, configura `STORAGE_BACKEND=mongo` y `MONGO_URI` en `.env`.

## Rendimiento

8 modelos testeados en Apple Silicon M4 Pro — 30 sesiones, 67K palabras de input:

| Modelo | Params | Avg/sesión | Compresión | Notas |
|---|---|---|---|---|
| **`qwen3:14b`** | 14B | ~36s | 15:1 | **Por defecto** — mejor precisión, respeta el idioma de la conversación |
| `glm4:9b` | 9B | ~20s | 18:1 | Opción rápida más fiable |
| `mistral-nemo` | 12B | ~27s | 14:1 | Sólido todoterreno |
| `gemma3:12b` | 12B | ~34s | 10:1 | Output más detallado |
| `granite3.3:8b` | 8B | ~26s | 11:1 | Buen equilibrio velocidad/calidad |

> `qwen3:14b` para precisión. `glm4:9b` o `granite3.3:8b` para ejecuciones más rápidas. Embedding + búsqueda es instantáneo (<1s).

<details>
<summary>Detalles completos del benchmark (3 modelos más + análisis de calidad)</summary>

| Modelo | Params | Avg/sesión | Compresión | Notas |
|---|---|---|---|---|
| `qwen3.5:9b` | 9B | ~32s | 10:1 | Más lento de lo esperado para su tamaño |
| `phi4-mini` | 3.8B | ~10s | 12:1 | El más rápido, pero introdujo errores factuales |
| `nemotron-mini` | 4.2B | ~4s | 550:1 | No recomendado — 8/30 respuestas vacías |

**Comparación cualitativa** (3 sesiones lado a lado):
- `qwen3:14b`: mejor precisión factual, bullets estructurados, respeta el idioma de la conversación
- `phi4-mini`: 3.4x más rápido pero invirtió una decisión en una sesión
- `granite3.3:8b`: buen punto medio entre velocidad y calidad

La condensación de sesiones usa una estrategia head/tail inteligente — mantiene contexto del inicio y final, comprime el medio. Maneja sesiones de 1K a 1M+ caracteres.

> Los tiempos varían según la longitud de la sesión y el hardware. Se recomienda aceleración GPU.

</details>

## Cómo funciona

```
~/.claude/projects/**/*.jsonl
         │
    cc-digest extract
         │
    ┌────▼────┐
    │ SQLite  │  (o MongoDB)
    │ sessions│
    └────┬────┘
         │
    cc-digest digest (Ollama → qwen3:14b)
         │
    ┌────▼────┐
    │ SQLite  │
    │ digests │
    └────┬────┘
         │
    cc-digest embed (Ollama → nomic-embed-text)
         │
    ┌────▼──────┐
    │ SQLite    │
    │ embeddings│
    └────┬──────┘
         │
    cc-digest search "tu consulta"
         │
    ┌────▼────────┐
    │ Resultados  │
    └─────────────┘
```

## Licencia

MIT
