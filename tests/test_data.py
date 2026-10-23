# -*- coding: utf-8 -*-
"""data.py: output files (including the additive-only rule checked against
the v1 code from git), write durability and failure, run-status helpers, and
the trial-order generator."""

import os
import hashlib
import importlib.util
import subprocess
from datetime import datetime

import pytest

import data
from config import BRIGHTNESS_LEVELS_BASE, BRIGHT_THRESHOLD, CANONICAL_ORDER_SEED, TonicRunConfig
from conftest import REPO, IMG1, IMG2, write_master, read_rows

V1_COMMIT = "ee205e4"

TRIAL = {'trial_number': 3, 'block_number': 1, 'trial_in_block': 2, 'brightness_factor': 0.6,
         'stimulus_duration': 10.0, 'fixation_duration': 8.0, 'checkerboard_hz': 7.5}


@pytest.fixture
def master(tmp_path):
    return write_master(tmp_path / "Study1_master_trials.csv", [[1, 0, 1, 0.1, 10, 8, 7.5]])


@pytest.fixture
def v1data(tmp_path):
    """data.py as shipped in v1.1 (commit ee205e4), loaded as a module."""
    try:
        src = subprocess.run(["git", "-C", REPO, "show", f"{V1_COMMIT}:data.py"],
                             capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("v1 source not available from git")
    path = tmp_path / "v1_data.py"; path.write_text(src)
    spec = importlib.util.spec_from_file_location("v1_data", path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def table_start(rows):
    return next(i for i, r in enumerate(rows) if r and r[0] == 'Trial_Number_Overall')


# --- Additive-only rule vs v1 ----------------------------------------------------

def test_standard_file_is_additive_over_v1(tmp_path, master, v1data):
    d1, d2 = tmp_path / "v1", tmp_path / "v2"
    h1 = v1data.ParticipantDataHandler(str(d1), "P01", master, IMG1, IMG2)
    h1.save_trial_response(TRIAL, 40, 55); h1.close()
    h2 = data.ParticipantDataHandler(str(d2), "P01", master, IMG1, IMG2, trials_expected=1)
    h2.save_trial_response(TRIAL, 40, 55); h2.status = "completed"; h2.close()
    r1 = read_rows(next(d1.glob("*.csv"))); r2 = read_rows(next(d2.glob("*.csv")))
    t1, t2 = table_start(r1), table_start(r2)

    # v1 header rows keep their names, order and leading position
    v1_head = [r[0] for r in r1[:t1] if r]
    assert [r[0] for r in r2[:len(v1_head)]] == v1_head
    for a, b in zip(r1[:len(v1_head)], r2[:len(v1_head)]):
        if a[0] != 'Timestamp_Start_Run': assert a == b
    # the v1 trial columns are the first columns, unchanged
    assert r2[t2][:len(r1[t1])] == r1[t1]
    # trial values in v1 columns are identical (apart from the response timestamp)
    assert r2[t2 + 1][:9] == r1[t1 + 1][:9]
    # last row is still Timestamp_End_Run
    assert r1[-1][0] == r2[-1][0] == 'Timestamp_End_Run'
    # documented offset: the table moved down by exactly the number of new header rows
    assert t2 - t1 == 11


def test_summary_file_is_additive_over_v1(tmp_path, v1data):
    s1 = v1data.ParticipantScoreHandler(str(tmp_path / "v1"), "P01"); os.makedirs(tmp_path / "v1")
    s2 = data.ParticipantScoreHandler(str(tmp_path / "v2"), "P01"); os.makedirs(tmp_path / "v2")
    for s in (s1, s2): s.add_ratings(30, 70); s.add_ratings(50, 90)
    s1.save_final_scores(); s2.save_final_scores("completed")
    r1 = read_rows(next((tmp_path / "v1").glob("*.csv"))); r2 = read_rows(next((tmp_path / "v2").glob("*.csv")))
    no_ts = lambda rows: [r for r in rows if r[:1] != ['Timestamp_Summary']]
    assert no_ts(r2[:len(r1)]) == no_ts(r1)          # every v1 row, same place, same value
    assert r2[-1] == ['Run_Status', 'completed']


def test_tonic_file_is_additive_over_v1(tmp_path, v1data):
    cfg = tonic_config(tmp_path)
    trig_wall, trig_perf = datetime(2026, 10, 23, 9, 0, 0), 500.0
    v1h = v1data.TonicDataHandler(cfg); v1h.filename = str(tmp_path / "v1.csv")
    v1h.save(trig_wall, trig_perf, 860.0, "completed")
    v2h = data.TonicDataHandler(cfg); v2h.filename = str(tmp_path / "v2.csv")
    v2h.save(trig_wall, trig_perf, 860.0, "completed", flip_stats={'Stim_Onset_s': "0.0170", 'N_Flips': 5401})
    r1, r2 = read_rows(tmp_path / "v1.csv"), read_rows(tmp_path / "v2.csv")
    blank1, blank2 = r1.index([]), r2.index([])
    assert [r[0] for r in r2[:blank1]] == [r[0] for r in r1[:blank1]]      # v1 header rows are a prefix
    v1_events = [r[0] for r in r1[blank1 + 1:]]
    assert [r[0] for r in r2[blank2 + 1:blank2 + 1 + len(v1_events)]] == v1_events   # event rows too


# --- ParticipantDataHandler -----------------------------------------------------------

def test_header_rows_and_values(tmp_path, master):
    info = {'size': (1600, 1200), 'refresh_hz_os': 60, 'display_index': 1,
            'refresh_hz_measured': 59.94, 'vsync': True}
    h = data.ParticipantDataHandler(str(tmp_path), "P01", master, IMG1, IMG2, trials_expected=24,
                                    display_info=info, display_check="OK 1600x1200")
    h.close()
    rows = dict((r[0], r[1]) for r in read_rows(h.filename) if len(r) == 2)
    assert rows['Master_CSV_Path'] == os.path.abspath(master)
    assert rows['Master_CSV_SHA256'] == hashlib.sha256(open(master, 'rb').read()).hexdigest()
    assert rows['Trials_Expected'] == "24"
    assert rows['Display_Size'] == "1600x1200" and rows['Display_Refresh_Hz_OS'] == "60.00"
    assert rows['Display_Check'] == "OK 1600x1200" and rows['Display_Index'] == "1"
    assert rows['Display_Refresh_Hz_Measured'] == "59.94" and rows['Vsync'] == "yes"
    assert rows['Image1_SHA256'] == hashlib.sha256(open(IMG1, 'rb').read()).hexdigest()
    assert rows['Experiment_ID'] == "Study1"
    order = [r[0] for r in read_rows(h.filename) if r]
    spec = ['Image2_File', 'Master_CSV_Path', 'Master_CSV_SHA256', 'Trials_Expected',
            'Display_Size', 'Display_Refresh_Hz_OS', 'Display_Check']
    i = order.index('Image2_File'); assert order[i:i + len(spec)] == spec   # v2 spec order


def test_trial_row_timing_columns(tmp_path, master):
    h = data.ParticipantDataHandler(str(tmp_path), "P01", master, IMG1, IMG2)
    timing = {c: f"v{i}" for i, c in enumerate(data.TIMING_COLUMNS)}
    h.save_trial_response(TRIAL, 12.0, 88.9, timing, focus_events=2); h.close()
    rows = read_rows(h.filename); t = table_start(rows)
    header, row = rows[t], rows[t + 1]
    assert header == data.TRIAL_COLUMNS + data.TIMING_COLUMNS + data.EXTRA_TRIAL_COLUMNS
    assert row[3] == "0.60" and row[7] == "12" and row[8] == "88"
    assert row[10:19] == [f"v{i}" for i in range(9)] and row[19] == "2"


def test_footer_and_status(tmp_path, master):
    h = data.ParticipantDataHandler(str(tmp_path), "P01", master, IMG1, IMG2)
    for _ in range(3): h.save_trial_response(TRIAL, 1, 2)
    h.status = "aborted"; h.close()
    rows = read_rows(h.filename)
    assert rows[-3] == ['Run_Status', 'aborted'] and rows[-2] == ['Trials_Completed', '3']
    assert rows[-1][0] == 'Timestamp_End_Run'
    h.close()                                                   # idempotent
    assert read_rows(h.filename) == rows


def test_default_status_is_error(tmp_path, master):
    h = data.ParticipantDataHandler(str(tmp_path), "P01", master, IMG1, IMG2); h.close()
    assert ['Run_Status', 'error'] in read_rows(h.filename)


def test_every_row_is_fsynced(tmp_path, master, monkeypatch):
    calls = []
    real = os.fsync
    monkeypatch.setattr(data.os, "fsync", lambda fd: (calls.append(fd), real(fd)))
    h = data.ParticipantDataHandler(str(tmp_path), "P01", master, IMG1, IMG2)
    n0 = len(calls)
    h.save_trial_response(TRIAL, 1, 2); h.save_trial_response(TRIAL, 1, 2)
    assert n0 >= 1 and len(calls) == n0 + 2
    h.close()


def test_write_failure_raises_and_is_not_counted(tmp_path, master, monkeypatch):
    h = data.ParticipantDataHandler(str(tmp_path), "P01", master, IMG1, IMG2)
    h.save_trial_response(TRIAL, 1, 2)
    def boom(fd): raise OSError(5, "Input/output error")
    monkeypatch.setattr(data.os, "fsync", boom)
    with pytest.raises(OSError):
        h.save_trial_response(TRIAL, 1, 2)
    assert h.trials_completed == 1
    monkeypatch.undo(); h.close()


def test_write_after_close_raises(tmp_path, master):
    h = data.ParticipantDataHandler(str(tmp_path), "P01", master, IMG1, IMG2); h.close()
    with pytest.raises(IOError):
        h.save_trial_response(TRIAL, 1, 2)


def test_unwritable_log_dir_raises(tmp_path, master):
    blocker = tmp_path / "file_not_dir"; blocker.write_text("x")
    with pytest.raises(OSError):
        data.ParticipantDataHandler(str(blocker / "sub"), "P01", master, IMG1, IMG2)


@pytest.mark.parametrize("pid", ["P 01", "Ünïcødé", "a.b-c_d"])
def test_unusual_participant_ids(tmp_path, master, pid):
    h = data.ParticipantDataHandler(str(tmp_path), pid, master, IMG1, IMG2); h.close()
    assert ['Participant_ID', pid] in read_rows(h.filename)


def test_score_handler(tmp_path):
    s = data.ParticipantScoreHandler(str(tmp_path), "P01")
    s.add_ratings(10, 20); s.add_ratings("x", 5); s.add_ratings(30, 40)
    assert s.num_ratings == 2 and s.get_average_scores() == (20.0, 30.0)
    s.save_final_scores("completed")
    rows = read_rows(s.filename)
    assert ['Average_Discomfort', '20.00'] in rows and rows[-1] == ['Run_Status', 'completed']
    empty = data.ParticipantScoreHandler(str(tmp_path), "P02"); empty.save_final_scores("aborted")
    assert empty.filename is None


# --- TonicDataHandler ---------------------------------------------------------------

def tonic_config(tmp_path):
    c = TonicRunConfig()
    c.participant_id, c.scanner, c.image1_path, c.image2_path = "T01", "GE", IMG1, IMG2
    c.log_dir_participant = str(tmp_path)
    return c


def test_tonic_running_then_final(tmp_path):
    h = data.TonicDataHandler(tonic_config(tmp_path), {'size': (1600, 1200), 'vsync': True}, "OK 1600x1200")
    wall, perf = datetime(2026, 10, 23, 9, 0, 0), 100.0
    h.save(wall, perf, status="running")
    running = dict((r[0], r[1:]) for r in read_rows(h.filename) if r)
    assert running['Run_Status'] == ['running']
    assert running['Scanner_Trigger_Received'] == ['2026-10-23 09:00:00.000', '0.000']
    assert running['N_Trigger_Pulses_During_Run'] == ['', '']    # not known yet
    stats = {'Stim_Onset_s': "0.0167", 'N_Flips': 5400, 'Median_Interval_ms': "66.67",
             'N_Intervals_Over_1p5x': 0, 'N_Intervals_Under_0p5x': 0, 'Focus_Lost_Events': 0}
    h.save(wall, perf, 460.0167, "completed", flip_stats=stats, pulses=[102.0, 104.0])
    rows = read_rows(h.filename); final = dict((r[0], r[1:]) for r in rows if r)
    assert final['Run_Status'] == ['completed']
    assert final['Stimulus_Onset'] == ['2026-10-23 09:00:00.016', '0.017']
    assert final['Pre_Stimulus_Gap_s'] == ['', '0.017']
    assert final['Actual_Stimulus_Duration_s'] == ['', '360.000']   # measured from onset, not trigger
    assert final['N_Trigger_Pulses_During_Run'] == ['', '2']
    pulses = [r for r in rows if r and r[0] == 'Scanner_Pulse']
    assert pulses == [['Scanner_Pulse', '2026-10-23 09:00:02.000', '2.000'],
                      ['Scanner_Pulse', '2026-10-23 09:00:04.000', '4.000']]
    assert final['Display_Check'] == ['OK 1600x1200'] and final['Vsync'] == ['yes']


def test_tonic_aborted_before_trigger(tmp_path):
    h = data.TonicDataHandler(tonic_config(tmp_path))
    h.save(status="aborted")
    final = dict((r[0], r[1:]) for r in read_rows(h.filename) if r)
    assert final['Run_Status'] == ['aborted'] and final['Stimulus_Onset'] == ['', '']


def test_tonic_write_failure(tmp_path, monkeypatch):
    h = data.TonicDataHandler(tonic_config(tmp_path))
    h.filename = str(tmp_path / "missing_dir" / "x.csv")
    h.save(status="running")                                     # swallowed by default
    with pytest.raises(OSError):
        h.save(status="running", raise_errors=True)


# --- Run-status helpers --------------------------------------------------------------

def test_read_run_status(tmp_path, master):
    h = data.ParticipantDataHandler(str(tmp_path), "P01", master, IMG1, IMG2)
    h.save_trial_response(TRIAL, 1, 2); h.status = "completed"; h.close()
    assert data.read_run_status(h.filename) == ("completed", "1")
    crashed = tmp_path / "data_PX_20260101_000000.csv"; crashed.write_text("App_Version,v1\n")
    assert data.read_run_status(str(crashed))[0].startswith("no status")
    assert data.read_run_status(str(tmp_path / "missing.csv"))[0].startswith("no status")


def test_find_existing_runs_exact_id(tmp_path):
    names = ["data_P1_20261020_101010.csv", "data_P10_20261020_101010.csv",
             "data_P1_2_20261020_101010.csv", "tonic_P1_20261021_090000.csv",
             "summary_P1_avg_scores_20261020_101011.csv", "data_P1_notes.csv"]
    for i, n in enumerate(names):
        (tmp_path / n).write_text("x"); os.utime(tmp_path / n, (1000 + i, 1000 + i))
    found = [os.path.basename(p) for p in data.find_existing_runs(str(tmp_path), "1")]
    assert found == ["tonic_P1_20261021_090000.csv", "data_P1_20261020_101010.csv"]   # newest first, exact ID only
    assert [os.path.basename(p) for p in data.find_existing_runs(str(tmp_path), "1_2")] == ["data_P1_2_20261020_101010.csv"]
    assert data.find_existing_runs(str(tmp_path), "") == []
    assert data.find_existing_runs("", "1") == []


def test_find_existing_runs_glob_chars_in_path(tmp_path):
    d = tmp_path / "study [pilot] *"; d.mkdir()
    (d / "data_P1_20261020_101010.csv").write_text("x")
    assert len(data.find_existing_runs(str(d), "1")) == 1


def test_count_runs_using_master(tmp_path, master):
    for pid in ("A", "B"):
        h = data.ParticipantDataHandler(str(tmp_path), pid, master, IMG1, IMG2); h.close()
    other = write_master(tmp_path / "Other_master_trials.csv", [[1, 0, 1, 0.1, 10, 8, 7.5]])
    h = data.ParticipantDataHandler(str(tmp_path), "C", other, IMG1, IMG2); h.close()
    (tmp_path / "data_Pjunk_20260101_000000.csv").write_bytes(b"\xff\xfe garbage")
    assert data.count_runs_using_master(str(tmp_path), "Study1_master_trials.csv") == 2
    assert data.count_runs_using_master(str(tmp_path), "Other_master_trials.csv") == 1
    assert data.count_runs_using_master(str(tmp_path / "nope"), "x") == 0


def test_sha256_file(tmp_path):
    f = tmp_path / "f"; f.write_bytes(b"abc")
    assert data.sha256_file(str(f)) == hashlib.sha256(b"abc").hexdigest()
    assert data.sha256_file(str(tmp_path / "missing")) == ""


# --- Trial order -----------------------------------------------------------------------

def is_spaced(seq):
    return all(not (a >= BRIGHT_THRESHOLD and b >= BRIGHT_THRESHOLD) for a, b in zip(seq, seq[1:]))


@pytest.mark.parametrize("blocks", [1, 2, 3, 5, 10, 20])
def test_schedule_properties_many_seeds(blocks):
    for seed in range(300):
        order = data.build_randomized_schedule(blocks, seed, True)
        assert len(order) == blocks * len(BRIGHTNESS_LEVELS_BASE)
        for b in range(blocks):
            assert sorted(order[b * 6:(b + 1) * 6]) == sorted(BRIGHTNESS_LEVELS_BASE)
        assert is_spaced(BRIGHTNESS_LEVELS_BASE[-1:] + order), (blocks, seed)


def test_schedule_deterministic_and_seed_sensitive():
    a = data.build_randomized_schedule(3, 7, True)
    assert a == data.build_randomized_schedule(3, 7, True)
    distinct = {tuple(data.build_randomized_schedule(3, s, True)) for s in range(50)}
    assert len(distinct) > 40


def test_schedule_without_spacing_is_plain_shuffle():
    orders = [data.build_randomized_schedule(3, s, False) for s in range(200)]
    assert all(sorted(o[i:i + 6]) == sorted(BRIGHTNESS_LEVELS_BASE) for o in orders for i in (0, 6, 12))
    assert any(not is_spaced(BRIGHTNESS_LEVELS_BASE[-1:] + o) for o in orders)   # spacing really is optional


def test_standard_order_is_locked():
    """The canonical order must not change silently: every site depends on it.
    If this fails after an intended change, update it together with the docs."""
    assert data.build_randomized_schedule(3, CANONICAL_ORDER_SEED, True) == [
        0.1, 1.0, 0.2, 0.8, 0.6, 0.4,
        0.8, 0.4, 1.0, 0.1, 0.6, 0.2,
        0.6, 0.4, 0.8, 0.1, 1.0, 0.2]


def test_schedule_impossible_constraint_raises(monkeypatch):
    monkeypatch.setattr(data, "BRIGHTNESS_LEVELS_BASE", [0.8, 0.9, 1.0])   # every value is bright
    with pytest.raises(RuntimeError):
        data.build_randomized_schedule(2, 1, True, max_attempts=50)
