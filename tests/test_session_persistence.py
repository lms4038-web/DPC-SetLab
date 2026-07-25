from pathlib import Path

import pandas as pd

from session_persistence import load_snapshot, new_session_id, restore_snapshot, save_snapshot


def test_snapshot_restores_workflow_data(tmp_path: Path):
    session_id = new_session_id()
    source = {
        "workspace_entered": True,
        "wizard_target_tab": "edit",
        "raw_collection": pd.DataFrame([{"title": "A", "artist": "DJ"}]),
        "transient_widget_value": "do not persist",
    }
    save_snapshot(session_id, source, root=tmp_path)
    restored = load_snapshot(session_id, root=tmp_path)
    assert restored["workspace_entered"] is True
    assert restored["wizard_target_tab"] == "edit"
    assert restored["raw_collection"].iloc[0]["title"] == "A"
    assert "transient_widget_value" not in restored


def test_restore_does_not_overwrite_live_state(tmp_path: Path):
    session_id = new_session_id()
    save_snapshot(session_id, {"wizard_target_tab": "library"}, root=tmp_path)
    live = {"wizard_target_tab": "generate"}
    assert restore_snapshot(session_id, live, root=tmp_path)
    assert live["wizard_target_tab"] == "generate"
