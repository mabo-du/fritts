# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.5] - Unreleased

### Fixed
- Fixed an issue where `pip install -e .` overrode the CPU version of PyTorch with the CUDA version on GitHub Actions, leading to standalone binaries exceeding GitHub's 2GB file size limit. Added a constraints file to force pip to honor the pre-installed CPU-only PyTorch wheel.

## [0.1.4] - 2026-06-12

### Fixed
- Changed PyInstaller builds to bundle CPU-only PyTorch to avoid exceeding the 2GB GitHub Release file size limit, which previously caused the release workflow to fail.

## [0.1.3] - 2026-06-12

### Changed
- Renamed PyPI package to `fritts-dendro`.

## [0.1.2] - 2026-06-12

### Fixed
- Replaced deprecated `np.warnings` usage with standard Python `warnings` in the `detrend` and `quality_control` statistics modules. This fixes a fatal `AttributeError` crash encountered when running cross-dating or standardisation on NumPy 1.24 or newer.

## [0.1.1] - 2026-06-12

### Added
- GitHub Actions CI/CD workflows for building, testing, and PyPI publishing.
- Dependabot configuration for dependency updates.
- MIT License file.
- Known Issues section to README.

### Fixed
- NOAA ITRDB API responses dropping connections by defaulting search limits to 30.
- Proper error handling for HTTPError responses from NOAA API.
- Fixed UI bug where the ITRDB dialog closed prematurely upon pressing the Enter key.
- Pinned `pyqtgraph<0.14` to prevent `autoRangeEnabled` API removal crashes.
- Fixed missing `DetrendCommand` import in the UI.
- Corrected internal `CommandStack` push logic typos.
