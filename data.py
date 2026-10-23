# -*- coding: utf-8 -*-
"""M-VAST 3 - CSV data/score logging handlers.

Output changes are additive only: existing rows and columns keep their names
and order. New header rows push the trial table down, so analysis scripts
should locate it by its header line ('Trial_Number_Overall,...'), not by row
number."""

import os
import re
import csv
import glob
import random
import hashlib
from datetime import datetime, timedelta

from config import APP_VERSION, BRIGHTNESS_LEVELS_BASE, BRIGHT_THRESHOLD

TRIAL_COLUMNS = ['Trial_Number_Overall', 'Block_Number', 'Trial_In_Block', 'Brightness_Factor',
                 'Stimulus_Duration_s', 'Fixation_Duration_s', 'Checkerboard_Hz',
                 'Discomfort_Rating_0_100', 'Brightness_Rating_0_100', 'Response_Timestamp']
# v2 per-trial timing columns, appended after the original ten.
TIMING_COLUMNS = ['Stim_Onset_s', 'Stim_Offset_s', 'Actual_Stimulus_Duration_s', 'N_Flips',
                  'Median_Interval_ms', 'Min_Interval_ms', 'Max_Interval_ms',
                  'N_Intervals_Over_1p5x', 'N_Intervals_Under_0p5x']
EXTRA_TRIAL_COLUMNS = ['Focus_Lost_Events']

# --- Helpers ---
def sha256_file(path):
    """Hex SHA-256 of a file, or "" if it can't be read."""
    try:
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(1 << 20), b''): h.update(chunk)
        return h.hexdigest()
    except OSError:
        return ""

def _fmt_hz(hz):
    return f"{hz:.2f}" if hz else ""

def _fmt_size(size):
    return f"{size[0]}x{size[1]}" if size else ""

def _wall(t):
    return t.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] if t else ""

def read_run_status(path):
    """(Run_Status, Trials_Completed) from an existing data file. A file
    without a Run_Status row died mid-run (or predates v2)."""
    status, completed = "", ""
    try:
        with open(path, newline='', encoding='utf-8', errors='replace') as f:
            for row in csv.reader(f):
                if len(row) >= 2 and row[0] == 'Run_Status': status = row[1]
                elif len(row) >= 2 and row[0] == 'Trials_Completed': completed = row[1]
    except (OSError, csv.Error):
        pass
    return status or "no status (process ended mid-run)", completed

def find_existing_runs(log_dir, participant_id):
    """Data files already written for this exact participant ID, newest first.
    Matches the full name pattern so ID "1" doesn't pick up "1_2" or "10"."""
    if not (log_dir and participant_id): return []
    exact = re.compile(rf"(data|tonic)_P{re.escape(participant_id)}_\d{{8}}_\d{{6}}\.csv")
    candidates = glob.glob(os.path.join(glob.escape(log_dir), f"*_P{glob.escape(participant_id)}_*.csv"))
    files = [p for p in candidates if exact.fullmatch(os.path.basename(p))]
    return sorted(files, key=os.path.getmtime, reverse=True)

def count_runs_using_master(participant_dir, master_csv_name):
    """How many participant data files in `participant_dir` used this master CSV."""
    n = 0
    for path in glob.glob(os.path.join(glob.escape(participant_dir), "data_P*.csv")):
        try:
            with open(path, newline='', encoding='utf-8', errors='replace') as f:
                for i, row in enumerate(csv.reader(f)):
                    if len(row) >= 2 and row[0] == 'Master_CSV_Used':
                        n += row[1] == master_csv_name; break
                    if i > 20: break
        except (OSError, csv.Error):
            pass
    return n

def build_randomized_schedule(num_blocks, seed, space_bright=True, max_attempts=1000):
    """Brightness factors for the randomized blocks: each block is a shuffle of
    BRIGHTNESS_LEVELS_BASE. With space_bright, each block is reshuffled until no
    two factors >= BRIGHT_THRESHOLD are adjacent, including across the boundary
    with the previous block (or the ramp-up's final, brightest trial).
    Deterministic for a given seed, so the standard order can be regenerated
    exactly."""
    def spaced(seq):
        return all(not (a >= BRIGHT_THRESHOLD and b >= BRIGHT_THRESHOLD) for a, b in zip(seq, seq[1:]))
    rng = random.Random(seed)
    order, prev = [], BRIGHTNESS_LEVELS_BASE[-1]
    for _ in range(num_blocks):
        block = BRIGHTNESS_LEVELS_BASE[:]
        for _ in range(max_attempts):
            rng.shuffle(block)
            if not space_bright or spaced([prev] + block): break
        else:
            raise RuntimeError("Could not build a spaced order; try another seed.")
        order.extend(block); prev = block[-1]
    return order

