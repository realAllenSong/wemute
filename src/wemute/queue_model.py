from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import QAbstractListModel, QByteArray, QLocale, QModelIndex, Qt

from wemute.capabilities import options_for
from wemute.domain import JobRecord, JobStatus, MediaKind
from wemute.presentation import (
    GROUP_LABELS,
    GROUP_ORDER,
    metadata_line,
    output_summary,
    status_title,
    thumbnail_url,
)


class QueueModel(QAbstractListModel):
    RowTypeRole = Qt.UserRole + 1
    JobIdRole = Qt.UserRole + 2
    GroupLabelRole = Qt.UserRole + 3
    SourceNameRole = Qt.UserRole + 4
    SourcePathRole = Qt.UserRole + 5
    MetadataRole = Qt.UserRole + 6
    ThumbnailRole = Qt.UserRole + 7
    TargetFormatRole = Qt.UserRole + 8
    TargetOptionsRole = Qt.UserRole + 9
    StatusRole = Qt.UserRole + 10
    StatusTitleRole = Qt.UserRole + 11
    StatusSubtitleRole = Qt.UserRole + 12
    ProgressRole = Qt.UserRole + 13
    SelectedRole = Qt.UserRole + 14
    CanConvertRole = Qt.UserRole + 15
    MediaKindRole = Qt.UserRole + 16
    GroupItemCountRole = Qt.UserRole + 17

    def __init__(self, jobs: Iterable[JobRecord] | None = None) -> None:
        super().__init__()
        self._jobs: list[JobRecord] = list(jobs or [])
        self._language = "zh" if QLocale.system().name().lower().startswith("zh") else "en"
        self._rows: list[tuple[str, MediaKind | JobRecord]] = []
        self._rebuild_rows()

    @property
    def jobs(self) -> list[JobRecord]:
        return self._jobs

    def roleNames(self) -> dict[int, QByteArray]:  # noqa: N802 - Qt API
        return {
            self.RowTypeRole: QByteArray(b"rowType"),
            self.JobIdRole: QByteArray(b"jobId"),
            self.GroupLabelRole: QByteArray(b"groupLabel"),
            self.SourceNameRole: QByteArray(b"sourceName"),
            self.SourcePathRole: QByteArray(b"sourcePath"),
            self.MetadataRole: QByteArray(b"metadata"),
            self.ThumbnailRole: QByteArray(b"thumbnailUrl"),
            self.TargetFormatRole: QByteArray(b"targetFormat"),
            self.TargetOptionsRole: QByteArray(b"targetOptions"),
            self.StatusRole: QByteArray(b"jobStatus"),
            self.StatusTitleRole: QByteArray(b"statusTitle"),
            self.StatusSubtitleRole: QByteArray(b"statusSubtitle"),
            self.ProgressRole: QByteArray(b"jobProgress"),
            self.SelectedRole: QByteArray(b"rowSelected"),
            self.CanConvertRole: QByteArray(b"canConvert"),
            self.MediaKindRole: QByteArray(b"mediaKind"),
            self.GroupItemCountRole: QByteArray(b"groupItemCount"),
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):  # noqa: ANN201
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        row_type, payload = self._rows[index.row()]
        if role == self.RowTypeRole:
            return row_type
        if row_type == "header":
            kind = payload
            assert isinstance(kind, MediaKind)
            group_jobs = [job for job in self._jobs if job.source.kind == kind]
            group_targets = {job.target_format for job in group_jobs}
            if role == self.GroupLabelRole:
                return GROUP_LABELS[self._language][kind]
            header_values = {
                self.TargetFormatRole: next(iter(group_targets)) if len(group_targets) == 1 else "",
                self.TargetOptionsRole: options_for(kind),
                self.CanConvertRole: bool(options_for(kind)),
                self.MediaKindRole: kind.value,
                self.GroupItemCountRole: len(group_jobs),
            }
            return header_values.get(role)

        job = payload
        assert isinstance(job, JobRecord)
        values = {
            self.JobIdRole: job.id,
            self.SourceNameRole: job.source.name,
            self.SourcePathRole: job.source.path,
            self.MetadataRole: metadata_line(job.source),
            self.ThumbnailRole: thumbnail_url(job.source),
            self.TargetFormatRole: job.target_format,
            self.TargetOptionsRole: options_for(job.source.kind),
            self.StatusRole: job.status.value,
            self.StatusTitleRole: status_title(job.status, self._language),
            self.StatusSubtitleRole: output_summary(job, self._language),
            self.ProgressRole: job.progress,
            self.SelectedRole: job.selected,
            self.CanConvertRole: bool(options_for(job.source.kind)),
            self.MediaKindRole: job.source.kind.value,
            self.GroupItemCountRole: 0,
        }
        return values.get(role)

    def replace(self, jobs: Iterable[JobRecord]) -> None:
        self.beginResetModel()
        self._jobs = list(jobs)
        self._rebuild_rows()
        self.endResetModel()

    def refresh(self) -> None:
        self.beginResetModel()
        self._rebuild_rows()
        self.endResetModel()

    def find(self, job_id: str) -> JobRecord | None:
        return next((job for job in self._jobs if job.id == job_id), None)

    def _rebuild_rows(self) -> None:
        grouped: dict[MediaKind, list[JobRecord]] = {}
        for job in self._jobs:
            grouped.setdefault(job.source.kind, []).append(job)
        self._rows = []
        for kind in sorted(grouped, key=GROUP_ORDER.get):
            self._rows.append(("header", kind))
            self._rows.extend(("job", job) for job in grouped[kind])
