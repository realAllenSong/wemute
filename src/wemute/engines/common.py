from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path


class ConversionError(RuntimeError):
    """A failure with a message that can be shown to the user as is."""


MESSAGES = {
    "zh": {
        "office_failed": "LibreOffice 无法转换这个文件",
        "office_timeout": "LibreOffice 处理超时（{seconds} 秒）",
        "ebook_failed": "Calibre 无法转换这本电子书",
        "ebook_drm": "这本电子书有 DRM 保护，无法转换",
        "pandoc_failed": "Pandoc 无法转换这个文件",
        "tool_timeout": "处理超时（{seconds} 秒）",
        "tool_missing": "缺少转换组件：{name}",
        "encrypted_pdf": "这个 PDF 有密码保护",
        "encrypted_archive": "压缩包有密码保护，暂不支持",
        "archive_failed": "无法解压这个压缩包",
        "empty_archive": "压缩包是空的",
        "no_table": "JSON 里没有可以转成表格的数据",
        "bad_json": "JSON 格式有误：{detail}",
        "bad_font": "无法读取这个字体文件",
        "bad_svg": "无法读取这个 SVG",
        "bad_pdf": "无法读取这个 PDF",
        "bad_image": "无法读取图片：{name}",
        "no_pages": "没有生成任何页面",
        "stage_starting_office": "首次启动…",
        "stage_converting": "转换中…",
        "stage_rendering": "渲染页面…",
        "stage_saving": "保存…",
        "stage_reading": "读取中…",
        "stage_extracting": "解压中…",
        "stage_packing": "打包中…",
        "stage_compressing": "压缩中…",
        "stage_recognizing": "识别文字…",
        "stage_finding_edges": "寻找文档边缘…",
        "stage_analyzing": "分析画面…",
        "stage_enhancing": "增强中…",
        "stage_comparing": "比较照片…",
        "no_text": "没有识别到文字",
        "no_document": "没有找到文档边缘",
        "no_faces": "没有找到人脸",
        "no_person": "没有找到人物",
        "no_codes": "没有找到二维码或条码",
        "no_horizon": "没有发现倾斜的地平线，不需要扶正",
        "already_level": "照片已经是水平的（只差 {angle}°），不需要扶正",
        "vision_missing": "这台 Mac 的系统版本不支持这个功能",
        "triage_found": "找到 {duplicates} 张重复、{blurry} 张模糊的照片",
        "triage_none": "没有发现重复或模糊的照片",
        "stage_loading_speech": "准备语音模型…",
        "stage_transcribing": "识别语音…",
        "stage_speaking": "合成语音…",
        "speech_missing": "需要安装支持字幕和朗读的 ThunderTalk",
        "speech_failed": "ThunderTalk 没能完成",
        "speech_none": "没有听到说话的声音",
        "speech_no_model": "ThunderTalk 还没有可用的语音识别模型，请在 ThunderTalk 里下载一个",
        "speech_no_voice": "ThunderTalk 还没有可用的朗读声音",
        "speech_permission": "没有语音识别权限：请在 系统设置 › 隐私与安全性 › 语音识别 里允许 ThunderTalk",
        "speech_locale": "这台 Mac 还没有安装这种语言的语音识别",
        "speech_decode": "无法读取这个文件里的声音",
        "speech_no_text": "文件里没有可以朗读的文字",
        "speech_unreadable": "只能朗读 TXT、Markdown、HTML、Word（.docx）和 PDF 里的文字",
    },
    "en": {
        "office_failed": "LibreOffice could not convert this file",
        "office_timeout": "LibreOffice timed out after {seconds} s",
        "ebook_failed": "Calibre could not convert this e-book",
        "ebook_drm": "This e-book is DRM-protected and cannot be converted",
        "pandoc_failed": "Pandoc could not convert this file",
        "tool_timeout": "Timed out after {seconds} s",
        "tool_missing": "Missing component: {name}",
        "encrypted_pdf": "This PDF is password-protected",
        "encrypted_archive": "Password-protected archives are not supported yet",
        "archive_failed": "This archive could not be extracted",
        "empty_archive": "The archive is empty",
        "no_table": "The JSON has no rows that fit in a table",
        "bad_json": "Invalid JSON: {detail}",
        "bad_font": "This font file could not be read",
        "bad_svg": "This SVG could not be read",
        "bad_pdf": "This PDF could not be read",
        "bad_image": "Could not read image: {name}",
        "no_pages": "No pages were produced",
        "stage_starting_office": "First start…",
        "stage_converting": "Converting…",
        "stage_rendering": "Rendering pages…",
        "stage_saving": "Saving…",
        "stage_reading": "Reading…",
        "stage_extracting": "Extracting…",
        "stage_packing": "Packing…",
        "stage_compressing": "Compressing…",
        "stage_recognizing": "Recognizing text…",
        "stage_finding_edges": "Finding the page edges…",
        "stage_analyzing": "Analyzing…",
        "stage_enhancing": "Enhancing…",
        "stage_comparing": "Comparing photos…",
        "no_text": "No text was found",
        "no_document": "No document edges were found",
        "no_faces": "No faces were found",
        "no_person": "No person was found",
        "no_codes": "No QR code or barcode was found",
        "no_horizon": "No tilted horizon was found, nothing to straighten",
        "already_level": "Already level (off by {angle}°), nothing to straighten",
        "vision_missing": "This feature needs a newer version of macOS",
        "triage_found": "Found {duplicates} duplicates and {blurry} blurry photos",
        "triage_none": "No duplicates or blurry photos found",
        "stage_loading_speech": "Preparing the speech model…",
        "stage_transcribing": "Listening…",
        "stage_speaking": "Reading aloud…",
        "speech_missing": "Needs a ThunderTalk with subtitles and read-aloud",
        "speech_failed": "ThunderTalk could not finish",
        "speech_none": "No speech was heard",
        "speech_no_model": "ThunderTalk has no speech recognition model yet; download one in ThunderTalk",
        "speech_no_voice": "ThunderTalk has no voice to read with yet",
        "speech_permission": "Speech recognition is not allowed: turn on ThunderTalk in System Settings › Privacy & Security › Speech Recognition",
        "speech_locale": "This Mac has no speech recognition for this language yet",
        "speech_decode": "Could not read the sound in this file",
        "speech_no_text": "There is no text to read in this file",
        "speech_unreadable": "Only text in TXT, Markdown, HTML, Word (.docx) and PDF files can be read aloud",
    },
}


