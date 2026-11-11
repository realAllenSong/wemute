"""Wemute as an MCP server, so any agent can read and convert files with it.

    wemute mcp        (or: Wemute --cli mcp)

Speaks the Model Context Protocol over stdin/stdout: newline-delimited
JSON-RPC 2.0. Every tool call runs one ``wemute`` command in its own process,
the same commands the CLI acceptance tests cover, so a file that crashes a
converter never takes the server down, and the server needs no extra
dependencies.

Tools:
    extract        any file or folder → Markdown or plain text
    convert        files → other formats, or through one tool (remove_background, to_pdf…)
    list_actions   the tool ids ``convert`` accepts
    list_models    the optional AI models and whether each is installed
    install_model  download one of them
    doctor         what works on this Mac
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from wemute import __version__
from wemute.finder_actions import wemute_command

PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
DEFAULT_MAX_CHARS = 200_000

INSTRUCTIONS = (
    "Wemute reads and converts files on this Mac; nothing is uploaded. "
    "Use `extract` to turn any document, spreadsheet, slide deck, PDF (with OCR), "
    "screenshot, e-mail, archive, folder or recording into text you can read. "
    "Use `convert` to produce files in other formats; call `list_actions` first "
    "to find a tool id such as remove_background, to_pdf, format:image:PNG or subtitles_srt. Paths must be absolute."
)

_PATHS = {
    "type": "array",
    "items": {"type": "string"},
    "minItems": 1,
    "description": "Absolute paths of files or folders on this Mac.",
}

TOOLS: list[dict[str, Any]] = [
    {
        "name": "extract",
        "title": "Read files as text",
        "description": (
            "Turn files or folders into Markdown (or plain text) a language model can read. "
            "Handles PDF (tables kept; scanned pages read with OCR), Word, Excel, PowerPoint "
            "with speaker notes, Pages, Numbers, Keynote, images and screenshots (OCR, QR codes), "
            "HTML, e-mail with attachments, EPUB, ZIP and other archives, CSV, JSON, SVG and code. "
            "Audio and video become a timestamped transcript (needs ThunderTalk); "
            "speakers=true labels who said what."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "paths": _PATHS,
                "format": {"type": "string", "enum": ["md", "txt"], "default": "md",
                           "description": "md keeps headings, tables, pages and slides; txt drops the markup."},
                "ocr": {"type": "string", "enum": ["auto", "always", "never"], "default": "auto",
                        "description": "auto reads only pages and images without a text layer."},
                "speakers": {"type": "boolean", "default": False,
                             "description": "Recordings: label each speaker (S01, S02, …)."},
                "language": {"type": "string", "default": "auto",
                             "description": "Speech language of recordings: auto, zh, en, …"},
                "max_rows": {"type": "integer", "minimum": 1, "default": 5000,
                             "description": "Most rows kept per sheet or table."},
                "max_chars": {"type": "integer", "minimum": 1000, "default": DEFAULT_MAX_CHARS,
                              "description": "Cut the reply after this many characters; a note says so."},
            },
            "required": ["paths"],
        },
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "convert",
        "title": "Convert files",
        "description": (
            "Convert files and return the paths of the new files. Without `action`, each file "
            "becomes its kind's default format (HEIC→JPG, MOV→MP4, DOCX→PDF…). With `action`, "
            "every file runs through that tool: a format (format:image:PNG, format:audio:MP3, to_pdf…), "
            "photo tools (remove_background, id_white, portrait_blur, ocr_pdf, scan_pdf…), subtitles "
            "and more; see list_actions. Outputs never overwrite existing files."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "paths": _PATHS,
                "action": {"type": "string", "description": "A tool id from list_actions. Omit for default formats."},
                "out_dir": {"type": "string",
                            "description": "Absolute folder for the outputs. Default: the app's save location setting "
                                           "(normally next to each original)."},
            },
            "required": ["paths"],
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "list_actions",
        "title": "List conversion tools",
        "description": "Every tool id that convert's `action` accepts, with its title. Optional `query` filters by id or title.",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "e.g. pdf, background, subtitles"}},
        },
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "list_models",
        "title": "List optional AI models",
        "description": "The optional local AI models (erase, upscale, vocal separation…) and whether each is installed.",
        "inputSchema": {"type": "object", "properties": {}},
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "install_model",
        "title": "Install an AI model",
        "description": "Download one optional AI model by id (see list_models). Some tools need one before they run.",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "string", "description": "A model id from list_models."}},
            "required": ["id"],
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True},
    },
    {
        "name": "doctor",
        "title": "Check Wemute",
        "description": "What works on this Mac: version, certificates, network, components, models and ThunderTalk.",
        "inputSchema": {"type": "object", "properties": {}},
        "annotations": {"readOnlyHint": True, "openWorldHint": True},
    },
]


class ToolError(Exception):
    """A tool call that failed in a way the agent should read."""


def _run(arguments: list[str], timeout: float | None = None) -> tuple[int, list[dict[str, Any]], str]:
    """Runs one ``wemute`` CLI command; returns its exit code, JSON lines and stderr."""
    try:
        completed = subprocess.run(
            [*wemute_command(), "--cli", *arguments],
            stdin=subprocess.DEVNULL,  # the server's own stdin carries the protocol
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "WEMUTE_LANGUAGE": "en"},
        )
    except subprocess.TimeoutExpired as exc:
        raise ToolError(f"wemute {arguments[0]} timed out after {exc.timeout:.0f} s") from exc
    lines = []
    for line in completed.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            lines.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return completed.returncode, lines, completed.stderr


def _paths(arguments: dict[str, Any]) -> list[str]:
    paths = arguments.get("paths")
    if isinstance(paths, str):
        paths = [paths]
    if not isinstance(paths, list) or not paths or not all(isinstance(path, str) and path for path in paths):
        raise ToolError("`paths` must be a non-empty list of file or folder paths")
    return [str(Path(path).expanduser()) for path in paths]


def _extract(arguments: dict[str, Any]) -> tuple[str, bool]:
    text_format = arguments.get("format", "md")
    if text_format not in ("md", "txt"):
        raise ToolError("`format` must be md or txt")
    command = ["extract", *_paths(arguments), "--format", "json",
               "--ocr", str(arguments.get("ocr", "auto")),
               "--language", str(arguments.get("language", "auto")),
               "--max-rows", str(int(arguments.get("max_rows", 5000)))]
    if arguments.get("speakers"):
        command.append("--speakers")
    _code, lines, stderr = _run(command)
    parts: list[str] = []
    errors = 0
    for line in lines:
        if line.get("type") == "document":
            body = line.get("markdown", "") if text_format == "md" else line.get("text", "")
            header = f"# {line.get('source', '')}"
            notes = "".join(f"\n> {warning}" for warning in line.get("warnings", []))
            parts.append(f"{header}\n{notes}\n\n{body}".rstrip())
        elif line.get("type") == "error":
            errors += 1
            parts.append(f"# {line.get('source', '')}\n\nCould not read it ({line.get('code', 'failed')}): {line.get('error', '')}")
    if not parts:
        raise ToolError(stderr.strip()[-2000:] or "wemute extract returned nothing")
    text = "\n\n---\n\n".join(parts)
    limit = max(1000, int(arguments.get("max_chars", DEFAULT_MAX_CHARS)))
    if len(text) > limit:
        text = text[:limit] + f"\n\n[Cut at {limit:,} of {len(text):,} characters. Extract fewer files or raise max_chars.]"
    return text, errors == len(parts)


def _convert(arguments: dict[str, Any]) -> tuple[str, bool]:
    command = ["convert", *_paths(arguments)]
    if arguments.get("action"):
        command += ["--action", str(arguments["action"])]
    if arguments.get("out_dir"):
        command += ["--out", str(Path(str(arguments["out_dir"])).expanduser())]
    _code, lines, stderr = _run(command)
    files = [line for line in lines if line.get("type") == "file"]
    result = next((line for line in lines if line.get("type") == "result"), None)
    if result is None:
        raise ToolError(stderr.strip()[-2000:] or "wemute convert returned nothing")
    rows = []
    for item in files:
        if item.get("ok"):
            rows.append(f"✓ {item.get('source')} → {item.get('output')}")
        else:
            rows.append(f"✗ {item.get('source')}: {item.get('error') or 'failed'}")
    summary = f"Converted {result.get('converted', 0)}, failed {result.get('failed', 0)}."
    if result.get("error"):
        summary += f" {result['error']}"
    return "\n".join([summary, *rows]), not result.get("ok")


def _list_actions(arguments: dict[str, Any]) -> tuple[str, bool]:
    _code, lines, stderr = _run(["actions"])
    query = str(arguments.get("query") or "").lower()
    rows = [f"{line['id']}\t{line['title']}" for line in lines
            if line.get("type") == "action" and (not query or query in f"{line['id']} {line['title']}".lower())]
    if not lines:
        raise ToolError(stderr.strip()[-2000:] or "wemute actions returned nothing")
    return "\n".join(rows) if rows else f"No tool matches “{query}”.", False


def _list_models(_arguments: dict[str, Any]) -> tuple[str, bool]:
    _code, lines, stderr = _run(["models", "list"])
    rows = [
        f"{line['id']}\t{'installed' if line.get('installed') else 'not installed'}\t{line.get('name', '')}"
        f"\t{round((line.get('size') or 0) / 1e6)} MB"
        for line in lines if line.get("type") == "model"
    ]
    if not rows:
        raise ToolError(stderr.strip()[-2000:] or "wemute models returned nothing")
    return "\n".join(rows), False


def _install_model(arguments: dict[str, Any]) -> tuple[str, bool]:
    model = str(arguments.get("id") or "")
    if not model:
        raise ToolError("`id` is required (see list_models)")
    _code, lines, stderr = _run(["models", "install", model])
    result = next((line for line in lines if line.get("type") == "result"), None)
    if result is None:
        raise ToolError(stderr.strip()[-2000:] or "wemute models install returned nothing")
    if result.get("ok"):
        return f"Installed {model}.", False
    return f"Could not install {model}: {result.get('error', 'failed')}", True


def _doctor(_arguments: dict[str, Any]) -> tuple[str, bool]:
    _code, lines, _stderr = _run(["doctor"], timeout=120)
    rows = [f"{'✓' if line.get('ok') else '✗'} {line.get('name')}: {line.get('value')}"
            for line in lines if line.get("type") == "check"]
    return "\n".join(rows) or "doctor returned nothing", False


HANDLERS = {
    "extract": _extract,
    "convert": _convert,
    "list_actions": _list_actions,
    "list_models": _list_models,
    "install_model": _install_model,
    "doctor": _doctor,
}


def handle(message: dict[str, Any]) -> dict[str, Any] | None:
    """One JSON-RPC message in, its response out (None for notifications)."""
    method = message.get("method")
    request_id = message.get("id")
    if "id" not in message:
        return None  # notifications/initialized, notifications/cancelled, …

    def reply(result: dict[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def error(code: int, text: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": text}}

    params = message.get("params") or {}
    if method == "initialize":
        requested = params.get("protocolVersion")
        version = requested if requested in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0]
        return reply({
            "protocolVersion": version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "wemute", "title": "Wemute", "version": __version__},
            "instructions": INSTRUCTIONS,
        })
    if method == "ping":
        return reply({})
    if method == "tools/list":
        return reply({"tools": TOOLS})
    if method == "tools/call":
        name = params.get("name")
        handler = HANDLERS.get(name)
        if handler is None:
            return error(-32602, f"Unknown tool: {name}")
        try:
            text, failed = handler(params.get("arguments") or {})
        except ToolError as exc:
            text, failed = str(exc), True
        except Exception as exc:  # noqa: BLE001 - report, keep serving
            text, failed = f"{type(exc).__name__}: {exc}", True
        return reply({"content": [{"type": "text", "text": text}], "isError": failed})
    return error(-32601, f"Method not found: {method}")


def serve(stdin=None, stdout=None) -> int:  # noqa: ANN001
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    for raw in stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            message = json.loads(raw)
        except json.JSONDecodeError:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        else:
            messages = message if isinstance(message, list) else [message]
            responses = [answer for item in messages if isinstance(item, dict) and (answer := handle(item))]
            if not responses:
                continue
            response = responses if isinstance(message, list) else responses[0]
        stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        stdout.flush()
    return 0
