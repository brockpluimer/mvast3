# M-VAST 3 v2: test plan for the rig

Branch: `v2-updates`. This covers every item in the v2 update list (run integrity, header and timing columns, tonic fixes, display handling, smaller fixes, docs) plus the issues found in review. The output format is **additive only**: every v1 row and column keeps its name and place. The trial table moves down 11 rows, so find it by its header line.

**Rating scales are unchanged from v1.** Prompts, anchors (0 "Not Unpleasant" / 100 "Most Unpleasant Image Imaginable"; 0 "No Image Visible" / 100 "Brightest Image Imaginable"), the 0–100 range, the slider starting at 0, and Confirm are byte-for-byte the v1 code, and a test fails if they change.

## 1. Setup

```bash
git fetch origin && git checkout v2-updates
python -m pip install pygame pillow numpy ttkbootstrap pytest
python -m pytest            # expect all tests to pass, in about 20 s
python mvast3.py
```

## 2. Already verified (macOS, 120 Hz built-in display, pygame 2.6.1)

- **Automated suite:** about 200 tests pass on Python 3.12 and 3.13. On 3.9, everything except the windowed tests passes (that macOS Python's Tk can't open windows).
- **Real full-screen standard run:**
  - vsync engaged and the refresh rate measured 119.9 Hz;
  - every trial's `Actual_Stimulus_Duration_s` was exactly the requested duration;
  - the median interval was 66.6–66.8 ms (8 frames), with no intervals flagged long or short;
  - stealing focus mid-trial was logged as `Focus_Lost_Events = 1` and the run continued.
- **Real tonic run driven by OS-level keystrokes:**
  - `5` pulses before the intro were ignored, and only SPACE continued;
  - the first frame came 3.8 ms after the trigger;
  - every pulse during the run was logged as a `Scanner_Pulse` row.
- **Real GUI → full-screen → GUI hand-off:** two sessions in a row worked.
- **Simulated stalls of 5–1000 ms,** plus about 15,000 randomized timing runs: a stall always shows as one long interval and never as a brief flash.

## 3. Please check on the Windows PC + EIZO

Display scaling must be **100%** on the EIZO. Put the dates and results in the right-hand column.

| # | Do | Expect | Result |
|---|---|---|---|
| 1 | Set up Extend mode with the laptop as the main display, then open Run Experiment | The Display list shows both screens. **Identify** shows "1" and "2" on the matching screens. | |
| 2 | Pick the EIZO and read the Pre-flight Check | "Display N is 1600×1200, matches the protocol"; "Refresh 60 Hz: 7.5 Hz flicker = exactly 4 frames per half-cycle" | |
| 3 | Pick the laptop panel and press Start | The Display Check dialog appears **in the GUI** (not behind a black screen). Cancel goes back. | |
| 4 | Run a full session on the EIZO with the canonical images | The task opens **on the EIZO**. The Run Summary says Completed and "Vsync on, refresh measured ≈60 Hz", with no flagged trials. | |
| 5 | Check the data file | `Display_Check = OK 1600x1200`, `Vsync = yes`, `Display_Refresh_Hz_Measured ≈ 60`. Per trial: `Median_Interval_ms ≈ 66.67`, `N_Intervals_Under_0p5x = 0`. | |
| 6 | During a stimulus, click on the laptop screen | The EIZO window **stays up** (not minimized). That trial's `Focus_Lost_Events ≥ 1`. Note whether the participant's next click on the EIZO registers on the first try. | |
| 7 | During a rating, try to move the mouse onto the laptop screen | The cursor stays confined to the EIZO. | |
| 8 | Press ESC mid-trial; separately, Alt+F4 | Both give `Run_Status = aborted` and return to the menu. The app does not quit. | |
| 9 | Unplug the USB drive holding the log folder mid-session | The run stops with an error screen and the summary says Error. If the drive comes back, the file ends with `Run_Status = error`. | |
| 10 | Photodiode on the EIZO for one session | Note the offset between logged `Stim_Onset_s` and light onset, and whether flips are tear-free. | |
| 11 | Photometer: measure each brightness level (0.1 … 1.0) as a still image | Record cd/m² per level. The factor scales pixel values, not luminance. | |

## 4. At the scanner (tonic run)

| # | Do | Expect | Result |
|---|---|---|---|
| 12 | **Test Trigger…**, then start a scan | "✓ Received '5' ×N · interval ≈ TR" | |
| 13 | Start Tonic Run while the scanner is already pulsing | The intro screen does **not** advance on pulses. The operator presses SPACE, then the next pulse starts the run. | |
| 14 | After the run, open the tonic log | `Pre_Stimulus_Gap_s` is a few ms. The `Scanner_Pulse` rows step by the TR. `N_Trigger_Pulses_During_Run` matches the volumes acquired during the run. | |
| 15 | Kill the app mid-run (Task Manager) | The tonic file still exists with `Run_Status = running` and the trigger time. | |

## 5. Questions for you

1. **Header rows.** v2 adds the six rows you specified, in your order, plus `Display_Index`, `Display_Refresh_Hz_Measured`, `Vsync`, `Image1_SHA256` and `Image2_SHA256`, for 11 in total. Is that OK with your CREATE scripts and tests?
2. **Focus.** After a click on the other screen, the task window stays up but isn't the focused window, so a participant's first click or key press may go elsewhere. Should the task take focus back automatically during a run, or is logging it enough?
3. **Your PRs.** Column names and order follow your spec, so your tests should mostly apply. Please run them against this branch and tell us what differs.

Automated tests: `python -m pytest`. A longer timing stress run: `MVAST_STRESS_CASES=5000 python -m pytest tests/test_flicker.py -k stress`.
