# -*- coding: utf-8 -*-
"""M-VAST 3 - experiment run orchestration (standard and tonic fMRI).

Both run functions return a result dict for the post-run summary:
status ('completed' / 'aborted' / 'error'), counts, timing QC, the files
written, and a message describing what stopped the run, if anything."""

import time
import traceback
import pygame

from data import (
    ParticipantDataHandler, ParticipantScoreHandler, TonicDataHandler,
)
from stimulus import (
    open_display, display_check_result, load_checkerboard_images,
    adjust_surface_brightness, build_brightness_cache, make_fixation_overlay,
    show_message, show_fixation, run_flicker, summarize_flips,
    get_rating_with_click, wait_for_scanner_trigger, take_focus_events,
)

def _new_result(**extra):
    result = {'status': 'error', 'message': '', 'files': [], 'display_info': {},
              'display_check': '', 'focus_events': 0, 'elapsed_s': 0.0}
    result.update(extra)
    return result

def _show_stop_screen(screen, text, wait_ms):
    if screen and pygame.display.get_init():
        show_message(screen, text, wait_for_key=False); pygame.time.wait(wait_ms)

# --- Main Experiment Execution Function ---
def execute_experiment_run(run_config):
    trials = run_config.trials_data
    result = _new_result(trials_expected=len(trials), trials_completed=0,
                         flagged_trials=[], avg_discomfort=None, avg_brightness=None)
    t_start = time.perf_counter()
    try:
        screen, info = open_display(run_config.display_index, "M-VAST 3 Visual Stimulus")
    except (pygame.error, RuntimeError) as e:
        if pygame.get_init(): pygame.quit()
        result['message'] = f"Could not open the stimulus display: {e}"
        return result
    result['display_info'] = info
    result['display_check'] = display_check_result(info['size'], run_config.display_mismatch_accepted)

    data_h, score_h = None, None
    try:
        data_h = ParticipantDataHandler(run_config.log_dir_participant, run_config.participant_id,
                                        run_config.master_csv_path, run_config.image1_path, run_config.image2_path,
                                        trials_expected=len(trials), display_info=info,
                                        display_check=result['display_check'])
        result['files'].append(data_h.filename)
        score_h = ParticipantScoreHandler(run_config.log_dir_participant, run_config.participant_id)
        board1, board2 = load_checkerboard_images(*info['size'], run_config.image1_path, run_config.image2_path)
        boards = build_brightness_cache(board1, board2, [t['brightness_factor'] for t in trials])

        instructions = f"""Welcome, Participant {run_config.participant_id}.

In this experiment you will be shown a series of visual stimuli.

Please keep your eyes focused on the center of the screen.

You will be asked to rate the unpleasantness and the brightness of each stimulus.

After the stimulus, use the mouse to adjust the slider bar to give your ratings and then click CONFIRM.


Press the ESC key at any time to stop the experiment.


Press any key to begin..."""
        if not show_message(screen, instructions): raise KeyboardInterrupt("Quit: instructions.")
        t_ref = time.perf_counter()   # participant's start keypress; timing columns are relative to this
        take_focus_events()

        for params in trials:
            trial_num, bf, sd, fd, hz = (params['trial_number'], params['brightness_factor'],
                                         params['stimulus_duration'], params['fixation_duration'],
                                         params['checkerboard_hz'])
            if not show_fixation(screen, fd): raise KeyboardInterrupt("Quit: fixation")
            stim = run_flicker(screen, *boards[bf], sd, hz, frame_period=info['frame_period'])
            if not stim.completed: raise KeyboardInterrupt("Quit: stimulus")
            timing = summarize_flips(stim, hz, t_ref)

            discomfort = get_rating_with_click(screen, "", "unpleasantness")
            if discomfort is None: raise KeyboardInterrupt("Quit: discomfort rating")

            brightness_rating = get_rating_with_click(screen, "", "brightness")
            if brightness_rating is None: raise KeyboardInterrupt("Quit: brightness rating")

            focus = take_focus_events()
            data_h.save_trial_response(params, discomfort, brightness_rating, timing, focus)
            score_h.add_ratings(discomfort, brightness_rating)
            result['focus_events'] += focus
            if timing['N_Intervals_Over_1p5x'] or timing['N_Intervals_Under_0p5x']:
                result['flagged_trials'].append({'trial': trial_num, 'brightness': bf,
                                                 'max_ms': timing['Max_Interval_ms'], 'min_ms': timing['Min_Interval_ms'],
                                                 'over': timing['N_Intervals_Over_1p5x'],
                                                 'under': timing['N_Intervals_Under_0p5x']})

        data_h.status = result['status'] = 'completed'
        print("\n===== All Trials Complete =====")
        show_message(screen, "Experiment complete. Thank you!\nWindow will close shortly.", wait_for_key=False)
        pygame.time.wait(4000)
    except KeyboardInterrupt as ki:
        result['status'] = 'aborted'; result['message'] = str(ki)
        _show_stop_screen(screen, "Experiment stopped.", 2000)
        print(f"\n--- User Terminated ({ki}) ---")
    except (RuntimeError, OSError, pygame.error) as e:
        result['status'] = 'error'; result['message'] = str(e)
        _show_stop_screen(screen, f"Error:\n{e}\nStopped.", 5000)
        print(f"\n--- Halted (Error): {e} ---")
    except Exception as e:
        result['status'] = 'error'; result['message'] = f"{type(e).__name__}: {e}"
        _show_stop_screen(screen, f"Unexpected error:\n{type(e).__name__}\nStopped.", 5000)
        print(f"\n--- Unexpected Error: {type(e).__name__}: {e} ---"); traceback.print_exc()
    finally:
        print("\n--- Cleaning Up ---")
        if data_h:
            data_h.status = result['status']
            result['trials_completed'] = data_h.trials_completed
            data_h.close()
        if score_h:
            score_h.save_final_scores(result['status'])
            if score_h.num_ratings:
                result['avg_discomfort'], result['avg_brightness'] = score_h.get_average_scores()
            if score_h.filename: result['files'].append(score_h.filename)
        if pygame.get_init(): pygame.quit(); print("Pygame closed.")
        result['elapsed_s'] = time.perf_counter() - t_start
    return result

