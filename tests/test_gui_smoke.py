# -*- coding: utf-8 -*-
"""Builds the real Tk windows off-screen and drives them: setup generator
(order preview, overwrite guard), run window (CSV summary, pre-flight,
participant warning, settings), tonic window (Hz hints, trigger test), and the
post-run summary. Dialogs are stubbed. Skipped where no display is available."""

import os
import json

import pytest

tk = pytest.importorskip("tkinter")
try:
    _probe = tk.Tk(); _probe.destroy()
except tk.TclError:
    pytest.skip("no display for Tk", allow_module_level=True)

import gui
import gui_widgets
from conftest import read_rows


@pytest.fixture(scope="module")
def _app():
    # One app per process: ttkbootstrap's Style is a singleton bound to the
    # first Tk root, as in the real program.
    a = gui.MVAST3Application()
    a.root.geometry("+5000+5000"); a.root.update()
    yield a
    a.root.destroy()


@pytest.fixture
def app(_app, tmp_path, monkeypatch):
    monkeypatch.setattr(gui_widgets, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    _app.msgs = []
    for name in ("showinfo", "showerror", "showwarning"):
        monkeypatch.setattr(gui.messagebox, name, lambda *a, _n=name, **k: _app.msgs.append((_n, a[0], a[1])))
    monkeypatch.setattr(gui.messagebox, "askyesno", lambda *a, **k: True)
    yield _app
    for w in _app.root.winfo_children():                       # close anything a test left open
        if isinstance(w, tk.Toplevel): w.destroy()


def setup_files(app, tmp_path, monkeypatch, exp_id="CREATE", choice="new"):
    monkeypatch.setattr(gui, "ask_choice", lambda *a, **k: (app.msgs.append(("ask_choice", a[2])), choice)[1])
    sg = gui.SetupGeneratorWindow(app.root, app); sg.window.geometry("+5000+5000")
    sg.exp_id_var.set(exp_id); sg.log_dir_base_var.set(str(tmp_path / "base")); sg.window.update()
    return sg


def test_setup_generator_standard_order_and_guard(app, tmp_path, monkeypatch):
    sg = setup_files(app, tmp_path, monkeypatch, choice="new")
    sg.process_generation()
    master = tmp_path / "base" / "experiment_setups" / "CREATE_master_trials.csv"
    order = [float(r[3]) for r in read_rows(master)[1:]]
    assert len(order) == 24 and order[6:] == [0.1, 1.0, 0.2, 0.8, 0.6, 0.4, 0.8, 0.4, 1.0, 0.1, 0.6, 0.2, 0.6, 0.4, 0.8, 0.1, 1.0, 0.2]
    assert (tmp_path / "base" / "randomization_schedules" / "CREATE_brightness_schedule.csv").exists()
    sg.process_generation()                                        # exists -> guard -> "save as new"
    assert ("ask_choice", "CREATE_master_trials.csv already exists") in app.msgs
    assert (tmp_path / "base" / "experiment_setups" / "CREATE_v2_master_trials.csv").exists()
    assert len(sg.order_canvas.find_all()) > 24                    # preview drawn
    sg.window.destroy()


def test_setup_generator_keep_existing_writes_nothing(app, tmp_path, monkeypatch):
    sg = setup_files(app, tmp_path, monkeypatch, choice="keep")
    sg.process_generation()
    master = tmp_path / "base" / "experiment_setups" / "CREATE_master_trials.csv"
    before = master.read_bytes(); mtime = master.stat().st_mtime_ns
    sg.order_mode_var.set("Custom"); sg.toggle_order_mode(); sg.seed_var.set(99); sg.window.update()
    sg.process_generation()
    assert master.read_bytes() == before and master.stat().st_mtime_ns == mtime
    sg.window.destroy()


def test_setup_generator_custom_order_and_validation(app, tmp_path, monkeypatch):
    sg = setup_files(app, tmp_path, monkeypatch)
    sg.order_mode_var.set("Custom"); sg.toggle_order_mode()
    assert str(sg.seed_entry.cget("state")) == "normal"
    sg.seed_var.set(5); sg.param_mode_var.set("Custom"); sg.toggle_custom_params(); sg.rand_blocks_var.set(20)
    sg.window.update()
    assert "Seed 5" in sg.order_note.cget("text")
    sg.order_mode_var.set("Standard"); sg.toggle_order_mode()
    assert sg.seed_var.get() == 16 and str(sg.seed_entry.cget("state")) == "disabled"
    sg.exp_id_var.set("bad/id"); sg.process_generation()
    assert app.msgs[-1][0] == "showerror"
    sg.window.destroy()


def test_run_window(app, tmp_path, monkeypatch):
    sg = setup_files(app, tmp_path, monkeypatch); sg.process_generation(); sg.window.destroy()
    runs = tmp_path / "base" / "participant_runs"; runs.mkdir(parents=True)
    rw = gui.ExperimentRunnerWindow(app.root, app); rw.window.geometry("+5000+5000")
    assert os.path.basename(rw.img1_path_var.get()) == "acheck_by.png"           # canonical default
    rw.master_csv_var.set(str(tmp_path / "base" / "experiment_setups" / "CREATE_master_trials.csv"))
    rw.participant_id_var.set("P01"); rw.log_dir_participant_var.set(str(runs))
    rw.refresh_preflight(); rw.window.update()
    assert rw.csv_summary.cget("text").startswith("✓ 24 trials")
    assert "Canonical" in rw.canonical_label.cget("text")
    assert rw.participant_note.cget("text") == ""
    (runs / "data_PP01_20261021_101530.csv").write_text("Run_Status,completed\nTrials_Completed,24\n")
    rw.refresh_preflight()
    assert "already exists" in rw.participant_note.cget("text")

    # Start with validation failures never reaches the runner
    started = []
    monkeypatch.setattr(gui, "execute_experiment_run", lambda c: started.append(c) or {'status': 'completed'})
    rw.participant_id_var.set(""); rw.start()
    assert started == [] and app.msgs[-1][1] == "Input Error"

    # Display mismatch: Cancel blocks the run; Continue records it
    monkeypatch.setattr(rw.display_picker, "selected", lambda: {'index': 0, 'name': '', 'size': (1920, 1080), 'refresh_hz': 60, 'bounds': None})
    rw.participant_id_var.set("P02")
    monkeypatch.setattr(gui, "ask_choice", lambda *a, **k: "cancel")
    rw.start(); assert started == []
    monkeypatch.setattr(gui, "ask_choice", lambda *a, **k: "continue")
    monkeypatch.setattr(gui, "show_run_summary", lambda *a, **k: None)
    rw.start()
    assert len(started) == 1 and started[0].display_mismatch_accepted and len(started[0].trials_data) == 24

    saved = json.load(open(gui_widgets.SETTINGS_FILE))["run"]
    assert saved["master_csv"].endswith("CREATE_master_trials.csv") and saved["log_dir"] == str(runs)
    rw.window.destroy()
    rw2 = gui.ExperimentRunnerWindow(app.root, app)
    assert rw2.master_csv_var.get() == saved["master_csv"]                       # remembered
    rw2.remember_var.set(False); rw2.remember(); rw2.window.destroy()
    assert json.load(open(gui_widgets.SETTINGS_FILE))["run"] == {'remember': False}


def test_run_window_rejects_bad_csv(app, tmp_path, monkeypatch):
    bad = tmp_path / "bad_master_trials.csv"
    bad.write_text("trial_number,block_number,trial_in_block,brightness_factor,stimulus_duration,fixation_duration,checkerboard_hz\n1,0,1,4,10,8,7.5\n")
    rw = gui.ExperimentRunnerWindow(app.root, app); rw.window.geometry("+5000+5000")
    rw.master_csv_var.set(str(bad)); rw.participant_id_var.set("P01"); rw.window.update()
    assert rw.csv_summary.cget("text").startswith("✗")
    started = []
    monkeypatch.setattr(gui, "execute_experiment_run", lambda c: started.append(c))
    rw.start()
    assert started == [] and app.msgs[-1][1] == "CSV Error"
    rw.window.destroy()


def test_tonic_window(app, tmp_path, monkeypatch):
    tw = gui.TonicRunnerWindow(app.root, app); tw.window.geometry("+5000+5000")
    monkeypatch.setattr(tw.display_picker, "selected", lambda: {'index': 0, 'name': '', 'size': (1600, 1200), 'refresh_hz': 60, 'bounds': None})
    for hz, expect in ((7.5, "✓ 4 frames"), (8.0, "3.75"), (0, "static")):
        tw.hz_var.set(hz); tw.refresh_preflight()
        assert expect in tw.hz_hint.cget("text")
    started = []
    monkeypatch.setattr(gui, "execute_tonic_run", lambda c: started.append(c) or {'status': 'completed'})
    monkeypatch.setattr(gui, "show_run_summary", lambda *a, **k: None)
    tw.participant_id_var.set("T01"); tw.log_dir_participant_var.set(str(tmp_path))
    tw.trigger_key_var.set(" "); tw.start()                       # SPACE is the operator's key
    assert started == [] and "single character" in app.msgs[-1][2]
    tw.trigger_key_var.set("55"); tw.start()
    assert started == [] and "single character" in app.msgs[-1][2]
    tw.hz_var.set(7.5); tw.trigger_key_var.set("5"); tw.duration_var.set(2.0); tw.start()
    assert started == [] and "Duration" in app.msgs[-1][2]
    tw.duration_var.set(360.0); tw.start()
    assert len(started) == 1 and started[0].trigger_key == "5" and started[0].hz == 7.5
    tw.window.destroy()


def test_trigger_test_counts_keys_and_tr(app, monkeypatch):
    tw = gui.TonicRunnerWindow(app.root, app); tw.window.geometry("+5000+5000")
    timers = []
    monkeypatch.setattr(tw.window, "after", lambda ms, fn: timers.append(fn) or "job")
    tw.test_trigger(seconds=10)
    tw.window.focus_force(); tw.window.update()                 # Tk sends keys to the focused window
    assert "Listening" in tw.trigger_result.cget("text")
    for t, key in ((1000, "5"), (3000, "5"), (4000, "a"), (5000, "5")):   # TR = 2 s; 'a' ignored
        tw.window.event_generate("<KeyPress>", keysym=key, time=t, when="now")
    timers[-1]()                                                           # the 10 s timer fires
    text = tw.trigger_result.cget("text")
    assert "×3" in text and "2.00 s" in text
    tw.test_trigger(seconds=10); tw.window.update(); timers[-1]()     # nothing received
    assert tw.trigger_result.cget("text").startswith("✗ No '5'")
    tw.window.destroy()


def test_run_summary_dialog(app, tmp_path, monkeypatch):
    f = tmp_path / "data_PX.csv"; f.write_text("x")
    res = {'status': 'aborted', 'message': 'Quit: stimulus', 'trials_completed': 3, 'trials_expected': 24,
           'elapsed_s': 95, 'display_info': {'vsync': True, 'refresh_hz_measured': 60.0},
           'display_check': 'OK 1600x1200', 'flagged_trials': [{'trial': 2, 'brightness': 0.6, 'max_ms': '183.4', 'min_ms': '66.5', 'over': 1, 'under': 0}],
           'focus_events': 1, 'avg_discomfort': 40.0, 'avg_brightness': 50.0, 'files': [str(f)]}
    texts = []
    def close():
        for w in app.root.winfo_children():
            if isinstance(w, gui.ttk.Toplevel) and w.title() == "Summary":
                def walk(x):
                    for c in x.winfo_children():
                        try: texts.append(str(c.cget("text")))
                        except Exception: pass
                        walk(c)
                walk(w); w.destroy()
    app.root.after(200, close)
    gui.show_run_summary(app.root, "Summary", res)
    joined = " | ".join(texts)
    for s in ("Aborted", "3 of 24 trials", "Quit: stimulus", "Trial 2", "lost focus 1 time", "Display_Check: OK", "data_PX.csv"):
        assert s in joined, s
