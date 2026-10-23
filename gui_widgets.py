# -*- coding: utf-8 -*-
"""M-VAST 3 - shared Tkinter widgets, dialogs, and helpers for the run and
setup windows: scrollable container, image row with thumbnail, display
picker, pre-flight check panel, choice dialog, run summary, remembered
settings, and master-CSV loading."""

import os
import sys
import csv
import json
import shutil
import subprocess

import tkinter as tk
from tkinter import filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk

from config import (
    APP_BASE_PATH, SETTINGS_FILE, EXPECTED_DISPLAY_SIZE, CSV_LIMITS,
    RAMP_UP_TRIALS_COUNT, TRIALS_PER_BLOCK,
)
from data import sha256_file, find_existing_runs, read_run_status
from stimulus import list_displays, describe_display, identify_displays, frames_per_half_cycle

HINT_FONT = ("", 9)
RATING_SECONDS_ESTIMATE = 10.0   # rough time per trial for the two ratings

# --- Remembered settings ---
def load_settings(section):
    try:
        with open(SETTINGS_FILE, encoding='utf-8') as f:
            return json.load(f).get(section, {})
    except (OSError, ValueError):
        return {}

def save_settings(section, values):
    try:
        try:
            with open(SETTINGS_FILE, encoding='utf-8') as f: allv = json.load(f)
        except (OSError, ValueError):
            allv = {}
        allv[section] = values
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f: json.dump(allv, f, indent=2)
    except OSError as e:
        print(f"Could not save settings: {e}")

def open_folder(path):
    try:
        if sys.platform.startswith('win'): os.startfile(path)
        elif sys.platform == 'darwin': subprocess.Popen(['open', path])
        else: subprocess.Popen(['xdg-open', path])
    except Exception as e:
        print(f"Could not open folder {path}: {e}")

# --- Master CSV ---
def load_master_csv(path):
    """Read and range-check a master trial CSV. Returns (trials, errors);
    `errors` is a list of human-readable problems (empty when valid)."""
    trials, errors = [], []
    try:
        # utf-8-sig: a CSV re-saved from Excel starts with a byte-order mark
        with open(path, 'r', newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            reader.fieldnames = [field.strip() for field in reader.fieldnames or []]
            expected = ['trial_number', 'brightness_factor', 'stimulus_duration', 'fixation_duration', 'checkerboard_hz']
            missing = [col for col in expected if col not in reader.fieldnames]
            if missing: return [], [f"CSV missing column(s): {', '.join(missing)}"]
            for i, row in enumerate(reader):
                line = i + 2
                try:
                    block_num_csv = row.get('block_number')
                    trial_in_block_csv = row.get('trial_in_block')
                    if block_num_csv is not None and trial_in_block_csv is not None:
                        block_num = int(block_num_csv)
                        trial_in_block = int(trial_in_block_csv)
                    else:
                        trial_idx_overall = int(row['trial_number']) -1
                        if trial_idx_overall < RAMP_UP_TRIALS_COUNT:
                            block_num = 0
                            trial_in_block = trial_idx_overall + 1
                        else:
                            randomized_trial_idx = trial_idx_overall - RAMP_UP_TRIALS_COUNT
                            block_num = (randomized_trial_idx // TRIALS_PER_BLOCK) + 1
                            trial_in_block = (randomized_trial_idx % TRIALS_PER_BLOCK) + 1
                    trial = {
                        'trial_number': int(row['trial_number']),
                        'block_number': block_num,
                        'trial_in_block': trial_in_block,
                        'brightness_factor': float(row['brightness_factor']),
                        'stimulus_duration': float(row['stimulus_duration']),
                        'fixation_duration': float(row['fixation_duration']),
                        'checkerboard_hz': float(row['checkerboard_hz'])}
                except (ValueError, KeyError, TypeError) as ve:
                    errors.append(f"Row {line}: not a number ({ve})"); continue
                for col, (lo, hi) in CSV_LIMITS.items():
                    v = trial[col]
                    low_ok = v >= lo if col == 'checkerboard_hz' else v > lo
                    if not (low_ok and v <= hi):
                        errors.append(f"Row {line}: {col} = {v:g} is outside {lo:g}–{hi:g}")
                trials.append(trial)
        if not trials and not errors: errors.append("No trials in CSV.")
        numbers = [t['trial_number'] for t in trials]
        if numbers and numbers != list(range(1, len(numbers) + 1)):
            errors.append("trial_number is not 1, 2, 3, … in order")
    except Exception as e:
        errors.append(f"Error reading {path}: {e}")
    return trials, errors

def estimate_minutes(trials):
    total = sum(t['fixation_duration'] + t['stimulus_duration'] + RATING_SECONDS_ESTIMATE for t in trials)
    return total / 60.0

# --- Scrollable container ---
class ScrollFrame(ttk.Frame):
    """A vertically scrollable frame; put content in `.inner`."""
    def __init__(self, parent, padding=(20, 15)):
        super().__init__(parent)
        bg = ttk.Style().colors.bg
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0, background=bg)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas, padding=padding)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.pack(side=LEFT, fill=BOTH, expand=YES)
        self.vsb.pack(side=RIGHT, fill=Y)
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        self.bind("<Enter>", lambda e: self._bind_wheel(True))
        self.bind("<Leave>", lambda e: self._bind_wheel(False))

    def _bind_wheel(self, on):
        seqs = ("<MouseWheel>", "<Button-4>", "<Button-5>")
        for s in seqs:
            if on: self.canvas.bind_all(s, self._on_wheel)
            else: self.canvas.unbind_all(s)

    def _on_wheel(self, e):
        if self.inner.winfo_height() <= self.canvas.winfo_height(): return
        if e.num == 4: step = -1
        elif e.num == 5: step = 1
        elif sys.platform == 'darwin': step = -e.delta
        else: step = -int(e.delta / 120)
        self.canvas.yview_scroll(step, "units")

