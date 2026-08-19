"""Collect the lazily imported Apple Silicon audio separation runtime."""

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)


_PACKAGES = ("demucs_mlx", "mlx", "mlx_audio_io", "mlx_spectro")

hiddenimports = []
datas = []
binaries = []
for package in _PACKAGES:
    hiddenimports += collect_submodules(package)
    datas += collect_data_files(package, include_py_files=False)
    binaries += collect_dynamic_libs(package)
