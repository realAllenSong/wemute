"""The MCP server speaks JSON-RPC on stdio and runs the CLI for each tool call."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from wemute import __version__
from wemute.mcp_server import TOOLS, handle


def _request(method: str, params: dict | None = None, request_id: int = 1) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}


def test_handshake_lists_every_tool_with_a_schema() -> None:
    init = handle(_request("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}}))["result"]
    assert init["protocolVersion"] == "2025-03-26"
    assert init["serverInfo"] == {"name": "wemute", "title": "Wemute", "version": __version__}
    assert "tools" in init["capabilities"]

    unknown = handle(_request("initialize", {"protocolVersion": "1999-01-01"}))["result"]
    assert unknown["protocolVersion"] == "2025-06-18"

    assert handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    assert handle(_request("ping"))["result"] == {}

    tools = handle(_request("tools/list"))["result"]["tools"]
    assert [tool["name"] for tool in tools] == [
        "extract", "convert", "list_actions", "list_models", "install_model", "doctor",
    ]
    for tool in tools:
        assert tool["description"] and tool["inputSchema"]["type"] == "object"
    assert TOOLS[0]["inputSchema"]["required"] == ["paths"]


def test_bad_calls_are_answered_not_fatal() -> None:
    assert handle(_request("resources/list"))["error"]["code"] == -32601
    assert handle(_request("tools/call", {"name": "nope"}))["error"]["code"] == -32602
    result = handle(_request("tools/call", {"name": "extract", "arguments": {"paths": []}}))["result"]
    assert result["isError"] is True
    assert "paths" in result["content"][0]["text"]


def test_a_real_server_extracts_and_converts(tmp_path: Path) -> None:
    from PIL import Image

    notes = tmp_path / "notes.md"
    notes.write_text("# Q3 notes\n\nRevenue grew 12%.\n", encoding="utf-8")
    photo = tmp_path / "photo.png"
    Image.new("RGB", (40, 30), "navy").save(photo)
    out = tmp_path / "out"

    messages = [
        _request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}}, 1),
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        _request("tools/call", {"name": "extract", "arguments": {"paths": [str(notes), str(tmp_path / "gone.pdf")]}}, 2),
        _request("tools/call", {"name": "convert", "arguments": {
            "paths": [str(photo)], "action": "format:image:JPEG", "out_dir": str(out)}}, 3),
        _request("tools/call", {"name": "list_actions", "arguments": {"query": "pdf"}}, 4),
    ]
    completed = subprocess.run(
        [sys.executable, "-m", "wemute", "--cli", "mcp"],
        input="".join(json.dumps(message) + "\n" for message in messages),
        capture_output=True, text=True, timeout=300,
    )
    replies = {reply["id"]: reply for reply in map(json.loads, completed.stdout.splitlines())}
    assert sorted(replies) == [1, 2, 3, 4]  # stdout carries nothing but protocol

    extracted = replies[2]["result"]
    assert extracted["isError"] is False
    text = extracted["content"][0]["text"]
    assert "Revenue grew 12%." in text
    assert "Could not read it (not_found)" in text

    converted = replies[3]["result"]
    assert converted["isError"] is False, converted
    outputs = list(out.glob("*.jpg"))
    assert len(outputs) == 1
    assert str(outputs[0]) in converted["content"][0]["text"]

    tools = replies[4]["result"]["content"][0]["text"]
    assert "to_pdf\t" in tools


def test_settings_copy_a_setup_that_starts_this_server() -> None:
    from PySide6.QtCore import QCoreApplication

    from wemute.settings_qt import Integrations

    app = QCoreApplication.instance() or QCoreApplication([])
    del app
    integrations = Integrations(thundertalk=Path("/nonexistent/ThunderTalk.app"))
    entry = json.loads(integrations.mcpConfig())["mcpServers"]["wemute"]
    assert entry["args"][-2:] == ["--cli", "mcp"]
    assert Path(entry["command"]).exists()
    assert integrations.mcpClaudeCommand().startswith("claude mcp add wemute -- ")
    assert integrations.mcpClaudeCommand().endswith("--cli mcp")
