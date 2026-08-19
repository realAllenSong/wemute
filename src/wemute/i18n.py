from __future__ import annotations

from PySide6.QtCore import Property, QLocale, QObject, Signal, Slot


TRANSLATIONS = {
    "en": {
        "files": "{count} Files",
        "file": "{count} File",
        "add_files": "Add Files",
        "same_folder": "Same Folder",
        "convert_all": "Convert All",
        "drop_anything": "Drop anything",
        "drop_hint": "Images, audio, and video stay on this Mac.",
        "choose_files": "Choose Files",
        "clear_completed": "Clear Completed",
        "clear_all": "Clear All",
        "retry_failed": "Retry Failed",
        "cancel": "Cancel",
        "reveal": "Show in Finder",
        "pause_after_current": "Pause After Current",
        "engine_missing": "FFmpeg is required for conversion.",
        "all_to": "All → ",
        "custom": "Custom",
        "image_options": "Image Options",
        "resize": "Resize",
        "quality": "Quality",
        "corners": "Corners",
        "original_size": "Original size",
        "half_size": "50%",
        "long_edge_2048": "Long edge 2048 px",
        "long_edge_1080": "Long edge 1080 px",
        "smaller": "Smaller",
        "balanced": "Balanced",
        "best_quality": "Best quality",
        "none": "None",
        "soft_corners": "24 px",
        "round_corners": "64 px",
    },
    "zh": {
        "files": "{count} 个文件",
        "file": "{count} 个文件",
        "add_files": "添加文件",
        "same_folder": "原文件夹",
        "convert_all": "全部转换",
        "drop_anything": "拖入任何文件",
        "drop_hint": "图片、音频和视频始终留在这台 Mac 上。",
        "choose_files": "选择文件",
        "clear_completed": "清除已完成",
        "clear_all": "清除全部",
        "retry_failed": "重试失败任务",
        "cancel": "取消",
        "reveal": "在访达中显示",
        "pause_after_current": "完成当前任务后暂停",
        "engine_missing": "转换需要 FFmpeg。",
        "all_to": "全部 → ",
        "custom": "各自设置",
        "image_options": "图片选项",
        "resize": "尺寸",
        "quality": "质量",
        "corners": "圆角",
        "original_size": "原始尺寸",
        "half_size": "缩小至 50%",
        "long_edge_2048": "长边 2048 像素",
        "long_edge_1080": "长边 1080 像素",
        "smaller": "更小",
        "balanced": "平衡",
        "best_quality": "最佳质量",
        "none": "无",
        "soft_corners": "24 像素",
        "round_corners": "64 像素",
    },
}


class I18n(QObject):
    languageChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        system = QLocale.system().name().lower()
        self._language = "zh" if system.startswith("zh") else "en"

    @Property(str, notify=languageChanged)
    def language(self) -> str:
        return self._language

    @Slot(str, result=str)
    def t(self, key: str) -> str:
        return TRANSLATIONS[self._language].get(key, key)

    @Slot(str, int, result=str)
    def count(self, key: str, value: int) -> str:
        selected = "file" if value == 1 else key
        return TRANSLATIONS[self._language].get(selected, key).format(count=value)
