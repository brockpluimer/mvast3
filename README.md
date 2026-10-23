# M-VAST 3

A desktop application for administering the M-VAST 3 (Michigan Visual Aversion Stress Test).

## Overview

This repository contains the complete M-VAST 3 platform, including source code, image assets, and comprehensive documentation. M-VAST 3 is a research tool designed to present visual stimuli and collect subjective ratings from participants in controlled experimental settings.

### Run modes

- **Run Experiment** — the standard behavioral paradigm: ramp-up and randomized blocks of flickering checkerboards at varying brightness, each followed by unpleasantness and brightness ratings.
- **Run Tonic fMRI** — a single continuous, constant-brightness flickering run (default ~6 minutes) with a central fixation cross and **no button responses**, intended to be acquired concurrently with fMRI. The run waits for the scanner trigger keystroke (default `5`) and logs the trigger time and stimulus onset/offset for fMRI alignment. The same tonic run is used on both the outpatient (GE Architect) and inpatient (Siemens Prisma) scanners; connect the presentation computer to the scanner display via HDMI — no E-Prime interface is required.

### What's new in v2

- **Run integrity:** every data file ends with `Run_Status` (`completed` / `aborted` / `error`) and `Trials_Completed`. A failed write (e.g. a USB drive dropping) stops the run with `error`. Closing the stimulus window returns to the menu instead of quitting the app.
- **Frame-accurate flicker:** image changes follow a fixed time grid aligned to the display's frames, with vsync requested. A system stall shows up as one long interval, never as a burst of catch-up flips. Brightness levels are prepared before the first trial.
- **Timing and provenance logging:** per-trial onset/offset, flip-interval statistics and focus-loss counts. The header records the master CSV's path and SHA-256, image hashes, display size, refresh rate (OS-reported and measured) and the result of the 1600×1200 display check.
- **Tonic fMRI:** the intro screen continues only on the operator's SPACE bar, so scanner pulses can't use up a volume. Onset is the measured first frame. The log is written as soon as the trigger arrives, and every scanner pulse during the run is logged.
- **Operator GUI:** a display picker (with Identify), pre-flight checks, a warning when a participant ID already has data, the canonical image pair by default with thumbnails, remembered settings, a post-run summary, Test Trigger, and a standard fixed trial order with bright trials spaced apart.

**Output format (additive only):** existing rows and columns keep their names and order. New header rows push the trial table down 11 rows, so analysis scripts should find it by its header line (`Trial_Number_Overall,...`). New columns are appended to the right. Timing values are software timestamps taken after each flip, not photon times; check each rig once with a photodiode, and measure display luminance per brightness level with a photometer. See `mvast3_manual.html` §4 for every field.

**Display setup:** the protocol expects the participant display at **1600×1200**. On Windows, set that display's scaling to 100%.

## Repository Contents

- **`mvast3.py`** - Application entry point (run this file)
- **`config.py`** - Constants, paths, and run configuration objects
- **`data.py`** - CSV data/score logging handlers
- **`stimulus.py`** - Pygame stimulus presentation, rating scale, and helpers
- **`runner.py`** - Experiment run orchestration (standard and tonic fMRI)
- **`gui.py`** - Tkinter GUI windows (main menu, setup generator, run windows)
- **`gui_widgets.py`** - Shared GUI pieces (display picker, pre-flight checks, run summary, remembered settings)
- **`mvast3_manual.html`** - Complete user guide (open in any web browser)
- **`images/`** - Default images and sample stimuli

> The application is split into focused modules, but you still run it the same
> way — `python mvast3.py`. Keep all the `.py` files together in the same folder.

## Installation

Choose one of the installation methods below. **Option A** is recommended for beginners who are new to programming or command line tools.

### Option A: Simple Installation (Recommended for Beginners)

**Best for users unfamiliar with programming or the terminal**

#### Step 1: Download the Files
1. Click the green **Code** button on this GitHub page
2. Select **Download ZIP**
3. Extract the downloaded `mvast3-main.zip` file to your Desktop or Documents folder
4. Remember where you saved it!

#### Step 2: Install Python

**On Windows:**
1. Open Command Prompt (search for "cmd" in the Start menu)
2. Type `python` and press Enter
3. This will open the Microsoft Store where you can install Python
4. Click "Install" and wait for it to complete

