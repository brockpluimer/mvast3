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

## License
MIT License

---

*For detailed usage instructions, open `mvast3_manual.html` in your web browser.*