# --- Image row with thumbnail ---
class ImageRow:
    """Label, thumbnail, read-only path entry and Browse button on one grid row."""
    THUMB = (52, 39)
    def __init__(self, parent, row, label, var, on_change=None):
        self.var, self.on_change, self._photo = var, on_change, None
        ttk.Label(parent, text=label, font=("", 10)).grid(row=row, column=0, padx=5, pady=5, sticky="w")
        self.thumb = ttk.Label(parent)
        self.thumb.grid(row=row, column=1, padx=(5, 0), pady=5)
        ttk.Entry(parent, textvariable=var, width=40, state='readonly', font=("", 10)).grid(row=row, column=2, padx=5, pady=5, sticky="ew")
        ttk.Button(parent, text="Browse...", command=self.browse, style='outline.TButton').grid(row=row, column=3, padx=5, pady=5)
        parent.columnconfigure(2, weight=1)
        var.trace_add("write", lambda *a: self.refresh())
        self.refresh()

    def browse(self):
        init_img_dir = os.path.join(APP_BASE_PATH, "images")
        fp = filedialog.askopenfilename(parent=self.thumb.winfo_toplevel(), title="Select Image",
                                        filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.gif")],
                                        initialdir=init_img_dir if os.path.exists(init_img_dir) else APP_BASE_PATH)
        if fp: self.var.set(fp)

    def refresh(self):
        self._photo = None
        try:
            img = Image.open(self.var.get()); img.thumbnail(self.THUMB)
            self._photo = ImageTk.PhotoImage(img)
        except Exception:
            pass
        self.thumb.configure(image=self._photo or "", text="" if self._photo else "  —  ")
        if self.on_change: self.on_change()

def check_image(path):
    """(ok, size_or_error) for an image path, checked with PIL before going full-screen."""
    if not path: return False, "not selected"
    if not os.path.exists(path): return False, "file not found"
    try:
        with Image.open(path) as im:
            im.verify()
        with Image.open(path) as im:
            return True, im.size
    except Exception as e:
        return False, f"can't be read ({e})"

