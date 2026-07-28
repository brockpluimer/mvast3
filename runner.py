# -*- coding: utf-8 -*-
"""M-VAST 3 - experiment run orchestration (standard and tonic fMRI)."""

import time
import pygame
from tkinter import messagebox

from data import (
    ParticipantDataHandler, ParticipantScoreHandler, TonicDataHandler,
)
from stimulus import (
    load_checkerboard_images, show_message, show_fixation,
    run_alternating_stimulus, get_rating_with_click,
    wait_for_scanner_trigger, run_tonic_stimulus,
)

# --- Main Experiment Execution Function ---
def execute_experiment_run(run_config):
    screen = None
    try:
        pygame.init()
        if not pygame.font: pygame.font.init() 
        s_info = pygame.display.Info()
        s_w, s_h = s_info.current_w, s_info.current_h
        flags = pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF
        try: screen = pygame.display.set_mode((s_w, s_h), flags)
        except pygame.error: flags = pygame.FULLSCREEN | pygame.DOUBLEBUF; screen = pygame.display.set_mode((s_w, s_h), flags)
        
        actual_w, actual_h = screen.get_size()
        pygame.display.set_caption("M-VAST 3 Visual Stimulus"); pygame.mouse.set_visible(False)
    except pygame.error as e: messagebox.showerror("Pygame Error", f"Pygame init failed: {e}"); return

    data_h, score_h = None, None
    try:
        data_h = ParticipantDataHandler(run_config.log_dir_participant, run_config.participant_id, 
                                        run_config.master_csv_path, run_config.image1_path, run_config.image2_path)
        score_h = ParticipantScoreHandler(run_config.log_dir_participant, run_config.participant_id)
        board1, board2 = load_checkerboard_images(actual_w, actual_h, run_config.image1_path, run_config.image2_path)
        if not (board1 and board2): raise RuntimeError("Failed to load stimulus images.")

        num_trials = len(run_config.trials_data)
        
        instructions = f"""Welcome, Participant {run_config.participant_id}.

In this experiment you will be shown a series of visual stimuli.

Please keep your eyes focused on the center of the screen.

You will be asked to rate the unpleasantness and the brightness of each stimulus.

After the stimulus, use the mouse to adjust the slider bar to give your ratings and then click CONFIRM.


Press the ESC key at any time to stop the experiment.


Press any key to begin..."""
        if not show_message(screen, instructions): raise KeyboardInterrupt("Quit: instructions.")

        for idx, params in enumerate(run_config.trials_data):
            trial_num, block, t_in_block = params['trial_number'], params['block_number'], params['trial_in_block']
            bf, sd, fd, hz = params['brightness_factor'], params['stimulus_duration'], params['fixation_duration'], params['checkerboard_hz']
            if not show_fixation(screen, fd): raise KeyboardInterrupt("Quit: fixation")
            if not run_alternating_stimulus(screen, board1, board2, sd, hz, bf): raise KeyboardInterrupt("Quit: stimulus")
            
            discomfort = get_rating_with_click(screen, "", "unpleasantness")
            if discomfort is None: raise KeyboardInterrupt("Quit: discomfort rating")
            
            brightness_rating = get_rating_with_click(screen, "", "brightness") 
            if brightness_rating is None: raise KeyboardInterrupt("Quit: brightness rating") 
            
            data_h.save_trial_response(params, discomfort, brightness_rating)
            score_h.add_ratings(discomfort, brightness_rating)

        print("\n===== All Trials Complete =====") 
        show_message(screen, "Experiment complete. Thank you!\nWindow will close shortly.", wait_for_key=False)
        pygame.time.wait(4000)
    except KeyboardInterrupt as ki: 
        if screen: show_message(screen, "Experiment stopped.", wait_for_key=False); pygame.time.wait(2000)
        print(f"\n--- User Terminated ({ki}) ---")
    except (RuntimeError, IOError, pygame.error) as e: 
        if screen: show_message(screen, f"Error:\n{e}\nStopped.", wait_for_key=False); pygame.time.wait(5000)
        print(f"\n--- Halted (Error): {e} ---")
    except Exception as e:
        if screen: show_message(screen, f"Unexpected error:\n{type(e).__name__}\nStopped.", wait_for_key=False); pygame.time.wait(5000)
        print(f"\n--- Unexpected Error: {type(e).__name__}: {e} ---"); import traceback; traceback.print_exc()
    finally:
        print("\n--- Cleaning Up ---")
        if score_h: score_h.save_final_scores()
        if data_h: data_h.close()
        if pygame.get_init(): pygame.quit(); print("Pygame closed.")

