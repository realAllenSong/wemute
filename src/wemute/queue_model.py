from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import QAbstractListModel, QByteArray, QLocale, QModelIndex, Qt

from wemute.capabilities import display_job_choice, options_for
from wemute.domain import JobRecord, JobStatus, MediaKind, OperationKind
from wemute.presentation import (
    GROUP_LABELS,
    GROUP_ORDER,
    metadata_line,
    output_summary,
    result_delta,
    result_size,
    short_duration,
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
    OutputPathRole = Qt.UserRole + 18
    LastInGroupRole = Qt.UserRole + 19
    SourceFormatRole = Qt.UserRole + 20
    ResultSizeRole = Qt.UserRole + 21
    ResultDeltaRole = Qt.UserRole + 22
    ErrorTextRole = Qt.UserRole + 23
    CardIndexRole = Qt.UserRole + 24
    DurationLabelRole = Qt.UserRole + 25
    StageRole = Qt.UserRole + 26
    IndeterminateRole = Qt.UserRole + 27
    StartedAtRole = Qt.UserRole + 28
    WaitingRole = Qt.UserRole + 29

    def __init__(self, jobs: Iterable[JobRecord] | None = None) -> None:
        super().__init__()
        self._jobs: list[JobRecord] = list(jobs or [])
        self._language = "zh" if QLocale.system().name().lower().startswith("zh") else "en"
        self._enabled_ai_actions: set[OperationKind] = set()
        self._rows: list[tuple[str, MediaKind | JobRecord]] = []
        self._card_index: dict[str, int] = {}
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
            self.OutputPathRole: QByteArray(b"outputPath"),
            self.LastInGroupRole: QByteArray(b"lastInGroup"),
            self.SourceFormatRole: QByteArray(b"sourceFormat"),
            self.ResultSizeRole: QByteArray(b"resultSize"),
            self.ResultDeltaRole: QByteArray(b"resultDelta"),
            self.ErrorTextRole: QByteArray(b"errorText"),
            self.CardIndexRole: QByteArray(b"cardIndex"),
            self.DurationLabelRole: QByteArray(b"durationLabel"),
            self.StageRole: QByteArray(b"stage"),
            self.IndeterminateRole: QByteArray(b"indeterminate"),
            self.StartedAtRole: QByteArray(b"startedAt"),
            self.WaitingRole: QByteArray(b"waiting"),
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):  # noqa: ANN201
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        row_type, payload = self._rows[index.row()]
        if role == self.RowTypeRole:
            return row_type
        if role == self.LastInGroupRole:
            following = index.row() + 1
            return following >= len(self._rows) or self._rows[following][0] == "header"
        if row_type == "header":
            kind = payload
            assert isinstance(kind, MediaKind)
            group_jobs = [job for job in self._jobs if job.source.kind == kind]
            group_targets = {display_job_choice(job) for job in group_jobs}
            if role == self.GroupLabelRole:
                return GROUP_LABELS[self._language][kind]
            header_values = {
                self.TargetFormatRole: next(iter(group_targets)) if len(group_targets) == 1 else "",
                self.TargetOptionsRole: options_for(kind, self._enabled_ai_actions),
                self.CanConvertRole: bool(options_for(kind, self._enabled_ai_actions)),
                self.MediaKindRole: kind.value,
                self.GroupItemCountRole: len(group_jobs),
                self.CardIndexRole: -1,
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
            self.TargetFormatRole: display_job_choice(job),
            self.TargetOptionsRole: options_for(job.source.kind, self._enabled_ai_actions),
            self.StatusRole: job.status.value,
            self.StatusTitleRole: status_title(job.status, self._language),
            self.StatusSubtitleRole: output_summary(job, self._language),
            self.ProgressRole: job.progress,
            self.SelectedRole: job.selected,
            self.CanConvertRole: bool(options_for(job.source.kind, self._enabled_ai_actions)),
            self.MediaKindRole: job.source.kind.value,
            self.GroupItemCountRole: 0,
            self.OutputPathRole: job.output_path or "",
            self.SourceFormatRole: job.source.source_format,
            self.ResultSizeRole: result_size(job),
            self.ResultDeltaRole: result_delta(job),
            self.ErrorTextRole: job.error or "",
            self.CardIndexRole: self._card_index.get(job.id, 0),
            self.DurationLabelRole: short_duration(job.source.duration),
            self.StageRole: job.stage,
            self.IndeterminateRole: job.indeterminate,
            self.StartedAtRole: job.started_at,
            self.WaitingRole: bool(job.waiting_component),
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

    def refresh_job(self, job: JobRecord) -> None:
        """Update one row in place so delegates, open menus and scroll position survive."""
        for row, (row_type, payload) in enumerate(self._rows):
            if row_type == "job" and payload is job:
                index = self.index(row)
                self.dataChanged.emit(index, index)
                return

    def set_language(self, language: str) -> None:
        if language != self._language:
            self._language = language
            self.refresh()

    @property
    def language(self) -> str:
        return self._language

    def find(self, job_id: str) -> JobRecord | None:
        return next((job for job in self._jobs if job.id == job_id), None)

    def set_enabled_ai_actions(self, actions: set[OperationKind]) -> None:
        if actions == self._enabled_ai_actions:
            return
        self._enabled_ai_actions = set(actions)
        self.refresh()

    @property
    def enabled_ai_actions(self) -> set[OperationKind]:
        return set(self._enabled_ai_actions)

    def _rebuild_rows(self) -> None:
        grouped: dict[MediaKind, list[JobRecord]] = {}
        for job in self._jobs:
            grouped.setdefault(job.source.kind, []).append(job)
        self._rows = []
        for kind in sorted(grouped, key=GROUP_ORDER.get):
            self._rows.append(("header", kind))
            self._rows.extend(("job", job) for job in grouped[kind])
        # Position among file cards only, so tilts stay stable across group headers.
        self._card_index = {
            payload.id: index
            for index, (_, payload) in enumerate(row for row in self._rows if row[0] == "job")
            if isinstance(payload, JobRecord)
        }