# --- Display picker ---
class DisplayPicker:
    """Combobox of connected displays plus an Identify button."""
    def __init__(self, parent, initial_index=0, on_change=None):
        self.on_change = on_change
        self.frame = ttk.Labelframe(parent, text="Display")
        self.var = tk.StringVar()
        ttk.Label(self.frame, text="Present on:", font=("", 10)).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.combo = ttk.Combobox(self.frame, textvariable=self.var, state="readonly", font=("", 10))
        self.combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(self.frame, text="Identify", command=self.identify, style='outline.TButton').grid(row=0, column=2, padx=5, pady=5)
        ttk.Label(self.frame, text="Identify shows each display's number on that screen for 2 s.",
                  font=HINT_FONT, foreground="gray").grid(row=1, column=1, columnspan=2, padx=5, pady=(0, 5), sticky="w")
        self.frame.columnconfigure(1, weight=1)
        self.combo.bind("<<ComboboxSelected>>", lambda e: self.on_change and self.on_change())
        self.displays = []
        self.reload(initial_index)

    def reload(self, index=None):
        if index is None: index = self.index()
        try: self.displays = list_displays()
        except Exception as e:
            print(f"Could not list displays: {e}"); self.displays = []
        labels = [describe_display(d) for d in self.displays] or ["Display 1 (main)"]
        self.combo.configure(values=labels)
        self.combo.current(index if 0 <= index < len(labels) else 0)
        if self.on_change: self.on_change()

    def index(self):
        i = self.combo.current()
        return i if i >= 0 else 0

    def selected(self):
        i = self.index()
        return self.displays[i] if i < len(self.displays) else None

    def identify(self):
        top = self.frame.winfo_toplevel()
        top.config(cursor="watch"); top.update_idletasks()
        try: identify_displays(2.0)
        except Exception as e: print(f"Identify failed: {e}")
        finally: top.config(cursor="")
        self.reload()

# --- Check lists ---
class CheckList(ttk.Frame):
    """Rows of checks shown as ✓ / ! / ✗ with text. `set` takes (level, text)
    pairs where level is 'ok', 'warn' or 'bad'."""
    ICONS = {'ok': ("✓", "success"), 'warn': ("!", "warning"), 'bad': ("✗", "danger")}
    def __init__(self, parent, wraplength=640):
        super().__init__(parent, padding=(5, 2))
        self.wraplength = wraplength

    def set(self, checks):
        for w in self.winfo_children(): w.destroy()
        for i, (level, text) in enumerate(checks):
            icon, style = self.ICONS[level]
            ttk.Label(self, text=icon, bootstyle=style, font=("", 11, "bold"), width=2).grid(row=i, column=0, sticky="nw", pady=1)
            ttk.Label(self, text=text, font=("", 10), wraplength=self.wraplength, justify="left").grid(row=i, column=1, sticky="w", pady=1)

class PreflightPanel:
    """The "Pre-flight Check" Labelframe on the run windows."""
    def __init__(self, parent):
        self.frame = ttk.Labelframe(parent, text="Pre-flight Check")
        self.list = CheckList(self.frame)
        self.list.pack(fill=X)

    def set(self, checks): self.list.set(checks)

def display_checks(display, hz_values):
    """Pre-flight rows for the chosen display and flicker rates."""
    checks = []
    if not display:
        return [('warn', "Displays could not be listed; the task will open on the main display.")]
    w, h = display['size']
    n = display['index'] + 1
    if (w, h) == EXPECTED_DISPLAY_SIZE:
        checks.append(('ok', f"Display {n} is {w}×{h}, matches the protocol"))
    else:
        checks.append(('warn', f"Display {n} is {w}×{h}; the protocol expects {EXPECTED_DISPLAY_SIZE[0]}×{EXPECTED_DISPLAY_SIZE[1]}. "
                               "(On Windows, also check display scaling is 100%.)"))
    rr = display['refresh_hz']
    for hz in sorted(set(hz_values)):
        if hz <= 0: continue
        fph = frames_per_half_cycle(hz, rr)
        if fph is None:
            checks.append(('warn', f"Refresh rate unknown; frames per half-cycle at {hz:g} Hz can't be checked (it's measured at run start)"))
        elif abs(fph - round(fph)) < 0.01:
            checks.append(('ok', f"Refresh {rr} Hz: {hz:g} Hz flicker = exactly {round(fph)} frames per half-cycle"))
        else:
            checks.append(('warn', f"Refresh {rr} Hz: {hz:g} Hz flicker = {fph:.2f} frames per half-cycle, not a whole number, "
                                   "so half-cycles will alternate in length"))
    return checks

def folder_check(path):
    probe = path
    while probe and not os.path.exists(probe):
        parent = os.path.dirname(probe)
        if parent == probe: break
        probe = parent
    if not probe or not os.path.exists(probe):
        return ('bad', f"Output folder not reachable: {path}")
    if not os.access(probe, os.W_OK):
        return ('bad', f"Output folder is not writable: {probe}")
    free_gb = shutil.disk_usage(probe).free / 1e9
    level = 'ok' if free_gb >= 1 else 'warn'
    return (level, f"Output folder writable, {free_gb:.0f} GB free")