# --- Tonic fMRI Run Execution Function ---
def execute_tonic_run(config):
    """Run a single continuous, constant-brightness flicker synced to the
    scanner trigger, concurrent with fMRI. No button responses are collected."""
    result = _new_result(onset_gap_s=None, flip_stats={}, n_pulses=0)
    t_start = time.perf_counter()
    try:
        screen, info = open_display(config.display_index, "M-VAST 3 Tonic fMRI")
    except (pygame.error, RuntimeError) as e:
        if pygame.get_init(): pygame.quit()
        result['message'] = f"Could not open the stimulus display: {e}"
        return result
    result['display_info'] = info
    result['display_check'] = display_check_result(info['size'], config.display_mismatch_accepted)

    data_h = TonicDataHandler(config, info, result['display_check'])
    result['files'].append(data_h.filename)
    trigger_wall = trigger_perf = stim_end_perf = None
    flip_stats, pulses = {}, []
    try:
        board1, board2 = load_checkerboard_images(*info['size'], config.image1_path, config.image2_path)
        b1 = adjust_surface_brightness(board1, config.brightness)
        b2 = adjust_surface_brightness(board2, config.brightness)
        overlay = make_fixation_overlay(screen) if config.show_fixation else None

        intro = (f"Tonic M-VAST + fMRI\n\n"
                 f"Participant {config.participant_id}  |  {config.scanner}\n\n"
                 f"Please keep your eyes focused on the central cross (+) for the entire run.\n\n"
                 f"The screen will flicker continuously for about {config.duration / 60.0:.1f} minutes.\n\n"
                 f"Operator: press SPACE when ready to arm the scanner trigger...")
        # Only SPACE continues: a scanner already sending pulses must not
        # dismiss this screen and use up a volume.
        if not show_message(screen, intro, continue_keys=(pygame.K_SPACE,)):
            raise KeyboardInterrupt("Quit: intro")

        trig = wait_for_scanner_trigger(screen, config.trigger_key)
        if trig is None: raise KeyboardInterrupt("Quit: waiting for trigger")
        trigger_wall, trigger_perf = trig
        print(f"Scanner trigger received at {trigger_wall}. Starting tonic stimulus.")
        data_h.save(trigger_wall=trigger_wall, trigger_perf=trigger_perf, status="running", raise_errors=True)

        take_focus_events()
        stim = run_flicker(screen, b1, b2, config.duration, config.hz, frame_period=info['frame_period'],
                           overlay=overlay, trigger_key=config.trigger_key)
        stim_end_perf, pulses = stim.offset, stim.pulses
        flip_stats = summarize_flips(stim, config.hz, trigger_perf)
        flip_stats['Focus_Lost_Events'] = result['focus_events'] = take_focus_events()
        if not stim.completed:
            raise KeyboardInterrupt("Quit: stimulus")

        result['status'] = 'completed'
        print("\n===== Tonic Run Complete =====")
        show_message(screen, "Run complete. Thank you!\nWindow will close shortly.", wait_for_key=False)
        pygame.time.wait(3000)
    except KeyboardInterrupt as ki:
        result['status'] = 'aborted'; result['message'] = str(ki)
        if stim_end_perf is None and trigger_perf is not None: stim_end_perf = time.perf_counter()
        _show_stop_screen(screen, "Run stopped.", 2000)
        print(f"\n--- User Terminated ({ki}) ---")
    except (RuntimeError, OSError, pygame.error) as e:
        result['status'] = 'error'; result['message'] = str(e)
        _show_stop_screen(screen, f"Error:\n{e}\nStopped.", 5000)
        print(f"\n--- Halted (Error): {e} ---")
    except Exception as e:
        result['status'] = 'error'; result['message'] = f"{type(e).__name__}: {e}"
        _show_stop_screen(screen, f"Unexpected error:\n{type(e).__name__}\nStopped.", 5000)
        print(f"\n--- Unexpected Error: {type(e).__name__}: {e} ---"); traceback.print_exc()
    finally:
        print("\n--- Cleaning Up ---")
        data_h.save(trigger_wall=trigger_wall, trigger_perf=trigger_perf, stim_end_perf=stim_end_perf,
                    status=result['status'], flip_stats=flip_stats, pulses=pulses)
        if pygame.get_init(): pygame.quit(); print("Pygame closed.")
        result['flip_stats'] = flip_stats
        result['n_pulses'] = len(pulses)
        if flip_stats.get('Stim_Onset_s', "") != "": result['onset_gap_s'] = float(flip_stats['Stim_Onset_s'])
        result['elapsed_s'] = time.perf_counter() - t_start
    return result