**On Mac:**
1. Go to [python.org/downloads](https://python.org/downloads)
2. Download and install the latest version of Python
3. Follow the installation prompts

#### Step 3: Navigate to the Downloaded Files
You need to tell your computer where to find the M-VAST 3 files.

**On Windows:**
1. Open Command Prompt (search for "cmd" in the Start menu)
2. Type `cd Desktop\mvast3-main` (if you saved it to Desktop) or `cd Documents\mvast3-main` (if you saved it to Documents)
3. Press Enter

**On Mac:**
1. Open Terminal (search for "Terminal" in Spotlight)
2. Type `cd Desktop/mvast3-main` (if you saved it to Desktop) or `cd Documents/mvast3-main` (if you saved it to Documents)
3. Press Enter

**How to check you're in the right place:**
- On Windows: type `dir` and press Enter
- On Mac: type `ls` and press Enter

You should see these items listed:
- `images`
- `mvast3.py` (and the other `.py` files: `config.py`, `data.py`, `stimulus.py`, `runner.py`, `gui.py`, `gui_widgets.py`)
- `mvast3_manual.html`

If you don't see these files, you're in the wrong folder. Try navigating to where you actually saved the extracted files.

#### Step 4: Install Required Packages
In the same terminal/command prompt window, type this command:

```bash
python -m pip install pygame pillow numpy ttkbootstrap
```

**If you get an error saying "python is not recognized":**
- Try using `python3` instead: `python3 -m pip install pygame pillow numpy ttkbootstrap`
- Use `python3` for all future commands if `python` doesn't work

#### Step 5: Run the Application
```bash
python mvast3.py
```

Or if `python` doesn't work:
```bash
python3 mvast3.py
```

The M-VAST 3 application window should now open!

### Option B: Python Virtual Environment (Standard)

**Best for users comfortable with Python development**

1. **Clone the repository**
   ```bash
   git clone https://github.com/brockpluimer/mvast3.git
   cd mvast3
   ```

2. **Set up virtual environment**
   ```bash
   # Create virtual environment
   python -m venv mvast3
   
   # Activate (Windows)
   .\mvast3\Scripts\activate
   
   # Activate (macOS/Linux)
   source mvast3/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install pygame pillow numpy ttkbootstrap
   ```

4. **Run the application**
   ```bash
   python mvast3.py
   ```

### Option C: Conda Environment (For Researchers)

**Best for scientific computing and research environments**

1. **Clone the repository**
   ```bash
   git clone https://github.com/brockpluimer/mvast3.git
   cd mvast3
   ```

2. **Create Conda environment**
   ```bash
   conda create -n mvast3 -c conda-forge python=3.9 pillow numpy pygame ttkbootstrap
   ```
   Type `y` when prompted to proceed.

3. **Activate environment**
   ```bash
   conda activate mvast3
   ```

4. **Run the application**
   ```bash
   python mvast3.py
   ```

## Running the Tests

The `tests/` folder holds an automated test suite (about 200 tests, ~20 seconds). It runs headless: no window opens.

```bash
python -m pip install pytest
python -m pytest
```

It covers:
- flicker timing, using a simulated clock with injected stalls, vsync on and off, ESC, and scanner pulses;
- the output files, checked against v1's `data.py` from git so every v1 row and column stays in place;
- every way a run can end, in both run modes;
- master-CSV validation, the pre-flight checks, and the GUI windows (skipped where no display is available).

For a longer randomized timing run: `MVAST_STRESS_CASES=5000 MVAST_STRESS_SEED=7 python -m pytest tests/test_flicker.py -k stress`.

## Troubleshooting

**"Python is not recognized" error:**
- Try using `python3` instead of `python` in all commands
- Make sure Python is properly installed

**"No module named..." error:**
- Make sure you ran the pip install command in the correct directory
- Try the install command again

**Can't find the files:**
- Make sure you extracted the ZIP file
- Use `dir` (Windows) or `ls` (Mac) to check what's in your current folder
- Navigate to the correct folder using `cd` command

**Still having trouble?**
- Double-check that when you type `dir` (Windows) or `ls` (Mac), you see `images`, `mvast3.py` (plus the other `.py` files), and `mvast3_manual.html`
- Make sure you're in the mvast3-main folder

## Getting Help

For questions about the software or M-VAST 3 methodology, please contact:

**Brock Pluimer**  
📧 bpluimer@hs.uci.edu

## Requirements

- Python 3.8+ (3.11+ recommended on Windows for finer-grained timing)
- Dependencies: pygame, pillow, numpy, ttkbootstrap

## Citation

If you use M-VAST 3 in your research, please cite:

```
Brock Pluimer, & Steven Harte. (2025). MVAST-3 Version 1 (Version v1.0) [Computer software]. Zenodo. https://doi.org/10.5281/ZENODO.15700319
```

## Additional reading

For further reading, please see the below articles.

```
Harper, D. E., Gopinath, K., Smith, J. L., Gregory, M., Ichesco, E., Aronovich, S., Harris, R. E., Harte, S. E., Clauw, D. J., & Fleischer, C. C. (2023). Characterization of visual processing in temporomandibular disorders using functional magnetic resonance imaging. Brain and Behavior, 13(3), e2916. https://doi.org/10.1002/brb3.2916

Harte, S. E., Ichesco, E., Hampson, J. P., Peltier, S. J., Schmidt-Wilcke, T., Clauw, D. J., & Harris, R. E. (2016). Pharmacologic attenuation of cross-modal sensory augmentation within the chronic pain insula. Pain, 157(9), 1933–1945. https://doi.org/10.1097/j.pain.0000000000000593

Kmiecik, M. J., Tu, F. F., Clauw, D. J., & Hellman, K. M. (2023). Multimodal hypersensitivity derived from quantitative sensory testing predicts pelvic pain outcome: An observational cohort study. Pain, 164(9), 2070–2083. https://doi.org/10.1097/j.pain.0000000000002909

Kmiecik, M. J., Tu, F. F., Silton, R. L., Dillane, K. E., Roth, G. E., Harte, S. E., & Hellman, K. M. (2022). Cortical mechanisms of visual hypersensitivity in women at risk for chronic pelvic pain. Pain, 163(6), 1035–1048. https://doi.org/10.1097/j.pain.0000000000002469
```

## License

This project is licensed under the MIT License - see below for details:

```
MIT License

Copyright (c) 2025 Brock Pluimer and Steven Harte

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

*For detailed usage instructions, open `mvast3_manual.html` in your web browser.*
