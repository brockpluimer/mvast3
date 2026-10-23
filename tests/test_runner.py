# -*- coding: utf-8 -*-
"""runner.py end to end with the dummy video driver: every way a run can end
(completed, aborted at each stage, write failure, missing image, bad display,
unexpected exception) must leave a correct file and return a correct result,
and pygame must always be shut down so the GUI can run again."""

import os
import threading
import time
from datetime import datetime

import pygame
import pytest

import data
import runner
import stimulus
from config import RunConfig, TonicRunConfig
from conftest import IMG1, IMG2, write_master, read_rows, key_event


@pytest.fixture
def ui(monkeypatch):
    """Stub the participant: waiting screens continue, ratings come from a script."""
    state = {'messages': [], 'continue': True, 'ratings': iter([])}
    def show_message(screen, text, wait_for_key=True, escape_quits=True, continue_keys=None):
        state['messages'].append((text.splitlines()[0], wait_for_key, continue_keys))
        return state['continue'] if wait_for_key else True
    monkeypatch.setattr(runner, "show_message", show_message)
    monkeypatch.setattr(runner, "get_rating_with_click", lambda s, t, k: next(state['ratings']))
    monkeypatch.setattr(runner.pygame.time, "wait", lambda ms: None)
    return state


def make_config(tmp_path, n=3, sd=0.15, hz=7.5, pid="P01"):
    rows = [[i + 1, 0, i + 1, bf, sd, 0.02, hz] for i, bf in enumerate([0.1, 0.6, 1.0, 0.4, 0.2, 0.8][:n])]
    c = RunConfig()
    c.master_csv_path = write_master(tmp_path / "T_master_trials.csv", rows)
    c.trials_data = [dict(trial_number=r[0], block_number=r[1], trial_in_block=r[2], brightness_factor=r[3],
                          stimulus_duration=r[4], fixation_duration=r[5], checkerboard_hz=r[6]) for r in rows]
    c.image1_path, c.image2_path = IMG1, IMG2
    c.participant_id, c.log_dir_participant = pid, str(tmp_path / "runs")
    return c


def data_file(result):
    return next(f for f in result['files'] if os.path.basename(f).startswith(("data_", "tonic_")))


def footer(path):
    return {r[0]: r[1] for r in read_rows(path)[-3:]}


def trial_rows(path):
    rows = read_rows(path)
    i = next(i for i, r in enumerate(rows) if r and r[0] == 'Trial_Number_Overall')
    return [r for r in rows[i + 1:] if r and r[0].isdigit()]


@pytest.fixture(autouse=True)
def pygame_always_shut_down():
    yield
    assert not pygame.get_init(), "runner left pygame initialised"


# --- standard run -------------------------------------------------------------------

def test_completed_run(tmp_path, ui):
    ui['ratings'] = iter([10, 20, 30, 40, 50, 60])
    r = runner.execute_experiment_run(make_config(tmp_path))
    assert r['status'] == 'completed' and r['trials_completed'] == r['trials_expected'] == 3
    assert r['avg_discomfort'] == 30 and r['avg_brightness'] == 40
    assert r['flagged_trials'] == [] and r['focus_events'] == 0
    assert len(r['files']) == 2 and all(os.path.exists(f) for f in r['files'])
    f = footer(data_file(r))
    assert f['Run_Status'] == 'completed' and f['Trials_Completed'] == '3'
    rows = trial_rows(data_file(r))
    assert [row[7:9] for row in rows] == [['10', '20'], ['30', '40'], ['50', '60']]
    onsets = [float(row[10]) for row in rows]
    assert onsets == sorted(onsets) and all(float(row[12]) == pytest.approx(0.15, abs=0.01) for row in rows)
    assert r['display_check'].startswith("MISMATCH")                 # dummy display isn't 1600x1200


@pytest.mark.parametrize("stage", ["instructions", "fixation", "stimulus", "rating1", "rating2"])
def test_abort_at_each_stage(tmp_path, ui, monkeypatch, stage):
    ui['ratings'] = iter([1, 2] + ([None] if stage == "rating1" else [3, None] if stage == "rating2" else [3, 4, 5, 6]))
    if stage == "instructions": ui['continue'] = False
    calls = {'n': 0}
    if stage == "fixation":
        real = runner.show_fixation
        monkeypatch.setattr(runner, "show_fixation", lambda s, d: (calls.__setitem__('n', calls['n'] + 1), calls['n'] < 2 and real(s, d))[1])
    if stage == "stimulus":
        real_f = runner.run_flicker
        def flick(*a, **k):
            calls['n'] += 1
            r = real_f(*a, **k)
            if calls['n'] == 2: r.completed = False
            return r
        monkeypatch.setattr(runner, "run_flicker", flick)
    r = runner.execute_experiment_run(make_config(tmp_path))
    expected_done = {'instructions': 0, 'fixation': 1, 'stimulus': 1, 'rating1': 1, 'rating2': 1}[stage]
    assert r['status'] == 'aborted' and r['trials_completed'] == expected_done
    f = footer(data_file(r))
    assert f['Run_Status'] == 'aborted' and f['Trials_Completed'] == str(expected_done)
    assert len(trial_rows(data_file(r))) == expected_done
    assert ("Experiment stopped.", False, None) in ui['messages']


