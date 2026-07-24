# DPC SetLab

**AI-assisted DJ workspace for planning, analyzing, and optimizing live DJ sets.**

DPC SetLab helps DJs analyze Rekordbox playlists, build performance-aware set plans, and understand where each track should be used—without taking creative control away from the DJ.

> DPC SetLab is not an AI that replaces the DJ. It is an AI workspace that helps DJs prepare better sets faster while keeping the DJ in control.

[한국어 안내](README_KR.md) · [Roadmap](ROADMAP.md) · [Changelog](CHANGELOG.md)

## Current version

**v2.3.2 — Used Segment Display**

- Rekordbox XML playlist selection
- Playlist Intelligence and health analysis
- AI Performance Planner
- Planned play duration and transition timing
- Track usage range display such as `00:32 → 01:58`
- Core playback and transition segments
- Whole-set timeline positions
- CSV export with readable timestamps and raw seconds

## Quick start

### Windows

Run:

```text
START_WINDOWS.bat
```

### macOS

Run:

```text
START_DPC_SET_BUILDER.command
```

Alternatively, install dependencies and launch manually:

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Tests

```bash
pytest
```

## Project status

DPC SetLab is under active development. The next infrastructure milestone is GitHub Releases-based update delivery, followed by an in-app update checker.