class Reporter:
    """Writes the line protocol the controller reads from a worker's stdout."""

    def __init__(self, language: str = "en", stream=None) -> None:  # noqa: ANN001
        self.language = language if language in MESSAGES else "en"
        self.stream = stream or sys.stdout
        self._last = -1.0

    def text(self, key: str, **values: object) -> str:
        return MESSAGES[self.language].get(key, key).format(**values)

    def error(self, key: str, **values: object) -> ConversionError:
        return ConversionError(self.text(key, **values))

    def _emit(self, line: str) -> None:
        try:
            self.stream.write(line + "\n")
            self.stream.flush()
        except (OSError, ValueError):
            pass

    def progress(self, value: float) -> None:
        value = max(0.0, min(1.0, value))
        if value - self._last >= 0.005 or value >= 1.0:
            self._last = value
            self._emit(f"wemute_progress={value:.4f}")

    def indeterminate(self, active: bool = True) -> None:
        self._emit(f"wemute_indeterminate={1 if active else 0}")

    def stage(self, key: str) -> None:
        self._emit("wemute_stage=" + self.text(key))

    def note(self, key: str, **values: object) -> None:
        """A one-line result summary shown in the Done headline."""
        self._emit("wemute_note=" + self.text(key, **values))


# The child currently running, killed with its process group on SIGTERM.
_ACTIVE: list[subprocess.Popen] = []


def _terminate_children(*_args: object) -> None:
    for process in list(_ACTIVE):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except OSError:
            pass
    raise SystemExit(143)


def install_signal_handlers() -> None:
    signal.signal(signal.SIGTERM, _terminate_children)
    signal.signal(signal.SIGINT, _terminate_children)


def run_tool(
    command: Sequence[str],
    *,
    timeout: float,
    timeout_message: str,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    on_line=None,  # noqa: ANN001 - optional callable(str)
) -> subprocess.CompletedProcess[str]:
    """Run a helper program in its own process group so cancel kills all of it."""
    process = subprocess.Popen(
        list(command),
        cwd=str(cwd) if cwd else None,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        start_new_session=True,
    )
    _ACTIVE.append(process)
    output: list[str] = []
    import threading

    def pump() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            output.append(line)
            if on_line:
                try:
                    on_line(line.rstrip("\n"))
                except Exception:  # noqa: BLE001 - progress parsing must not fail a job
                    pass

    reader = threading.Thread(target=pump, daemon=True)
    reader.start()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except OSError:
            pass
        process.wait()
        raise ConversionError(timeout_message) from None
    finally:
        if process in _ACTIVE:
            _ACTIVE.remove(process)
    reader.join(timeout=2)
    return subprocess.CompletedProcess(list(command), process.returncode, "".join(output), "")


def scratch_dir(prefix: str) -> Path:
    from wemute.paths import CACHE_ROOT

    root = CACHE_ROOT / "work"
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=str(root)))


def remove_tree(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


def last_line(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else ""