def test_write_failure_stops_run_with_error(tmp_path, ui, monkeypatch):
    ui['ratings'] = iter([1, 2, 3, 4, 5, 6])
    real = data.ParticipantDataHandler.save_trial_response
    def flaky(self, *a, **k):
        if self.trials_completed == 1: raise OSError(5, "Input/output error")
        return real(self, *a, **k)
    monkeypatch.setattr(data.ParticipantDataHandler, "save_trial_response", flaky)
    r = runner.execute_experiment_run(make_config(tmp_path))
    assert r['status'] == 'error' and "Input/output" in r['message'] and r['trials_completed'] == 1
    assert footer(data_file(r))['Run_Status'] == 'error'


def test_missing_image_is_an_error_with_a_file(tmp_path, ui):
    c = make_config(tmp_path); c.image2_path = str(tmp_path / "gone.png")
    r = runner.execute_experiment_run(c)
    assert r['status'] == 'error' and "not found" in r['message']
    assert footer(data_file(r))['Run_Status'] == 'error'


def test_bad_display_index(tmp_path, ui):
    c = make_config(tmp_path); c.display_index = 5
    r = runner.execute_experiment_run(c)
    assert r['status'] == 'error' and "Could not open the stimulus display" in r['message']
    assert r['files'] == []


def test_unexpected_exception_is_contained(tmp_path, ui, monkeypatch):
    def broken(*a): raise ValueError("boom")
    monkeypatch.setattr(runner, "get_rating_with_click", broken)
    r = runner.execute_experiment_run(make_config(tmp_path))
    assert r['status'] == 'error' and "ValueError" in r['message']
    assert footer(data_file(r))['Run_Status'] == 'error'


def test_unwritable_log_dir(tmp_path, ui):
    blocker = tmp_path / "blocker"; blocker.write_text("x")
    c = make_config(tmp_path); c.log_dir_participant = str(blocker / "runs")
    r = runner.execute_experiment_run(c)
    assert r['status'] == 'error' and r['files'] == []


def test_flagged_trials_and_focus_events(tmp_path, ui, monkeypatch):
    ui['ratings'] = iter([1, 2, 3, 4])
    real = runner.run_flicker
    def stalled(*a, **k):
        r = real(*a, **k)
        if len(r.flips) > 2: r.flips[2] += 0.2      # one long interval, then one short
        stimulus._focus_events[0] += 1
        return r
    monkeypatch.setattr(runner, "run_flicker", stalled)
    r = runner.execute_experiment_run(make_config(tmp_path, n=2, sd=0.4))
    assert r['status'] == 'completed'
    assert [f['trial'] for f in r['flagged_trials']] == [1, 2]
    assert r['focus_events'] == 2
    assert [row[19] for row in trial_rows(data_file(r))] == ['1', '1']


def test_static_hz_zero_trials(tmp_path, ui):
    ui['ratings'] = iter([1, 2])
    r = runner.execute_experiment_run(make_config(tmp_path, n=1, hz=0))
    row = trial_rows(data_file(r))[0]
    assert r['status'] == 'completed' and row[13] == '1' and row[14] == ''   # one flip, no interval stats


def test_back_to_back_runs(tmp_path, ui):
    """The GUI runs several sessions in one process."""
    for i in range(3):
        ui['ratings'] = iter([1, 2])
        r = runner.execute_experiment_run(make_config(tmp_path, n=1, pid=f"P{i}"))
        assert r['status'] == 'completed'
        assert not pygame.get_init()


# --- tonic run -------------------------------------------------------------------------

def tonic_config(tmp_path, duration=1.0):
    c = TonicRunConfig()
    c.participant_id, c.scanner, c.duration = "T01", "GE", duration
    c.image1_path, c.image2_path, c.log_dir_participant = IMG1, IMG2, str(tmp_path / "runs")
    return c