# --- Data Handlers ---
class ParticipantDataHandler:
    """Trial-by-trial log for a standard run. Each row is flushed and fsynced;
    a failed write raises so the runner halts with Run_Status=error."""
    def __init__(self, log_dir_participant, participant_id, master_csv_path, image1_path, image2_path,
                 trials_expected=None, display_info=None, display_check=""):
        self.log_dir = log_dir_participant
        self.participant_id = participant_id
        self.master_csv_name = os.path.basename(master_csv_path)
        self.image1_name = os.path.basename(image1_path)
        self.image2_name = os.path.basename(image2_path)
        self.file, self.writer = None, None
        self.status = "error"   # until the runner says otherwise
        self.trials_completed = 0
        display_info = display_info or {}
        os.makedirs(self.log_dir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.filename = os.path.join(self.log_dir, f"data_P{self.participant_id}_{ts}.csv")
        self.file = open(self.filename, 'w', newline='', encoding='utf-8')
        self.writer = csv.writer(self.file)
        exp_id_from_master = self.master_csv_name.split('_master_trials.csv')[0] if '_master_trials.csv' in self.master_csv_name else 'UnknownExpID'
        self.writer.writerows([
            ['App_Version', APP_VERSION],
            ['Experiment_ID', exp_id_from_master], ['Participant_ID', self.participant_id],
            ['Timestamp_Start_Run', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            ['Master_CSV_Used', self.master_csv_name],
            ['Image1_File', self.image1_name],
            ['Image2_File', self.image2_name],
            # v2 header rows
            ['Master_CSV_Path', os.path.abspath(master_csv_path)],
            ['Master_CSV_SHA256', sha256_file(master_csv_path)],
            ['Trials_Expected', trials_expected if trials_expected is not None else ""],
            ['Display_Size', _fmt_size(display_info.get('size'))],
            ['Display_Refresh_Hz_OS', _fmt_hz(display_info.get('refresh_hz_os'))],
            ['Display_Check', display_check],
            ['Display_Index', display_info.get('display_index', "")],
            ['Display_Refresh_Hz_Measured', _fmt_hz(display_info.get('refresh_hz_measured'))],
            ['Vsync', 'yes' if display_info.get('vsync') else 'no'],
            ['Image1_SHA256', sha256_file(image1_path)],
            ['Image2_SHA256', sha256_file(image2_path)],
            [],
            TRIAL_COLUMNS + TIMING_COLUMNS + EXTRA_TRIAL_COLUMNS,
        ])
        self._sync()
        print(f"Logging data to: {self.filename}")

    def _sync(self):
        self.file.flush()
        os.fsync(self.file.fileno())

    def save_trial_response(self, trial_info, discomfort, brightness_rating, timing=None, focus_events=0):
        """Write one trial row. Raises on failure (e.g. a USB drive dropped)."""
        if not self.writer: raise IOError("Data log is not open.")
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        timing = timing or {}
        self.writer.writerow([
            trial_info['trial_number'], trial_info['block_number'], trial_info['trial_in_block'],
            f"{trial_info['brightness_factor']:.2f}", trial_info['stimulus_duration'],
            trial_info['fixation_duration'], trial_info['checkerboard_hz'],
            int(discomfort), int(brightness_rating), ts]
            + [timing.get(c, "") for c in TIMING_COLUMNS] + [focus_events])
        self._sync()
        self.trials_completed += 1

    def close(self):
        if self.file:
            try:
                if self.writer:
                    self.writer.writerows([
                        ['Run_Status', self.status],
                        ['Trials_Completed', self.trials_completed],
                        ['Timestamp_End_Run', datetime.now().strftime('%Y-%m-%d %H:%M:%S')]])
                self.file.close()
                print("Participant data log closed.")
            except Exception as e: print(f"Error closing data log: {e}")
            finally: self.file = None; self.writer = None

class ParticipantScoreHandler:
    def __init__(self, log_dir_participant, participant_id):
        self.total_discomfort, self.total_brightness, self.num_ratings = 0.0, 0.0, 0
        self.log_dir, self.participant_id = log_dir_participant, participant_id
        self.filename = None

    def add_ratings(self, discomfort, brightness_rating):
        try: self.total_discomfort += float(discomfort); self.total_brightness += float(brightness_rating); self.num_ratings += 1
        except (ValueError, TypeError) as e: print(f"Skipped invalid rating (D:{discomfort}, B:{brightness_rating}). Err: {e}")

    def get_average_scores(self):
        return (self.total_discomfort / self.num_ratings, self.total_brightness / self.num_ratings) if self.num_ratings > 0 else (0.0, 0.0)

    def save_final_scores(self, status=""):
        if self.num_ratings == 0: print("No ratings, skipping score save."); return
        avg_d, avg_b = self.get_average_scores()
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        fn = os.path.join(self.log_dir, f"summary_P{self.participant_id}_avg_scores_{ts}.csv")
        try:
            with open(fn, 'w', newline='', encoding='utf-8') as f:
                csv.writer(f).writerows([
                    ['Participant_ID', self.participant_id], ['Timestamp_Summary', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                    ['Number_Of_Rated_Trials', self.num_ratings], [], ['Metric', 'Average_Score_0_100'],
                    ['Average_Discomfort', f"{avg_d:.2f}"], ['Average_Brightness', f"{avg_b:.2f}"],
                    [], ['Run_Status', status]])
            self.filename = fn
            print(f"Average scores saved to: {fn}")
        except Exception as e: print(f"Error saving summary scores {fn}: {e}")

class TonicDataHandler:
    """Writes a single-file timing log for a tonic fMRI run. There are no
    trial-by-trial ratings; the key outputs are the run parameters and the
    trigger / stimulus onset & offset timestamps for fMRI alignment. The file
    is first written at trigger receipt (Run_Status=running) and rewritten at
    the end, so a crash still leaves the trigger time on disk."""
    def __init__(self, config, display_info=None, display_check=""):
        self.config = config
        self.display_info = display_info or {}
        self.display_check = display_check
        self.log_dir = config.log_dir_participant
        os.makedirs(self.log_dir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.filename = os.path.join(self.log_dir, f"tonic_P{config.participant_id}_{ts}.csv")

    def save(self, trigger_wall=None, trigger_perf=None, stim_end_perf=None, status="unknown",
             flip_stats=None, pulses=None, raise_errors=False):
        """Persist run metadata and timing. Times are recorded both as wall
        clock and as a monotonic clock (seconds) relative to the scanner
        trigger. `flip_stats` comes from stimulus.summarize_flips with the
        trigger as reference; `pulses` are perf times of trigger keystrokes
        received during the stimulus."""
        flip_stats = flip_stats or {}
        pulses = pulses or []
        def rel(perf):
            if perf is None or trigger_perf is None: return ""
            return f"{perf - trigger_perf:.3f}"
        def wall_at(perf):
            if perf is None or trigger_perf is None or trigger_wall is None: return ""
            return _wall(trigger_wall + timedelta(seconds=perf - trigger_perf))
        onset_rel = flip_stats.get('Stim_Onset_s', "")
        onset_perf = trigger_perf + float(onset_rel) if (onset_rel != "" and trigger_perf is not None) else None
        actual_duration = ""
        if onset_perf is not None and stim_end_perf is not None:
            actual_duration = f"{stim_end_perf - onset_perf:.3f}"
        rows = [
            ['App_Version', APP_VERSION],
            ['Run_Type', 'Tonic_fMRI'],
            ['Participant_ID', self.config.participant_id],
            ['Scanner_Site', self.config.scanner],
            ['Image1_File', os.path.basename(self.config.image1_path)],
            ['Image2_File', os.path.basename(self.config.image2_path)],
            ['Constant_Brightness', f"{self.config.brightness:.2f}"],
            ['Flicker_Hz', f"{self.config.hz:.2f}"],
            ['Requested_Duration_s', f"{self.config.duration:.2f}"],
            ['Trigger_Key', self.config.trigger_key],
            ['Fixation_Cross_Overlay', 'yes' if getattr(self.config, 'show_fixation', False) else 'no'],
            ['Run_Status', status],
            # v2 header rows
            ['Display_Size', _fmt_size(self.display_info.get('size'))],
            ['Display_Refresh_Hz_OS', _fmt_hz(self.display_info.get('refresh_hz_os'))],
            ['Display_Check', self.display_check],
            ['Display_Index', self.display_info.get('display_index', "")],
            ['Display_Refresh_Hz_Measured', _fmt_hz(self.display_info.get('refresh_hz_measured'))],
            ['Vsync', 'yes' if self.display_info.get('vsync') else 'no'],
            ['Image1_SHA256', sha256_file(self.config.image1_path)],
            ['Image2_SHA256', sha256_file(self.config.image2_path)],
            [],
            ['Event', 'Wall_Clock', 'Seconds_Relative_To_Trigger'],
            ['Scanner_Trigger_Received', _wall(trigger_wall), rel(trigger_perf)],
            ['Stimulus_Onset', wall_at(onset_perf), rel(onset_perf)],
            ['Stimulus_Offset', wall_at(stim_end_perf), rel(stim_end_perf)],
            ['Actual_Stimulus_Duration_s', "", actual_duration],
            # v2 event rows
            ['Pre_Stimulus_Gap_s', "", rel(onset_perf)],
            ['N_Flips', "", flip_stats.get('N_Flips', "")],
            ['Median_Interval_ms', "", flip_stats.get('Median_Interval_ms', "")],
            ['Min_Interval_ms', "", flip_stats.get('Min_Interval_ms', "")],
            ['Max_Interval_ms', "", flip_stats.get('Max_Interval_ms', "")],
            ['N_Intervals_Over_1p5x', "", flip_stats.get('N_Intervals_Over_1p5x', "")],
            ['N_Intervals_Under_0p5x', "", flip_stats.get('N_Intervals_Under_0p5x', "")],
            ['Focus_Lost_Events', "", flip_stats.get('Focus_Lost_Events', "")],
            ['N_Trigger_Pulses_During_Run', "", len(pulses) if status != "running" else ""],
        ] + [['Scanner_Pulse', wall_at(p), rel(p)] for p in pulses]
        try:
            with open(self.filename, 'w', newline='', encoding='utf-8') as f:
                csv.writer(f).writerows(rows)
                f.flush(); os.fsync(f.fileno())
            print(f"Tonic run log saved to: {self.filename}")
        except Exception as e:
            print(f"Error saving tonic log {self.filename}: {e}")
            if raise_errors: raise
