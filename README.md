# M-VAST 3

A desktop application for administering the M-VAST 3 (Michigan Visual Aversion Stress Test).

## Overview

This repository contains the complete M-VAST 3 platform, including source code, image assets, and comprehensive documentation. M-VAST 3 is a research tool designed to present visual stimuli and collect subjective ratings from participants in controlled experimental settings.

## Repository Contents

- **`mvast3.py`** - Core Python application
- **`mvast3_manual.html`** - Complete user guide (open in any web browser)
- **`images/`** - Default images and sample stimuli

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

You should see these three items listed:
- `images`
- `mvast3.py`
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
- Double-check that when you type `dir` (Windows) or `ls` (Mac), you see the three items: `images`, `mvast3.py`, and `mvast3_manual.html`
- Make sure you're in the mvast3-main folder

## Getting Help

For questions about the software or M-VAST 3 methodology, please contact:

**Brock Pluimer**  
📧 bpluimer@hs.uci.edu

## Requirements

- Python 3.8+
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