@pytest.fixture
def scanner(monkeypatch):
    """Trigger arrives at once; `pulses` (seconds after the trigger) are posted as '5' keystrokes."""
    state = {'pulses': [0.2, 0.4, 0.6], 'trigger': True, 'threads': []}
    def wait(screen, key):
        if not state['trigger']: return None
        def send():
            t0 = time.perf_counter()
            for p in state['pulses']:
                time.sleep(max(0, p - (time.perf_counter() - t0)))
                if pygame.display.get_init(): pygame.event.post(key_event(pygame.K_5, "5"))
        th = threading.Thread(target=send, daemon=True); th.start(); state['threads'].append(th)
        return datetime.now(), time.perf_counter()
    monkeypatch.setattr(runner, "wait_for_scanner_trigger", wait)
    yield state
    for th in state['threads']: th.join()   # don't leak pulses into the next test


def test_tonic_completed(tmp_path, ui, scanner):
    r = runner.execute_tonic_run(tonic_config(tmp_path))
    assert r['status'] == 'completed' and r['n_pulses'] == 3
    assert 0 <= r['onset_gap_s'] < 0.05
    assert ui['messages'][0][2] == (pygame.K_SPACE,)                  # intro waits for SPACE only
    rows = {row[0]: row[1:] for row in read_rows(data_file(r)) if row}
    assert rows['Run_Status'] == ['completed']
    assert float(rows['Actual_Stimulus_Duration_s'][1]) == pytest.approx(1.0, abs=0.02)
    assert rows['N_Trigger_Pulses_During_Run'] == ['', '3']
    pulses = [row for row in read_rows(data_file(r)) if row and row[0] == 'Scanner_Pulse']
    assert [round(float(p[2]), 1) for p in pulses] == [0.2, 0.4, 0.6]


def test_tonic_log_exists_before_stimulus(tmp_path, ui, scanner, monkeypatch):
    seen = {}
    real = runner.run_flicker
    def check(*a, **k):
        path = next((tmp_path / "runs").glob("tonic_*.csv"))
        seen['status'] = {r[0]: r[1] for r in read_rows(path) if len(r) > 1}['Run_Status']
        return real(*a, **k)
    monkeypatch.setattr(runner, "run_flicker", check)
    runner.execute_tonic_run(tonic_config(tmp_path, 0.3))
    assert seen['status'] == 'running'


def test_tonic_abort_before_trigger(tmp_path, ui, scanner):
    scanner['trigger'] = False
    r = runner.execute_tonic_run(tonic_config(tmp_path))
    assert r['status'] == 'aborted' and r['onset_gap_s'] is None
    rows = {row[0]: row[1:] for row in read_rows(data_file(r)) if row}
    assert rows['Run_Status'] == ['aborted'] and rows['Scanner_Trigger_Received'] == ['', '']


def test_tonic_abort_during_stimulus_keeps_partial_timing(tmp_path, ui, scanner):
    scanner['pulses'] = [0.2, 0.5]
    def esc_later():
        time.sleep(0.6); pygame.event.post(key_event(pygame.K_ESCAPE))
    threading.Thread(target=esc_later, daemon=True).start()
    r = runner.execute_tonic_run(tonic_config(tmp_path, 5.0))
    assert r['status'] == 'aborted' and r['n_pulses'] == 2
    rows = {row[0]: row[1:] for row in read_rows(data_file(r)) if row}
    assert 0.4 < float(rows['Actual_Stimulus_Duration_s'][1]) < 1.5
    assert int(rows['N_Flips'][1]) > 1


def test_tonic_write_failure_at_trigger_stops_before_stimulus(tmp_path, ui, scanner, monkeypatch):
    started = []
    monkeypatch.setattr(runner, "run_flicker", lambda *a, **k: started.append(1))
    real = data.TonicDataHandler.save
    def save(self, *a, **k):
        if k.get('status') == 'running': raise OSError(28, "No space left on device")
        return real(self, *a, **k)
    monkeypatch.setattr(data.TonicDataHandler, "save", save)
    r = runner.execute_tonic_run(tonic_config(tmp_path))
    assert r['status'] == 'error' and "No space" in r['message'] and started == []


def test_tonic_bad_display(tmp_path, ui, scanner):
    c = tonic_config(tmp_path); c.display_index = 9
    r = runner.execute_tonic_run(c)
    assert r['status'] == 'error' and r['files'] == []


def test_tonic_fixation_overlay(tmp_path, ui, scanner, monkeypatch):
    seen = {}
    real = runner.run_flicker
    monkeypatch.setattr(runner, "run_flicker", lambda *a, **k: (seen.update(k), real(*a, **k))[1])
    c = tonic_config(tmp_path, 0.2); c.show_fixation = True
    runner.execute_tonic_run(c)
    assert seen['overlay'] is not None and seen['trigger_key'] == "5"
