# M-VAST 3

A desktop application for administering the M-VAST 3 (Michigan Visual Aversion Stress Test).

## Overview

This repository contains the complete M-VAST 3 platform, including source code, image assets, and comprehensive documentation. M-VAST 3 is a research tool designed to present visual stimuli and collect subjective ratings from participants in controlled experimental settings.

## Repository Contents

- **`mvast3.py`** - Core Python application
- **`mvast3_manual.html`** - Complete user guide (open in any web browser)
- **`images/`** - Default images and sample stimuli

## Installation

Choose one of the three installation methods below. **Option C (Conda)** is recommended for the most reliable setup.

### Option A: Manual Download (Simplest)

**Best for users unfamiliar with Git or package managers**

1. **Download the repository**
   - Click the green **Code** button on this GitHub page
   - Select **Download ZIP**
   - Extract the downloaded `mvast3-main.zip` file

2. **Install dependencies**
   - Ensure Python is installed on your system
   - Open terminal/Command Prompt and navigate to the extracted folder:
     ```bash
     cd path/to/mvast3-main
     ```
   - Install required packages:
     ```bash
     pip install pygame pillow numpy ttkbootstrap
     ```

3. **Run the application**
   ```bash
   python mvast3.py
   ```

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

### Option C: Conda Environment (Recommended)

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
Pluimer, Brock, & Harte, Steven. (2025). M-VAST 3: Michigan Visual Aversion Stress Test (v1.0.0). 
Zenodo. https://doi.org/10.5281/zenodo.15700319
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