def image_checks(path1, path2, display):
    checks, sizes = [], []
    for label, p in (("Image 1", path1), ("Image 2", path2)):
        ok, info = check_image(p)
        if not ok: checks.append(('bad', f"{label} {info}")); continue
        sizes.append(info)
    if len(sizes) == 2:
        dsize = display['size'] if display else None
        if dsize and any(s != tuple(dsize) for s in sizes):
            s = sizes[0]
            checks.append(('warn', f"Images are {s[0]}×{s[1]} but the display is {dsize[0]}×{dsize[1]}; they will be stretched to fit"))
        else:
            checks.append(('ok', "Both images load" + (f" and match the display ({sizes[0][0]}×{sizes[0][1]})" if dsize else "")))
        if path1 == path2: checks.append(('warn', "Image 1 and Image 2 are the same file (no visible flicker)"))
    return checks

def participant_check(log_dir, participant_id):
    """(level, text) or None, warning if this ID already has data here."""
    runs = find_existing_runs(log_dir, participant_id)
    if not runs: return None
    status, done = read_run_status(runs[0])
    extra = f", {done} trials completed" if done else ""
    more = f" (+{len(runs) - 1} more)" if len(runs) > 1 else ""
    return ('warn', f"Data for {participant_id} already exists: {os.path.basename(runs[0])}{more}, "
                    f"run status {status}{extra}. Starting creates a new file; nothing is overwritten.")

# --- Choice dialog ---
def ask_choice(parent, title, heading, body_lines, buttons, default, icon="⚠", detail_style="warning"):
    """Modal dialog. `buttons` is a list of (value, label, bootstyle) shown
    right-aligned in order; returns the chosen value (or `default` on close/Escape)."""
    dlg = ttk.Toplevel(parent)
    dlg.title(title); dlg.transient(parent); dlg.resizable(False, False)
    choice = {'v': default}
    body = ttk.Frame(dlg, padding=(22, 18)); body.pack(fill=BOTH, expand=YES)
    ttk.Label(body, text=icon, font=("", 26), bootstyle=detail_style).grid(row=0, column=0, rowspan=2, sticky="n", padx=(0, 14))
    ttk.Label(body, text=heading, font=("", 13, "bold")).grid(row=0, column=1, sticky="w", pady=(0, 6))
    text = ttk.Frame(body); text.grid(row=1, column=1, sticky="w")
    for line in body_lines:
        ttk.Label(text, text=line, font=("", 10), wraplength=480, justify="left").pack(anchor="w", pady=2)
    btns = ttk.Frame(body); btns.grid(row=2, column=0, columnspan=2, sticky="e", pady=(16, 0))
    def pick(v): choice['v'] = v; dlg.destroy()
    default_btn = None
    for value, label, style in buttons:
        b = ttk.Button(btns, text=label, bootstyle=style, command=lambda v=value: pick(v))
        b.pack(side=LEFT, padx=(8, 0))
        if value == default: default_btn = b
    dlg.bind("<Escape>", lambda e: pick(default))
    dlg.bind("<Return>", lambda e: pick(default))
    dlg.grab_set()
    if default_btn: default_btn.focus_set()
    dlg.wait_window()
    return choice['v']