# --- Tonic fMRI Run Execution Function ---
def execute_tonic_run(config):
    """Run a single continuous, constant-brightness flicker synced to the
    scanner trigger, concurrent with fMRI. No button responses are collected."""
    screen = None
    try:
        pygame.init()
        if not pygame.font: pygame.font.init()
        s_info = pygame.display.Info()
        s_w, s_h = s_info.current_w, s_info.current_h
        flags = pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF
        try: screen = pygame.display.set_mode((s_w, s_h), flags)
        except pygame.error: flags = pygame.FULLSCREEN | pygame.DOUBLEBUF; screen = pygame.display.set_mode((s_w, s_h), flags)
        actual_w, actual_h = screen.get_size()
        pygame.display.set_caption("M-VAST 3 Tonic fMRI"); pygame.mouse.set_visible(False)
    except pygame.error as e:
        messagebox.showerror("Pygame Error", f"Pygame init failed: {e}"); return

    data_h = TonicDataHandler(config)
    trigger_wall = trigger_perf = stim_end_perf = None
    status = "aborted"
    try:
        board1, board2 = load_checkerboard_images(actual_w, actual_h, config.image1_path, config.image2_path)
        if not (board1 and board2): raise RuntimeError("Failed to load stimulus images.")

        intro = (f"Tonic M-VAST + fMRI\n\n"
                 f"Participant {config.participant_id}  |  {config.scanner}\n\n"
                 f"Please keep your eyes focused on the central cross (+) for the entire run.\n\n"
                 f"The screen will flicker continuously for about {config.duration / 60.0:.1f} minutes.\n\n"
                 f"Press any key when ready to arm the scanner trigger...")
        if not show_message(screen, intro): raise KeyboardInterrupt("Quit: intro")

        trig = wait_for_scanner_trigger(screen, config.trigger_key)
        if trig is None: raise KeyboardInterrupt("Quit: waiting for trigger")
        trigger_wall, trigger_perf = trig
        print(f"Scanner trigger received at {trigger_wall}. Starting tonic stimulus.")

        completed = run_tonic_stimulus(screen, board1, board2, config.duration, config.hz,
                                       config.brightness, show_fixation=config.show_fixation)
        stim_end_perf = time.perf_counter()

        if not completed:
            raise KeyboardInterrupt("Quit: stimulus")

        status = "completed"
        print("\n===== Tonic Run Complete =====")
        show_message(screen, "Run complete. Thank you!\nWindow will close shortly.", wait_for_key=False)
        pygame.time.wait(3000)
    except KeyboardInterrupt as ki:
        if stim_end_perf is None and trigger_perf is not None: stim_end_perf = time.perf_counter()
        if screen: show_message(screen, "Run stopped.", wait_for_key=False); pygame.time.wait(2000)
        print(f"\n--- User Terminated ({ki}) ---")
    except (RuntimeError, IOError, pygame.error) as e:
        if screen: show_message(screen, f"Error:\n{e}\nStopped.", wait_for_key=False); pygame.time.wait(5000)
        print(f"\n--- Halted (Error): {e} ---")
        status = "error"
    except Exception as e:
        if screen: show_message(screen, f"Unexpected error:\n{type(e).__name__}\nStopped.", wait_for_key=False); pygame.time.wait(5000)
        print(f"\n--- Unexpected Error: {type(e).__name__}: {e} ---"); import traceback; traceback.print_exc()
        status = "error"
    finally:
        print("\n--- Cleaning Up ---")
        data_h.save(trigger_wall=trigger_wall, trigger_perf=trigger_perf,
                    stim_end_perf=stim_end_perf, status=status)
        if pygame.get_init(): pygame.quit(); print("Pygame closed.")

