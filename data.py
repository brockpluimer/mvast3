# -*- coding: utf-8 -*-
"""M-VAST 3 - CSV data/score logging handlers."""

import os
import csv
from datetime import datetime
from tkinter import messagebox

from config import APP_VERSION

# --- Data Handlers ---
class ParticipantDataHandler:
    def __init__(self, log_dir_participant, participant_id, master_csv_path, image1_path, image2_path):
        self.log_dir = log_dir_participant 
        self.participant_id = participant_id
        self.master_csv_name = os.path.basename(master_csv_path)
        self.image1_name = os.path.basename(image1_path)
        self.image2_name = os.path.basename(image2_path)
        self.file, self.writer = None, None
        os.makedirs(self.log_dir, exist_ok=True) 
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(self.log_dir, f"data_P{self.participant_id}_{ts}.csv")
        try:
            self.file = open(filename, 'w', newline='', encoding='utf-8')
            self.writer = csv.writer(self.file)
            exp_id_from_master = self.master_csv_name.split('_master_trials.csv')[0] if '_master_trials.csv' in self.master_csv_name else 'UnknownExpID'
            self.writer.writerows([
                ['App_Version', APP_VERSION],
                ['Experiment_ID', exp_id_from_master], ['Participant_ID', self.participant_id],
                ['Timestamp_Start_Run', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                ['Master_CSV_Used', self.master_csv_name], 
                ['Image1_File', self.image1_name], 
                ['Image2_File', self.image2_name], 
                [],
                ['Trial_Number_Overall', 'Block_Number', 'Trial_In_Block', 'Brightness_Factor',
                 'Stimulus_Duration_s', 'Fixation_Duration_s', 'Checkerboard_Hz',
                 'Discomfort_Rating_0_100', 'Brightness_Rating_0_100', 'Response_Timestamp']
            ])
            print(f"Logging data to: {filename}")
        except IOError as e: messagebox.showerror("File Error", f"Cannot open log {filename}:\n{e}"); raise

    def save_trial_response(self, trial_info, discomfort, brightness_rating):
        if not self.writer: print("DataHandler not init."); return
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        try:
            self.writer.writerow([
                trial_info['trial_number'], trial_info['block_number'], trial_info['trial_in_block'],
                f"{trial_info['brightness_factor']:.2f}", trial_info['stimulus_duration'],
                trial_info['fixation_duration'], trial_info['checkerboard_hz'],
                int(discomfort), int(brightness_rating), ts])
            self.file.flush()
        except Exception as e: print(f"Error writing trial to CSV: {e}")

    def close(self):
        if self.file:
            try:
                if self.writer: self.writer.writerow(['Timestamp_End_Run', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
                self.file.close(); self.file = None; self.writer = None
                print("Participant data log closed.")
            except Exception as e: print(f"Error closing data log: {e}")

class ParticipantScoreHandler:
    def __init__(self, log_dir_participant, participant_id):
        self.total_discomfort, self.total_brightness, self.num_ratings = 0.0, 0.0, 0
        self.log_dir, self.participant_id = log_dir_participant, participant_id 
        
    def add_ratings(self, discomfort, brightness_rating):
        try: self.total_discomfort += float(discomfort); self.total_brightness += float(brightness_rating); self.num_ratings += 1
        except (ValueError, TypeError) as e: print(f"Skipped invalid rating (D:{discomfort}, B:{brightness_rating}). Err: {e}")
    
    def get_average_scores(self):
        return (self.total_discomfort / self.num_ratings, self.total_brightness / self.num_ratings) if self.num_ratings > 0 else (0.0, 0.0)
    
    def save_final_scores(self):
        if self.num_ratings == 0: print("No ratings, skipping score save."); return
        avg_d, avg_b = self.get_average_scores()
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        fn = os.path.join(self.log_dir, f"summary_P{self.participant_id}_avg_scores_{ts}.csv") 
        try:
            with open(fn, 'w', newline='', encoding='utf-8') as f:
                csv.writer(f).writerows([
                    ['Participant_ID', self.participant_id], ['Timestamp_Summary', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                    ['Number_Of_Rated_Trials', self.num_ratings], [], ['Metric', 'Average_Score_0_100'],
                    ['Average_Discomfort', f"{avg_d:.2f}"], ['Average_Brightness', f"{avg_b:.2f}"]])
            print(f"Average scores saved to: {fn}")
        except Exception as e: print(f"Error saving summary scores {fn}: {e}")

class TonicDataHandler:
    """Writes a single-file timing log for a tonic fMRI run. There are no
    trial-by-trial ratings; the key outputs are the run parameters and the
    trigger / stimulus onset & offset timestamps for fMRI alignment."""
    def __init__(self, config):
        self.config = config
        self.log_dir = config.log_dir_participant
        os.makedirs(self.log_dir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.filename = os.path.join(self.log_dir, f"tonic_P{config.participant_id}_{ts}.csv")

    def save(self, trigger_wall=None, trigger_perf=None, stim_end_perf=None, status="unknown"):
        """Persist run metadata and timing. Times are recorded both as wall
        clock and as a monotonic clock (seconds) so onset/offset can be
        expressed relative to the scanner trigger."""
        def rel(perf):
            if perf is None or trigger_perf is None: return ""
            return f"{perf - trigger_perf:.3f}"
        actual_duration = ""
        if trigger_perf is not None and stim_end_perf is not None:
            actual_duration = f"{stim_end_perf - trigger_perf:.3f}"
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
            [],
            ['Event', 'Wall_Clock', 'Seconds_Relative_To_Trigger'],
            ['Scanner_Trigger_Received',
             trigger_wall.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] if trigger_wall else "",
             rel(trigger_perf)],
            ['Stimulus_Onset',
             trigger_wall.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] if trigger_wall else "",
             rel(trigger_perf)],
            ['Stimulus_Offset', "", rel(stim_end_perf)],
            ['Actual_Stimulus_Duration_s', "", actual_duration],
        ]
        try:
            with open(self.filename, 'w', newline='', encoding='utf-8') as f:
                csv.writer(f).writerows(rows)
            print(f"Tonic run log saved to: {self.filename}")
        except Exception as e:
            print(f"Error saving tonic log {self.filename}: {e}")