# --- Run summary ---
def show_run_summary(parent, title, result, tonic=False):
    """Post-run dialog: status, timing QC, focus, display check, files."""
    status = result.get('status', 'error')
    dlg = ttk.Toplevel(parent)
    dlg.title(title); dlg.transient(parent)
    body = ttk.Frame(dlg, padding=(22, 18)); body.pack(fill=BOTH, expand=YES)

    head = ttk.Frame(body); head.pack(fill=X, pady=(0, 12))
    style = {'completed': 'success', 'aborted': 'warning'}.get(status, 'danger')
    ttk.Label(head, text=f" {'✓' if status == 'completed' else '!'} {status.capitalize()} ",
              bootstyle=f"inverse-{style}", font=("", 12, "bold")).pack(side=LEFT)
    mins, secs = divmod(int(result.get('elapsed_s', 0)), 60)
    if tonic:
        fs = result.get('flip_stats', {})
        dur = fs.get('Actual_Stimulus_Duration_s', "")
        summary = f"Stimulus {float(dur):.1f} s · {result.get('n_pulses', 0)} scanner pulses" if dur else "Stimulus did not start"
    else:
        summary = f"{result.get('trials_completed', 0)} of {result.get('trials_expected', 0)} trials · {mins} min {secs} s"
    ttk.Label(head, text=summary, font=("", 13, "bold")).pack(side=LEFT, padx=10)
    if result.get('message') and status != 'completed':
        ttk.Label(body, text=f"Stopped: {result['message']}", font=("", 10), wraplength=560, justify="left").pack(anchor="w", pady=(0, 10))

    qc = ttk.Labelframe(body, text="Timing QC"); qc.pack(fill=X, pady=(0, 10))
    qc_list = CheckList(qc, wraplength=540); qc_list.pack(fill=X)
    checks = []
    info = result.get('display_info') or {}
    if info:
        if info.get('vsync'):
            checks.append(('ok', f"Vsync on, refresh measured {info['refresh_hz_measured']:.1f} Hz"))
        else:
            checks.append(('warn', "Vsync not available; board changes were timed in software only"))
    if tonic:
        fs = result.get('flip_stats', {})
        if fs.get('N_Flips'):
            over, under = fs.get('N_Intervals_Over_1p5x') or 0, fs.get('N_Intervals_Under_0p5x') or 0
            level = 'ok' if not (over or under) else 'warn'
            checks.append((level, f"{fs['N_Flips']} flips, median interval {fs.get('Median_Interval_ms')} ms "
                                  f"(min {fs.get('Min_Interval_ms')}, max {fs.get('Max_Interval_ms')}); "
                                  f"{over} over 1.5×, {under} under 0.5×"))
        if result.get('onset_gap_s') is not None:
            checks.append(('ok', f"First frame {result['onset_gap_s'] * 1000:.1f} ms after the scanner trigger"))
    else:
        flagged = result.get('flagged_trials', [])
        done = result.get('trials_completed', 0)
        if done:
            checks.append(('ok' if not flagged else 'warn', f"{done - len(flagged)} of {done} trials had no stalls or catch-up flips"))
        for f in flagged:
            checks.append(('warn', f"Trial {f['trial']} (brightness {f['brightness']:g}): max interval {f['max_ms']} ms, "
                                   f"min {f['min_ms']} ms ({f['over']} over 1.5×, {f['under']} under 0.5×)"))
    focus = result.get('focus_events', 0)
    checks.append(('ok', "Window kept focus for the whole run") if not focus else
                  ('warn', f"Window lost focus {focus} time(s); see the Focus_Lost_Events column"))
    dc = result.get('display_check', "")
    if dc: checks.append(('ok' if dc.startswith("OK") else 'warn', f"Display_Check: {dc}"))
    qc_list.set(checks)

    if not tonic and result.get('avg_discomfort') is not None:
        r = ttk.Labelframe(body, text="Ratings"); r.pack(fill=X, pady=(0, 10))
        ttk.Label(r, text=f"Avg. unpleasantness {result['avg_discomfort']:.1f}      Avg. brightness {result['avg_brightness']:.1f}",
                  font=("", 10), padding=(5, 4)).pack(anchor="w")

    files = [f for f in result.get('files', []) if f and os.path.exists(f)]
    if files:
        fr = ttk.Labelframe(body, text="Files Written"); fr.pack(fill=X, pady=(0, 10))
        for f in files: ttk.Label(fr, text=os.path.basename(f), font=("Courier", 10), padding=(5, 1)).pack(anchor="w")
        ttk.Label(fr, text=os.path.dirname(files[0]), font=HINT_FONT, foreground="gray", padding=(5, 2)).pack(anchor="w")

    btns = ttk.Frame(body); btns.pack(fill=X, pady=(4, 0))
    done_btn = ttk.Button(btns, text="Done", bootstyle="primary", command=dlg.destroy)
    done_btn.pack(side=RIGHT)
    if files:
        ttk.Button(btns, text="Open Folder", bootstyle="outline", command=lambda: open_folder(os.path.dirname(files[0]))).pack(side=RIGHT, padx=8)
    dlg.bind("<Escape>", lambda e: dlg.destroy()); dlg.bind("<Return>", lambda e: dlg.destroy())
    dlg.grab_set(); done_btn.focus_set()
    dlg.wait_window()

def short_hash(path):
    h = sha256_file(path)
    return f"{h[:6]}…{h[-4:]}" if h else "unavailable"
