# -*- coding: utf-8 -*-
"""
M-VAST 3 (Michigan Visual Aversion Stress Test) - application entry point.

The codebase is organized into focused modules:
  config.py    - constants, paths, and run configuration objects
  data.py      - CSV data/score logging handlers
  stimulus.py  - pygame stimulus presentation and helpers
  runner.py    - experiment run orchestration (standard and tonic fMRI)
  gui.py       - Tkinter GUI windows
  gui_widgets.py - shared GUI widgets, dialogs, and pre-flight checks
  mvast3.py    - this entry point
"""

from gui import MVAST3Application

if __name__ == '__main__':
    app = MVAST3Application()
    app.run()
