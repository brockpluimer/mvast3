# -*- coding: utf-8 -*-
"""gui_widgets.py logic that doesn't need a window: master-CSV loading and
range checks, pre-flight checks, and remembered settings."""

import os
import sys
import json
import stat

import pytest

import gui_widgets as gw
from config import EXPECTED_DISPLAY_SIZE, BRIGHTNESS_LEVELS_BASE
from conftest import IMG1, IMG2, MASTER_HEADER, write_master

GOOD = [1, 0, 1, 0.1, 10, 8, 7.5]


# --- load_master_csv ---------------------------------------------------------------

def test_valid_csv(tmp_path):
    rows = [[i + 1, 0 if i < 6 else (i - 6) // 6 + 1, i % 6 + 1, BRIGHTNESS_LEVELS_BASE[i % 6], 10, 8, 7.5] for i in range(24)]
    trials, errors = gw.load_master_csv(write_master(tmp_path / "m.csv", rows))
    assert errors == [] and len(trials) == 24
    assert trials[0] == {'trial_number': 1, 'block_number': 0, 'trial_in_block': 1, 'brightness_factor': 0.1,
                         'stimulus_duration': 10.0, 'fixation_duration': 8.0, 'checkerboard_hz': 7.5}


def test_excel_bom_and_spaces_in_header(tmp_path):
    p = tmp_path / "excel.csv"
    p.write_bytes("﻿ trial_number , block_number,trial_in_block, brightness_factor,stimulus_duration,fixation_duration,checkerboard_hz\r\n"
                  "1,0,1,0.1,10,8,7.5\r\n".encode("utf-8"))
    trials, errors = gw.load_master_csv(str(p))
    assert errors == [] and len(trials) == 1


def test_missing_block_columns_are_derived(tmp_path):
    header = ['trial_number', 'brightness_factor', 'stimulus_duration', 'fixation_duration', 'checkerboard_hz']
    rows = [[i + 1, 0.4, 10, 8, 7.5] for i in range(14)]
    trials, errors = gw.load_master_csv(write_master(tmp_path / "m.csv", rows, header))
    assert errors == []
    assert [(t['block_number'], t['trial_in_block']) for t in trials][5:8] == [(0, 6), (1, 1), (1, 2)]
    assert (trials[13]['block_number'], trials[13]['trial_in_block']) == (2, 2)


def test_missing_column(tmp_path):
    header = [h for h in MASTER_HEADER if h != 'checkerboard_hz']
    trials, errors = gw.load_master_csv(write_master(tmp_path / "m.csv", [GOOD[:-1]], header))
    assert trials == [] and "checkerboard_hz" in errors[0]


@pytest.mark.parametrize("col,value,ok", [
    (3, 0.0, False), (3, 0.05, True), (3, 1.0, True), (3, 1.01, False), (3, -0.5, False),
    (4, 0, False), (4, 0.5, True), (4, 300, True), (4, 300.1, False),
    (5, 0, False), (5, 300, True), (5, 301, False),
    (6, 0, True), (6, -0.1, False), (6, 60, True), (6, 60.5, False),
    (3, "nan", False), (4, "inf", False), (6, "abc", False), (0, "1.5", False), (3, "", False),
])
def test_value_ranges(tmp_path, col, value, ok):
    row = GOOD[:]; row[col] = value
    trials, errors = gw.load_master_csv(write_master(tmp_path / "m.csv", [row]))
    assert (errors == []) is ok, errors


def test_errors_report_row_numbers(tmp_path):
    rows = [GOOD, [2, 0, 2, 1.7, 10, 8, 7.5], [3, 0, 3, 0.5, -3, 8, 90]]
    _, errors = gw.load_master_csv(write_master(tmp_path / "m.csv", rows))
    assert len(errors) == 3
    assert errors[0].startswith("Row 3:") and "brightness_factor" in errors[0]
    assert any(e.startswith("Row 4:") and "checkerboard_hz" in e for e in errors)


def test_trial_numbers_must_be_sequential(tmp_path):
    rows = [GOOD, [3, 0, 2, 0.2, 10, 8, 7.5]]
    _, errors = gw.load_master_csv(write_master(tmp_path / "m.csv", rows))
    assert any("trial_number" in e for e in errors)


def test_empty_and_missing_files(tmp_path):
    _, errors = gw.load_master_csv(write_master(tmp_path / "m.csv", []))
    assert errors == ["No trials in CSV."]
    _, errors = gw.load_master_csv(str(tmp_path / "missing.csv"))
    assert errors and "Error reading" in errors[0]
    blank = tmp_path / "blank.csv"; blank.write_text("")
    _, errors = gw.load_master_csv(str(blank))
    assert errors


def test_generated_setup_round_trips(tmp_path):
    """A file written like the setup generator writes it loads cleanly."""
    from data import build_randomized_schedule
    full = BRIGHTNESS_LEVELS_BASE + build_randomized_schedule(3, 16, True)
    rows = [[i + 1, 0 if i < 6 else (i - 6) // 6 + 1, (i % 6) + 1, f"{bf:.2f}", 10.0, 8.0, 7.5] for i, bf in enumerate(full)]
    trials, errors = gw.load_master_csv(write_master(tmp_path / "m.csv", rows))
    assert errors == [] and [t['brightness_factor'] for t in trials] == full


def test_estimate_minutes():
    trials = [{'fixation_duration': 8, 'stimulus_duration': 10}] * 24
    assert gw.estimate_minutes(trials) == pytest.approx(24 * 28 / 60)


# --- pre-flight checks -----------------------------------------------------------------

def disp(size=EXPECTED_DISPLAY_SIZE, rr=60, index=0):
    return {'index': index, 'name': "", 'size': size, 'refresh_hz': rr, 'bounds': None}


def levels(checks): return [c[0] for c in checks]


def test_display_checks():
    assert levels(gw.display_checks(None, [7.5])) == ['warn']
    ok = gw.display_checks(disp(), [7.5, 7.5, 0])
    assert levels(ok) == ['ok', 'ok'] and "exactly 4 frames" in ok[1][1]
    mism = gw.display_checks(disp((1920, 1080)), [7.5])
    assert mism[0][0] == 'warn' and "1920×1080" in mism[0][1]
    assert levels(gw.display_checks(disp(rr=60), [8.0]))[1] == 'warn'
    assert levels(gw.display_checks(disp(rr=None), [7.5]))[1] == 'warn'
    assert len(gw.display_checks(disp(), [7.5, 10, 7.5])) == 3      # one row per distinct rate


def test_folder_check(tmp_path):
    assert gw.folder_check(str(tmp_path))[0] == 'ok'
    assert gw.folder_check(str(tmp_path / "new" / "nested"))[0] == 'ok'   # created later; parent writable


@pytest.mark.skipif(sys.platform.startswith("win") or os.geteuid() == 0, reason="POSIX permissions, non-root")
def test_folder_check_unwritable(tmp_path):
    ro = tmp_path / "ro"; ro.mkdir(); ro.chmod(stat.S_IRUSR | stat.S_IXUSR)
    try:
        assert gw.folder_check(str(ro / "sub"))[0] == 'bad'
    finally:
        ro.chmod(stat.S_IRWXU)


def test_image_checks(tmp_path):
    d = disp()
    assert levels(gw.image_checks(IMG1, IMG2, d)) == ['ok']
    assert levels(gw.image_checks(IMG1, IMG2, disp((1920, 1080)))) == ['warn']
    assert levels(gw.image_checks(IMG1, IMG1, d)) == ['ok', 'warn']           # same file: no flicker
    assert levels(gw.image_checks("", IMG2, d)) == ['bad']
    bad = tmp_path / "bad.png"; bad.write_bytes(b"\x89PNG not really")
    checks = gw.image_checks(str(bad), str(tmp_path / "missing.png"), d)
    assert levels(checks) == ['bad', 'bad'] and "can't be read" in checks[0][1] and "not found" in checks[1][1]
    assert levels(gw.image_checks(IMG1, IMG2, None)) == ['ok']


def test_check_image_reports_size():
    assert gw.check_image(IMG1) == (True, (1600, 1200))


def test_participant_check(tmp_path):
    assert gw.participant_check(str(tmp_path), "P01") is None
    (tmp_path / "data_PP01_20261021_101530.csv").write_text("Run_Status,aborted\nTrials_Completed,9\n")
    level, text = gw.participant_check(str(tmp_path), "P01")
    assert level == 'warn' and "aborted" in text and "9 trials" in text
    assert gw.participant_check(str(tmp_path), "P0") is None                # no prefix matches


# --- settings ---------------------------------------------------------------------------

@pytest.fixture
def settings_file(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    monkeypatch.setattr(gw, "SETTINGS_FILE", str(path))
    return path


def test_settings_round_trip_keeps_other_sections(settings_file):
    assert gw.load_settings("run") == {}
    gw.save_settings("run", {'master_csv': "a.csv", 'display_index': 1})
    gw.save_settings("tonic", {'hz': 7.5})
    assert gw.load_settings("run") == {'master_csv': "a.csv", 'display_index': 1}
    assert gw.load_settings("tonic") == {'hz': 7.5}


def test_corrupt_settings_are_ignored(settings_file):
    settings_file.write_text("{not json")
    assert gw.load_settings("run") == {}
    gw.save_settings("run", {'x': 1})                                     # overwrites the corrupt file
    assert json.loads(settings_file.read_text()) == {'run': {'x': 1}}


def test_unwritable_settings_dont_raise(tmp_path, monkeypatch):
    monkeypatch.setattr(gw, "SETTINGS_FILE", str(tmp_path / "missing_dir" / "s.json"))
    gw.save_settings("run", {'x': 1})                                     # logs, doesn't crash the GUI
    assert gw.load_settings("run") == {}
