# -*- coding: utf-8 -*-
"""M-VAST 3 - application constants, paths, and run configuration objects."""

import sys
import os

# --- PyInstaller Helper for Data Files ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for a portable app folder. """
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        base_path = os.path.abspath(".")

    full_path = os.path.join(base_path, relative_path)
    print(f"DEBUG: Trying to load resource from: {full_path}")
    return full_path
    
# --- Application Constants ---
APP_VERSION = "v1.0_2025_06_18"

DEFAULT_LOG_DIR_BASE_NAME = "experiment_data" 
DEFAULT_LOG_DIR_PARTICIPANT_NAME = "participant_runs" 

if getattr(sys, 'frozen', False): 
    APP_BASE_PATH = os.path.dirname(sys.executable)
else: 
    APP_BASE_PATH = os.path.abspath(".") 

DEFAULT_LOG_DIR_BASE = os.path.join(APP_BASE_PATH, DEFAULT_LOG_DIR_BASE_NAME)
DEFAULT_LOG_DIR_PARTICIPANT = os.path.join(DEFAULT_LOG_DIR_BASE, DEFAULT_LOG_DIR_PARTICIPANT_NAME)

SCHEDULES_SUBDIR = "randomization_schedules"
SETUPS_SUBDIR = "experiment_setups"
HELP_FILE_NAME = "mvast3_manual.html" 

DEFAULT_STIMULUS_DURATION = 10.0
DEFAULT_FIXATION_DURATION = 8.0
DEFAULT_CHECKERBOARD_HZ = 7.5
DEFAULT_RANDOMIZED_BLOCKS_COUNT = 3

# --- Tonic fMRI run defaults ---
# A single continuous, constant-brightness flickering run designed to be
# acquired concurrently with fMRI (see collaborator protocol: structural ->
# rsfMRI -> H-MRS -> tonic M-VAST + fMRI -> rsfMRI).
DEFAULT_TONIC_DURATION = 360.0        # seconds (~6 minutes)
DEFAULT_TONIC_BRIGHTNESS = 1.0        # constant brightness (1.0 = full)
DEFAULT_TONIC_HZ = DEFAULT_CHECKERBOARD_HZ
DEFAULT_TRIGGER_KEY = "5"             # scanner TTL pulse is delivered as this keystroke

BRIGHTNESS_LEVELS_BASE = [0.1, 0.2, 0.4, 0.6, 0.8, 1.0]
RAMP_UP_TRIALS_COUNT = len(BRIGHTNESS_LEVELS_BASE)
TRIALS_PER_BLOCK = len(BRIGHTNESS_LEVELS_BASE) 

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 200, 0)
DARK_GREEN = (0, 150, 0)
GRAY_COLOR = (150, 150, 150) 

PYGAME_REFERENCE_SCREEN_HEIGHT = 1080.0

# --- Configuration Classes ---
class RunConfig:
    def __init__(self):
        self.master_csv_path = ""
        self.image1_path = ""
        self.image2_path = ""
        self.participant_id = ""
        self.log_dir_participant = DEFAULT_LOG_DIR_PARTICIPANT
        self.trials_data = []

class TonicRunConfig:
    def __init__(self):
        self.participant_id = ""
        self.scanner = ""
        self.image1_path = ""
        self.image2_path = ""
        self.brightness = DEFAULT_TONIC_BRIGHTNESS
        self.hz = DEFAULT_TONIC_HZ
        self.duration = DEFAULT_TONIC_DURATION
        self.trigger_key = DEFAULT_TRIGGER_KEY
        self.log_dir_participant = DEFAULT_LOG_DIR_PARTICIPANT

