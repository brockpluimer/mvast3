# -*- coding: utf-8 -*-
"""
M-VAST 3 (Michigan Visual Aversion Stress Test) Unified Application
"""

import pygame
import sys
import csv
from datetime import datetime
import time
import os
import numpy as np
import random
import webbrowser
import shutil

import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk

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

BRIGHTNESS_LEVELS_BASE = [0.1, 0.2, 0.4, 0.6, 0.8, 1.0]
RAMP_UP_TRIALS_COUNT = len(BRIGHTNESS_LEVELS_BASE)
TRIALS_PER_BLOCK = len(BRIGHTNESS_LEVELS_BASE) 

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 200, 0)
DARK_GREEN = (0, 150, 0)
GRAY_COLOR = (150, 150, 150) 

PYGAME_REFERENCE_SCREEN_HEIGHT = 1080.0

# --- Main Application Class ---
class MVAST3Application:
    def __init__(self):
        self.root = ttk.Window(themename="litera")
        self.root.title("M-VAST 3 - Michigan Visual Aversion Stress Test")
        
        try:
            self.root.state('zoomed')
        except tk.TclError:
            try:
                screen_width = self.root.winfo_screenwidth()
                screen_height = self.root.winfo_screenheight()
                self.root.geometry(f"{screen_width}x{screen_height}+0+0")
            except tk.TclError:
                print("Could not set window to maximized or large geometry. Using default.")
                self.root.geometry("1200x800") 

        self.root.minsize(800, 600) 
        
        self.create_main_menu()
        
    def create_main_menu(self):
            for widget in self.root.winfo_children():
                widget.destroy()

            # Use a main frame with some padding
            main_frame = ttk.Frame(self.root)
            main_frame.pack(fill=BOTH, expand=YES, padx=20, pady=20)

            # --- HEADER SECTION ---
            header_frame_height = 300
            header_frame = ttk.Frame(main_frame, height=header_frame_height)
            header_frame.pack(side=TOP, fill=X, pady=(10, 20)) 
            header_frame.pack_propagate(False)
            self.create_logo_tiles(header_frame, header_frame_height)
            
            # --- TITLE SECTION ---
            title_frame = ttk.Frame(main_frame)
            title_frame.pack(side=TOP, fill=X, pady=(0, 20)) # Added bottom padding
            ttk.Label(title_frame, text="M-VAST 3", font=("Helvetica", 72, "bold"), foreground="#1a73e8", anchor=CENTER).pack(fill=X)
            ttk.Label(title_frame, text="Michigan Visual Aversion Stress Test", font=("Helvetica", 24), foreground="#5f6368", anchor=CENTER).pack(fill=X, pady=(5, 0))
            ttk.Label(title_frame, text="Visual Stimulus Experiment Platform", font=("Helvetica", 18), foreground="#80868b", anchor=CENTER).pack(fill=X, pady=(5, 0))

            # --- ACTION CARDS SECTION ---
            cards_frame = ttk.Frame(main_frame)
            cards_frame.pack(side=TOP, fill=X, expand=False, pady=(20, 0)) # Set expand to False

            # Use a sub-frame to center the cards if the window is very wide
            centering_frame = ttk.Frame(cards_frame)
            centering_frame.pack(anchor=CENTER)

            setup_card = self.create_action_card(centering_frame, "Generate Experiment Setup", "Create experiment parameters\nand trial sequences", "#34a853", self.open_setup_generator)
            setup_card.pack(side=LEFT, padx=30, pady=20, fill=Y)

            run_card = self.create_action_card(centering_frame, "Run Experiment", "Execute visual stimulus testing\nwith a participant", "#ea4335", self.open_experiment_runner)
            run_card.pack(side=LEFT, padx=30, pady=20, fill=Y)
            
            # Spacer to push the footer down
            ttk.Frame(main_frame).pack(side=TOP, fill=BOTH, expand=YES)

            # --- FOOTER SECTION ---
            footer_frame = ttk.Frame(main_frame) 
            footer_frame.pack(side=BOTTOM, pady=15, padx=0, fill=X)
            
            self.help_btn = ttk.Button(footer_frame, text="Help / How to Use",
                                  command=self.show_help,
                                  style='danger.TButton') 
            self.help_btn.pack(side=LEFT)

            self.signature_label = ttk.Label(footer_frame, text="Brock Pluimer (University of California, Irvine) & Steven Harte (University of Michigan)",
                                             font=("Helvetica", 10, "italic"), foreground="grey50")
            self.signature_label.pack(side=LEFT, padx=(20,0), expand=True, anchor='w')

            self.version_label = ttk.Label(footer_frame, text=APP_VERSION,
                                           font=("Helvetica", 10), foreground="grey50")
            self.version_label.pack(side=RIGHT, padx=(10, 0))
            
            self.exit_btn = ttk.Button(footer_frame, text="Exit", 
                                 command=self.root.quit,
                                 style='secondary.TButton')
            self.exit_btn.pack(side=RIGHT)


    def create_logo_tiles(self, parent, header_height):
            try:
                canvas = tk.Canvas(parent, highlightthickness=0, bg="#f8f9fa") 
                canvas.pack(fill=BOTH, expand=YES)
                logos_data = []

                # Load only the single M-VAST 3 logo.
                logo_files = [
                    (resource_path("images/mvast_3.png"), "#1a73e8")
                ]
                
                # Set the desired larger size.
                thumb_w, thumb_h = 450, 300 
                
                for filepath, accent_color in logo_files: 
                    try:
                        img = Image.open(filepath)
                        img.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                        logos_data.append((ImageTk.PhotoImage(img), accent_color))
                    except FileNotFoundError:
                        print(f"Warning: Logo file '{os.path.basename(filepath)}' not found at '{filepath}'. Skipping.")
                    except Exception as e: print(f"Could not load logo {os.path.basename(filepath)}: {e}")
                
                def position_logos(event=None): 
                    canvas.delete("all")
                    cw = parent.winfo_width() 
                    ch = parent.winfo_height() 
                    
                    if cw <= 1 or ch <= 1 or not logos_data: return

                    num_logos = len(logos_data)
                    total_logo_native_width = sum(logo_photo.width() for logo_photo, _ in logos_data)
                    
                    if num_logos > 0:
                        spacing = (cw - total_logo_native_width) / (num_logos + 1)
                    else:
                        spacing = 0
                    
                    current_x = spacing
                    y_center = ch // 2 
                    
                    for photo, accent in logos_data:
                        img_width = photo.width()
                        canvas.create_image(current_x + img_width // 2, y_center, image=photo)
                        current_x += img_width + spacing 
                        
                        if not hasattr(canvas, 'image_refs'): canvas.image_refs = []
                        canvas.image_refs.append(photo)
                
                parent.bind('<Configure>', position_logos) 
                parent.after(100, position_logos) 
            except Exception as e:
                print(f"Could not create logo tiles: {e}")
                ttk.Label(parent, text="M-VAST 3 Platform", font=("Helvetica", 16), background="#f8f9fa").pack(expand=YES)

    def create_action_card(self, parent, title, description, color, command):
            card_frame = ttk.Frame(parent, relief="flat", borderwidth=1, style='secondary.TFrame')
            card_content = ttk.Frame(card_frame, padding=20)
            card_content.pack(fill=BOTH, expand=YES)

            title_label = ttk.Label(card_content, text=title, font=("Helvetica", 20, "bold"), foreground=color)
            title_label.pack(pady=(0, 15))

            desc_label = ttk.Label(card_content, text=description, font=("Helvetica", 14), foreground="#5f6368", justify="center")
            desc_label.pack(pady=(0, 15))

            action_btn = ttk.Button(card_content, text="Get Started", command=command, style='info.TButton')
            action_btn.pack(ipady=5, ipadx=25, pady=(0,10))

            def on_enter(e): card_frame.config(style='primary.TFrame')
            def on_leave(e): card_frame.config(style='secondary.TFrame')

            card_frame.bind("<Enter>", on_enter); card_frame.bind("<Leave>", on_leave)
            return card_frame

    def show_help(self):
        help_text = f"""
M-VAST 3 Application - How to Use
Version: {APP_VERSION}

Step 1.  GENERATE EXPERIMENT SETUP:
    *   This step only needs to be once per experiment i.e. for the first participant.
    *   Click "Generate Experiment Setup".
    *   Enter a unique 'Experiment ID'.
    *   Choose a 'Base Output Directory'.
    *   Select 'Default' or 'Custom' parameters.
    *   Click "Generate Experiment Files". This creates:
        *   A randomization schedule (`..._brightness_schedule.csv`).
        *   A master trial list (`..._master_trials.csv`).

Step 2.  RUN EXPERIMENT:
    *   Click "Run Experiment".
    *   Browse for the 'Master Trial CSV' you generated in step 1.
    *   Enter a 'Participant ID'.
    *   Browse for your desired file for 'Image 1' and 'Image 2'
    *   Choose a 'Participant Data Log Directory'.
    *   Click "Start Experiment".

Step 3.  DURING EXPERIMENT (for Participant):
    *   Follow on-screen instructions.
    *   Focus on the fixation cross (+).
    *   After each stimulus, rate Unpleasantness and Brightness using the sliders (0-100) and click "Confirm".
    *   Press ESC to quit at any time.
        """
        messagebox.showinfo("How to Use - M-VAST 3 Application", help_text, parent=self.root)
        
        # Crash-Proof Logic for Opening the Manual in a packaged app
        try:
            internal_manual_path = resource_path(HELP_FILE_NAME)
            if os.path.exists(internal_manual_path):
                desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
                external_manual_path = os.path.join(desktop_path, HELP_FILE_NAME)
                shutil.copy(internal_manual_path, external_manual_path)
                webbrowser.open(f"file://{os.path.abspath(external_manual_path)}")
                print(f"Successfully copied and opened manual at: {external_manual_path}")
            else:
                print(f"Manual file not found at internal path: {internal_manual_path}")
        except Exception as e:
            print(f"Could not copy or open the help file: {e}")
            messagebox.showwarning("Help File Error",
                                   "Could not automatically open the manual.\n"
                                   f"Please look for {HELP_FILE_NAME} in the application folder.",
                                   parent=self.root)
        
    def open_setup_generator(self): SetupGeneratorWindow(self.root, self)
    def open_experiment_runner(self): ExperimentRunnerWindow(self.root, self)
    def run(self): self.root.mainloop()

# --- Setup Generator Window ---
class SetupGeneratorWindow:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.window = ttk.Toplevel(parent)
        self.window.title("M-VAST 3 - Generate Experiment Setup")
        
        # Set geometry BEFORE creating widgets
        self.window.geometry("700x750")
        self.window.minsize(650, 700)
        
        # Force the window to fully initialize before adding content
        self.window.update_idletasks()
        
        # Grab focus
        self.window.grab_set()
        self.window.focus_force()
        
        # Initialize variables BEFORE creating GUI
        self._init_variables()
        
        # Now create the GUI
        self.create_setup_gui()
        
        # Force another update after GUI creation
        self.window.update_idletasks()
        self.window.update()
        
    def _init_variables(self):
        """Initialize all tkinter variables before GUI creation."""
        self.exp_id_var = tk.StringVar(value="")
        self.log_dir_base_var = tk.StringVar(value=DEFAULT_LOG_DIR_BASE)
        self.param_mode_var = tk.StringVar(value="Default")
        self.stim_dur_var = tk.DoubleVar(value=DEFAULT_STIMULUS_DURATION)
        self.fix_dur_var = tk.DoubleVar(value=DEFAULT_FIXATION_DURATION)
        self.hz_var = tk.DoubleVar(value=DEFAULT_CHECKERBOARD_HZ)
        self.rand_blocks_var = tk.IntVar(value=DEFAULT_RANDOMIZED_BLOCKS_COUNT)
        
    def create_setup_gui(self):
        # Create main scrollable container in case window is small
        main_frame = ttk.Frame(self.window, padding=(20, 20))
        main_frame.pack(fill=BOTH, expand=YES)
        
        # Force frame to expand
        main_frame.update_idletasks()
        
        # --- Back Button ---
        back_btn = ttk.Button(
            main_frame, 
            text="← Back to Main Menu", 
            command=self.back_to_main, 
            style='secondary.TButton'
        )
        back_btn.pack(anchor='w', pady=(0, 15))
        
        # --- Font sizes ---
        lbl_font = ("TkDefaultFont", 10)
        small_font = ("TkDefaultFont", 9)
        entry_font = ("TkDefaultFont", 10)
        
        # ============================================================
        # SECTION 1: Experiment Identifier
        # ============================================================
        id_frame = ttk.LabelFrame(main_frame, text="Experiment Identifier", padding=(10, 10))
        id_frame.pack(fill=X, pady=(0, 10), ipady=5)
        
        # Use grid with explicit row/column configuration
        id_frame.columnconfigure(1, weight=1)
        
        ttk.Label(
            id_frame, 
            text="Experiment ID:", 
            font=lbl_font
        ).grid(row=0, column=0, padx=(5, 10), pady=8, sticky="w")
        
        self.exp_id_entry = ttk.Entry(
            id_frame, 
            textvariable=self.exp_id_var, 
            width=30, 
            font=entry_font
        )
        self.exp_id_entry.grid(row=0, column=1, padx=5, pady=8, sticky="ew")
        
        ttk.Label(
            id_frame, 
            text="(e.g., Study1_CondA_Group1)", 
            font=small_font,
            foreground="gray"
        ).grid(row=0, column=2, padx=(10, 5), pady=8, sticky="w")
        
        # Force the frame to render
        id_frame.update_idletasks()
        
        # ============================================================
        # SECTION 2: Base Output Directory
        # ============================================================
        dir_frame = ttk.LabelFrame(main_frame, text="Base Output Directory", padding=(10, 10))
        dir_frame.pack(fill=X, pady=(0, 10), ipady=5)
        
        dir_frame.columnconfigure(1, weight=1)
        
        ttk.Label(
            dir_frame, 
            text="Directory:", 
            font=lbl_font
        ).grid(row=0, column=0, padx=(5, 10), pady=8, sticky="w")
        
        self.dir_entry = ttk.Entry(
            dir_frame, 
            textvariable=self.log_dir_base_var, 
            width=45, 
            state="readonly", 
            font=entry_font
        )
        self.dir_entry.grid(row=0, column=1, padx=5, pady=8, sticky="ew")
        
        ttk.Button(
            dir_frame, 
            text="Browse...", 
            command=self.browse_log_dir_base, 
            style='outline.TButton'
        ).grid(row=0, column=2, padx=(10, 5), pady=8)
        
        dir_frame.update_idletasks()
        
        # ============================================================
        # SECTION 3: Parameter Mode Selection
        # ============================================================
        mode_frame = ttk.LabelFrame(main_frame, text="Parameter Mode", padding=(10, 10))
        mode_frame.pack(fill=X, pady=(0, 10), ipady=5)
        
        radio_container = ttk.Frame(mode_frame)
        radio_container.pack(fill=X, padx=5, pady=5)
        
        self.default_radio = ttk.Radiobutton(
            radio_container, 
            text="Default Parameters", 
            variable=self.param_mode_var, 
            value="Default", 
            command=self.toggle_custom_params
        )
        self.default_radio.pack(side=LEFT, padx=(5, 20))
        
        self.custom_radio = ttk.Radiobutton(
            radio_container, 
            text="Custom Parameters", 
            variable=self.param_mode_var, 
            value="Custom", 
            command=self.toggle_custom_params
        )
        self.custom_radio.pack(side=LEFT, padx=5)
        
        mode_frame.update_idletasks()
        
        # ============================================================
        # SECTION 4: Custom Parameters
        # ============================================================
        self.custom_params_frame = ttk.LabelFrame(
            main_frame, 
            text="Custom Experiment Parameters", 
            padding=(10, 10)
        )
        self.custom_params_frame.pack(fill=X, pady=(0, 10), ipady=5)
        
        # Configure grid columns
        self.custom_params_frame.columnconfigure(0, weight=0, minsize=200)
        self.custom_params_frame.columnconfigure(1, weight=0, minsize=100)
        self.custom_params_frame.columnconfigure(2, weight=1)
        
        # Row 0: Stimulus Duration
        ttk.Label(
            self.custom_params_frame, 
            text="Stimulus Duration (s):", 
            font=lbl_font
        ).grid(row=0, column=0, padx=(5, 10), pady=8, sticky="w")
        
        self.stim_dur_spinbox = ttk.Spinbox(
            self.custom_params_frame, 
            from_=1.0, 
            to=300.0, 
            increment=1.0, 
            textvariable=self.stim_dur_var, 
            width=10, 
            format="%.1f", 
            font=entry_font
        )
        self.stim_dur_spinbox.grid(row=0, column=1, padx=5, pady=8, sticky="w")
        
        # Row 1: Fixation Duration
        ttk.Label(
            self.custom_params_frame, 
            text="Fixation Duration (s):", 
            font=lbl_font
        ).grid(row=1, column=0, padx=(5, 10), pady=8, sticky="w")
        
        self.fix_dur_spinbox = ttk.Spinbox(
            self.custom_params_frame, 
            from_=0.5, 
            to=300.0, 
            increment=0.5, 
            textvariable=self.fix_dur_var, 
            width=10, 
            format="%.1f", 
            font=entry_font
        )
        self.fix_dur_spinbox.grid(row=1, column=1, padx=5, pady=8, sticky="w")
        
        # Row 2: Checkerboard Frequency
        ttk.Label(
            self.custom_params_frame, 
            text="Checkerboard Freq (Hz):", 
            font=lbl_font
        ).grid(row=2, column=0, padx=(5, 10), pady=8, sticky="w")
        
        self.hz_spinbox = ttk.Spinbox(
            self.custom_params_frame, 
            from_=0.1, 
            to=60.0, 
            increment=0.1, 
            textvariable=self.hz_var, 
            width=10, 
            format="%.1f", 
            font=entry_font
        )
        self.hz_spinbox.grid(row=2, column=1, padx=5, pady=8, sticky="w")
        
        # Row 3: Number of Randomized Blocks
        ttk.Label(
            self.custom_params_frame, 
            text="Num. Randomized Blocks:", 
            font=lbl_font
        ).grid(row=3, column=0, padx=(5, 10), pady=8, sticky="w")
        
        self.rand_blocks_spinbox = ttk.Spinbox(
            self.custom_params_frame, 
            from_=1, 
            to=20, 
            increment=1, 
            textvariable=self.rand_blocks_var, 
            width=10, 
            font=entry_font
        )
        self.rand_blocks_spinbox.grid(row=3, column=1, padx=5, pady=8, sticky="w")
        
        ttk.Label(
            self.custom_params_frame, 
            text=f"(each with {TRIALS_PER_BLOCK} trials)", 
            font=small_font,
            foreground="gray"
        ).grid(row=3, column=2, padx=(10, 5), pady=8, sticky="w")
        
        self.custom_params_frame.update_idletasks()
        
        # ============================================================
        # SECTION 5: Info Label
        # ============================================================
        info_container = ttk.Frame(main_frame, padding=(5, 10))
        info_container.pack(fill=X, pady=(5, 5))
        
        self.info_label = ttk.Label(
            info_container, 
            text="", 
            justify="left", 
            wraplength=600, 
            font=small_font
        )
        self.info_label.pack(fill=X, anchor="w")
        
        # ============================================================
        # SECTION 6: Generate Button
        # ============================================================
        btn_container = ttk.Frame(main_frame, padding=(0, 10))
        btn_container.pack(fill=X, pady=(10, 5))
        
        self.generate_button = ttk.Button(
            btn_container, 
            text="Generate Experiment Files", 
            command=self.process_generation, 
            style='success.TButton'
        )
        self.generate_button.pack(pady=10, ipadx=20, ipady=8)
        
        # ============================================================
        # Final Setup
        # ============================================================
        
        # Apply initial state to custom params (disable them by default)
        self.toggle_custom_params()
        
        # Update info label
        self.update_info_label()
        
        # Set focus to experiment ID entry
        self.exp_id_entry.focus_set()
        
        # Final forced update to ensure everything renders
        self.window.update_idletasks()
        self.window.update()
        
    def back_to_main(self):
        self.window.destroy()
    
    def toggle_custom_params(self):
        """Enable/disable custom parameter widgets based on mode selection."""
        mode = self.param_mode_var.get()
        
        widgets_to_toggle = [
            self.stim_dur_spinbox, 
            self.fix_dur_spinbox, 
            self.hz_spinbox, 
            self.rand_blocks_spinbox
        ]
        
        if mode == "Custom":
            new_state = "normal"
        else:
            new_state = "disabled"
            # Reset to defaults when switching back to Default mode
            self.stim_dur_var.set(DEFAULT_STIMULUS_DURATION)
            self.fix_dur_var.set(DEFAULT_FIXATION_DURATION)
            self.hz_var.set(DEFAULT_CHECKERBOARD_HZ)
            self.rand_blocks_var.set(DEFAULT_RANDOMIZED_BLOCKS_COUNT)
        
        for widget in widgets_to_toggle:
            try:
                widget.config(state=new_state)
            except Exception as e:
                print(f"Warning: Could not set widget state: {e}")
        
        # Update the info label
        self.update_info_label()

    def update_info_label(self):
        """Update the information label with current settings."""
        is_default = self.param_mode_var.get() == "Default"
        
        try:
            if is_default:
                stim = DEFAULT_STIMULUS_DURATION
                fix = DEFAULT_FIXATION_DURATION
                hz = DEFAULT_CHECKERBOARD_HZ
                blocks = DEFAULT_RANDOMIZED_BLOCKS_COUNT
            else:
                stim = self.stim_dur_var.get()
                fix = self.fix_dur_var.get()
                hz = self.hz_var.get()
                blocks = self.rand_blocks_var.get()
                
                # Validate the values
                float(stim)
                float(fix)
                float(hz)
                int(blocks)
        except (tk.TclError, ValueError):
            self.info_label.config(text="⚠ Please enter valid custom parameters.")
            return
        
        rand_trials = int(blocks) * TRIALS_PER_BLOCK
        total_trials = RAMP_UP_TRIALS_COUNT + rand_trials
        
        brightness_str = ', '.join(map(str, BRIGHTNESS_LEVELS_BASE))
        
        info_text = (
            f"Mode: {self.param_mode_var.get()}\n"
            f"Total trials to be generated: {total_trials}\n"
            f"  • Ramp-up: {RAMP_UP_TRIALS_COUNT} trials (brightness: {brightness_str})\n"
            f"  • Randomized: {int(blocks)} blocks × {TRIALS_PER_BLOCK} trials = {rand_trials} trials\n"
            f"  • Per trial: Stimulus={float(stim):.1f}s, Fixation={float(fix):.1f}s, Freq={float(hz):.1f}Hz\n"
            f"Output: Master trial CSV in '{SETUPS_SUBDIR}/', schedule in '{SCHEDULES_SUBDIR}/'"
        )
        
        self.info_label.config(text=info_text)

    def browse_log_dir_base(self):
        """Open directory browser for base output directory."""
        current_dir = self.log_dir_base_var.get()
        if not os.path.exists(current_dir):
            current_dir = APP_BASE_PATH
            
        dirpath = filedialog.askdirectory(
            parent=self.window, 
            initialdir=current_dir, 
            title="Select Base Output Directory"
        )
        
        if dirpath:
            self.log_dir_base_var.set(dirpath)

    def validate_inputs(self):
        """Validate all user inputs before generation."""
        self.exp_id = self.exp_id_var.get().strip()
        self.log_dir_base = self.log_dir_base_var.get().strip()
        
        # Check Experiment ID
        if not self.exp_id:
            messagebox.showerror(
                "Input Error", 
                "Experiment ID cannot be empty.", 
                parent=self.window
            )
            self.exp_id_entry.focus_set()
            return False
        
        # Check for invalid characters in Experiment ID
        invalid_chars = r'/\:*?"<>|'
        if any(c in self.exp_id for c in invalid_chars):
            messagebox.showerror(
                "Input Error", 
                f"Experiment ID contains invalid characters.\nAvoid: {invalid_chars}", 
                parent=self.window
            )
            self.exp_id_entry.focus_set()
            return False
        
        # Check Base Output Directory
        if not self.log_dir_base:
            messagebox.showerror(
                "Input Error", 
                "Base Output Directory cannot be empty.", 
                parent=self.window
            )
            return False
        
        # Validate custom parameters if in Custom mode
        if self.param_mode_var.get() == "Custom":
            try:
                s = self.stim_dur_var.get()
                f = self.fix_dur_var.get()
                h = self.hz_var.get()
                b = self.rand_blocks_var.get()
                
                if not (0 < s <= 300):
                    raise ValueError("Stimulus duration must be between 1 and 300 seconds.")
                if not (0 < f <= 300):
                    raise ValueError("Fixation duration must be between 0.5 and 300 seconds.")
                if not (0 < h <= 60):
                    raise ValueError("Frequency must be between 0.1 and 60 Hz.")
                if not (1 <= b <= 20):
                    raise ValueError("Number of randomized blocks must be between 1 and 20.")
                    
            except tk.TclError:
                messagebox.showerror(
                    "Input Error", 
                    "Please enter valid numeric values for all custom parameters.", 
                    parent=self.window
                )
                return False
            except ValueError as ve:
                messagebox.showerror(
                    "Input Error", 
                    str(ve), 
                    parent=self.window
                )
                return False
        
        return True

    def get_current_params(self):
        """Get current parameter values based on mode."""
        if self.param_mode_var.get() == "Default":
            return {
                "stim_duration": DEFAULT_STIMULUS_DURATION,
                "fixation_duration": DEFAULT_FIXATION_DURATION,
                "hz": DEFAULT_CHECKERBOARD_HZ,
                "randomized_blocks": DEFAULT_RANDOMIZED_BLOCKS_COUNT
            }
        else:
            return {
                "stim_duration": self.stim_dur_var.get(),
                "fixation_duration": self.fix_dur_var.get(),
                "hz": self.hz_var.get(),
                "randomized_blocks": self.rand_blocks_var.get()
            }

    def get_or_create_brightness_schedule(self, num_rand_blocks):
        """Load existing brightness schedule or create a new one."""
        sched_dir = os.path.join(self.log_dir_base, SCHEDULES_SUBDIR)
        os.makedirs(sched_dir, exist_ok=True)
        sched_file = os.path.join(sched_dir, f"{self.exp_id}_brightness_schedule.csv")
        
        factors = []
        expected_len = TRIALS_PER_BLOCK * num_rand_blocks
        
        # Try to load existing schedule
        if os.path.exists(sched_file):
            try:
                with open(sched_file, 'r', newline='') as f:
                    reader = csv.reader(f)
                    factors = [float(row[0]) for row in reader if row]
                
                if len(factors) == expected_len:
                    messagebox.showinfo(
                        "Schedule Loaded", 
                        f"Loaded existing schedule ({len(factors)} trials) for ID: {self.exp_id}", 
                        parent=self.window
                    )
                    return factors
                else:
                    msg = (
                        f"Existing schedule for ID '{self.exp_id}' has {len(factors)} trials, "
                        f"but current settings need {expected_len}.\n\n"
                        f"Do you want to regenerate the schedule?"
                    )
                    if not messagebox.askyesno("Schedule Mismatch", msg, parent=self.window):
                        return "cancelled"
                    factors = []  # Will regenerate below
                    
            except Exception as e:
                messagebox.showerror(
                    "Schedule Load Error", 
                    f"Error loading {sched_file}:\n{e}\n\nRegenerating schedule.", 
                    parent=self.window
                )
                factors = []
        
        # Generate new schedule
        if not factors:
            for _ in range(num_rand_blocks):
                shuffled = BRIGHTNESS_LEVELS_BASE[:]
                random.shuffle(shuffled)
                factors.extend(shuffled)
            
            try:
                with open(sched_file, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows([[f_val] for f_val in factors])
                
                messagebox.showinfo(
                    "Schedule Generated", 
                    f"New schedule ({len(factors)} trials) saved for ID: {self.exp_id}\n\n"
                    f"File: {sched_file}", 
                    parent=self.window
                )
            except Exception as e:
                messagebox.showerror(
                    "Schedule Save Error", 
                    f"Could not save {sched_file}:\n{e}", 
                    parent=self.window
                )
                return None
        
        return factors

    def generate_master_trial_csv(self, full_brightness_schedule, params):
        """Generate the master trial CSV file."""
        setups_dir = os.path.join(self.log_dir_base, SETUPS_SUBDIR)
        os.makedirs(setups_dir, exist_ok=True)
        master_file = os.path.join(setups_dir, f"{self.exp_id}_master_trials.csv")
        
        header = [
            'trial_number', 
            'block_number', 
            'trial_in_block', 
            'brightness_factor',
            'stimulus_duration', 
            'fixation_duration', 
            'checkerboard_hz'
        ]
        
        try:
            with open(master_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(header)
                
                # Safely get parameters with defaults
                stim_dur = params.get("stim_duration", DEFAULT_STIMULUS_DURATION)
                fix_dur = params.get("fixation_duration", DEFAULT_FIXATION_DURATION)
                hz = params.get("hz", DEFAULT_CHECKERBOARD_HZ)
                
                for i, bf in enumerate(full_brightness_schedule):
                    trial_num = i + 1
                    
                    if i < RAMP_UP_TRIALS_COUNT:
                        block_num = 0
                        trial_in_block = i + 1
                    else:
                        rand_idx = i - RAMP_UP_TRIALS_COUNT
                        block_num = (rand_idx // TRIALS_PER_BLOCK) + 1
                        trial_in_block = (rand_idx % TRIALS_PER_BLOCK) + 1
                    
                    writer.writerow([
                        trial_num, 
                        block_num, 
                        trial_in_block, 
                        f"{bf:.2f}",
                        stim_dur, 
                        fix_dur, 
                        hz
                    ])
            
            messagebox.showinfo(
                "Success", 
                f"Master CSV ({len(full_brightness_schedule)} trials) generated:\n\n{master_file}", 
                parent=self.window
            )
            return True
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror(
                "CSV Save Error", 
                f"Could not save {master_file}:\n\n{type(e).__name__}: {e}", 
                parent=self.window
            )
            return False

    def process_generation(self):
        """Main process to generate experiment files."""
        # Validate inputs
        if not self.validate_inputs():
            return
        
        # Create base directory
        try:
            os.makedirs(self.log_dir_base, exist_ok=True)
        except Exception as e:
            messagebox.showerror(
                "Directory Error", 
                f"Could not create directory:\n{self.log_dir_base}\n\nError: {e}", 
                parent=self.window
            )
            return
        
        # Get parameters
        params = self.get_current_params()
        
        # Get or create brightness schedule
        rand_bf = self.get_or_create_brightness_schedule(int(params["randomized_blocks"]))
        
        if rand_bf is None or rand_bf == "cancelled":
            return
        
        # Build full schedule (ramp-up + randomized)
        full_schedule = BRIGHTNESS_LEVELS_BASE[:] + rand_bf
        
        # Verify length
        expected_len = RAMP_UP_TRIALS_COUNT + (int(params["randomized_blocks"]) * TRIALS_PER_BLOCK)
        if len(full_schedule) != expected_len:
            messagebox.showerror(
                "Logic Error", 
                f"Schedule length mismatch: got {len(full_schedule)}, expected {expected_len}.\n\n"
                f"Please try again or report this issue.", 
                parent=self.window
            )
            return
        
        # Generate the master trial CSV
        self.generate_master_trial_csv(full_schedule, params)

# --- Experiment Runner Window (Fixed geometry) ---
class ExperimentRunnerWindow:
    def __init__(self, parent, app):
        self.parent = parent; self.app = app
        self.window = ttk.Toplevel(parent)
        self.window.title("M-VAST 3 - Run Experiment")
        self.window.geometry("800x700")
        self.window.minsize(700, 650)
        self.window.grab_set()
        self.config = RunConfig() 
        self.create_runner_gui()
        
    def create_runner_gui(self):
        main_frame = ttk.Frame(self.window, padding=(20,20))
        main_frame.pack(fill=BOTH, expand=YES)
        
        ttk.Button(main_frame, text="← Back to Main Menu", command=self.back_to_main, style='secondary.TButton').pack(anchor='w', pady=(0, 15))
        
        lf_pad = (10,5) 
        lbl_font_size = 10

        csv_frame = ttk.LabelFrame(main_frame, text="Experiment Setup File")
        csv_frame.pack(fill=X, pady=(0, 10))
        ttk.Label(csv_frame, text="Master Trial CSV:", font=("",lbl_font_size)).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.master_csv_var = tk.StringVar()
        self.csv_entry = ttk.Entry(csv_frame, textvariable=self.master_csv_var, width=50, state="readonly", font=("",lbl_font_size))
        self.csv_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(csv_frame, text="Browse...", command=self.browse_master_csv, style='outline.TButton').grid(row=0, column=2, padx=5, pady=5)
        csv_frame.columnconfigure(1, weight=1)

        part_id_frame = ttk.LabelFrame(main_frame, text="Participant Information")
        part_id_frame.pack(fill=X, pady=(0,10))
        ttk.Label(part_id_frame, text="Participant ID:", font=("",lbl_font_size)).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.participant_id_var = tk.StringVar()
        self.part_id_entry = ttk.Entry(part_id_frame, textvariable=self.participant_id_var, width=30, font=("",lbl_font_size))
        self.part_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        part_id_frame.columnconfigure(1, weight=1)

        img_frame = ttk.LabelFrame(main_frame, text="Stimulus Image Files")
        img_frame.pack(fill=X, pady=(0, 10))
        self.img1_path_var, self.img2_path_var = tk.StringVar(), tk.StringVar()
        ttk.Label(img_frame, text="Image 1:", font=("",lbl_font_size)).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(img_frame, textvariable=self.img1_path_var, width=40, state='readonly', font=("",lbl_font_size)).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(img_frame, text="Browse...", command=self.browse_image1, style='outline.TButton').grid(row=0, column=2, padx=5, pady=5)
        ttk.Label(img_frame, text="Image 2:", font=("",lbl_font_size)).grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(img_frame, textvariable=self.img2_path_var, width=40, state='readonly', font=("",lbl_font_size)).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(img_frame, text="Browse...", command=self.browse_image2, style='outline.TButton').grid(row=1, column=2, padx=5, pady=5)
        img_frame.columnconfigure(1, weight=1)

        log_dir_frame = ttk.LabelFrame(main_frame, text="Participant Data Log Directory")
        log_dir_frame.pack(fill=X, pady=(0, 15))
        ttk.Label(log_dir_frame, text="Directory:", font=("",lbl_font_size)).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.log_dir_participant_var = tk.StringVar(value=self.config.log_dir_participant)
        ttk.Entry(log_dir_frame, textvariable=self.log_dir_participant_var, width=40, state="readonly", font=("",lbl_font_size)).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(log_dir_frame, text="Browse...", command=self.browse_log_dir_participant, style='outline.TButton').grid(row=0, column=2, padx=5, pady=5)
        log_dir_frame.columnconfigure(1, weight=1)

        btn_frame = ttk.Frame(main_frame, padding=(0, 10)); btn_frame.pack(fill=X) 
        ttk.Button(btn_frame, text="Start Experiment", command=self.start_experiment, style='success.TButton', padding=(10,5)).pack(side=RIGHT)
        
        self.csv_entry.focus()
        
    def back_to_main(self): self.window.destroy()

    def browse_master_csv(self):
        init_dir = os.path.join(DEFAULT_LOG_DIR_BASE, SETUPS_SUBDIR)
        fp = filedialog.askopenfilename(parent=self.window, title="Select Master CSV", filetypes=[("CSV files", "*.csv")], initialdir=init_dir if os.path.exists(init_dir) else APP_BASE_PATH)
        if fp: self.master_csv_var.set(fp)

    def browse_image(self, var):
        init_img_dir = os.path.join(APP_BASE_PATH, "images")
        fp = filedialog.askopenfilename(parent=self.window, title="Select Image", 
                                      filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.gif")],
                                      initialdir=init_img_dir if os.path.exists(init_img_dir) else APP_BASE_PATH)
        if fp: var.set(fp)
    def browse_image1(self): self.browse_image(self.img1_path_var)
    def browse_image2(self): self.browse_image(self.img2_path_var)

    def browse_log_dir_participant(self):
        dp = filedialog.askdirectory(parent=self.window, initialdir=self.log_dir_participant_var.get(), title="Select Participant Log Directory")
        if dp: self.log_dir_participant_var.set(dp)

    def validate_inputs(self):
        self.config.master_csv_path = self.master_csv_var.get()
        self.config.image1_path = self.img1_path_var.get()
        self.config.image2_path = self.img2_path_var.get()
        self.config.participant_id = self.part_id_entry.get().strip()
        self.config.log_dir_participant = self.log_dir_participant_var.get() 

        if not (self.config.master_csv_path and os.path.exists(self.config.master_csv_path)):
            messagebox.showerror("Input Error", "Valid Master CSV required.", parent=self.window); return False
        if not self.config.participant_id:
            messagebox.showerror("Input Error", "Participant ID required.", parent=self.window); return False
        if any(c in self.config.participant_id for c in r'/\:*?"<>|'):
            messagebox.showerror("Input Error", "Participant ID has invalid chars.", parent=self.window); return False
        if not (self.config.image1_path and os.path.exists(self.config.image1_path)):
            messagebox.showerror("Input Error", "Valid Image 1 required.", parent=self.window); return False
        if not (self.config.image2_path and os.path.exists(self.config.image2_path)):
            messagebox.showerror("Input Error", "Valid Image 2 required.", parent=self.window); return False
        if self.config.image1_path == self.config.image2_path and \
           not messagebox.askyesno("Warning", "Images are same (no flicker). Continue?", parent=self.window): return False
        if not self.config.log_dir_participant:
            messagebox.showerror("Input Error", "Participant Log Directory required.", parent=self.window); return False
        try: os.makedirs(self.config.log_dir_participant, exist_ok=True) 
        except Exception as e: messagebox.showerror("Directory Error", f"Cannot create log dir:\n{e}", parent=self.window); return False
        return True

    def load_trials_from_csv(self):
        trials = []
        try:
            with open(self.config.master_csv_path, 'r', newline='') as f:
                reader = csv.DictReader(f)
                reader.fieldnames = [field.strip() for field in reader.fieldnames or []]
                expected = ['trial_number', 'brightness_factor', 'stimulus_duration', 'fixation_duration', 'checkerboard_hz']
                missing = [col for col in expected if col not in reader.fieldnames]
                if missing:
                    messagebox.showerror("CSV Error", f"CSV missing: {', '.join(missing)}", parent=self.window); return False
                for i, row in enumerate(reader):
                    try:
                        block_num_csv = row.get('block_number')
                        trial_in_block_csv = row.get('trial_in_block')

                        if block_num_csv is not None and trial_in_block_csv is not None:
                            block_num = int(block_num_csv)
                            trial_in_block = int(trial_in_block_csv)
                        else: 
                            trial_idx_overall = int(row['trial_number']) -1 
                            if trial_idx_overall < RAMP_UP_TRIALS_COUNT:
                                block_num = 0 
                                trial_in_block = trial_idx_overall + 1
                            else:
                                randomized_trial_idx = trial_idx_overall - RAMP_UP_TRIALS_COUNT
                                block_num = (randomized_trial_idx // TRIALS_PER_BLOCK) + 1
                                trial_in_block = (randomized_trial_idx % TRIALS_PER_BLOCK) + 1
                        
                        trials.append({
                            'trial_number': int(row['trial_number']),
                            'block_number': block_num,
                            'trial_in_block': trial_in_block,
                            'brightness_factor': float(row['brightness_factor']),
                            'stimulus_duration': float(row['stimulus_duration']),
                            'fixation_duration': float(row['fixation_duration']),
                            'checkerboard_hz': float(row['checkerboard_hz'])})
                    except (ValueError, KeyError) as ve:
                        messagebox.showerror("CSV Data Error", f"Row {i+2}: {ve}\n{row}", parent=self.window); return False
            if not trials: messagebox.showerror("CSV Error", "No valid trials in CSV.", parent=self.window); return False
            self.config.trials_data = trials
            return True
        except Exception as e: messagebox.showerror("CSV Read Error", f"Error reading {self.config.master_csv_path}:\n{e}", parent=self.window); return False

    def start_experiment(self):
        if not self.validate_inputs() or not self.load_trials_from_csv(): return
        self.window.withdraw()
        execute_experiment_run(self.config)
        self.window.deiconify()

# --- Configuration Class ---
class RunConfig:
    def __init__(self):
        self.master_csv_path = ""
        self.image1_path = ""
        self.image2_path = ""
        self.participant_id = ""
        self.log_dir_participant = DEFAULT_LOG_DIR_PARTICIPANT 
        self.trials_data = []

# --- Rating Scale Class (Pygame UI) ---
class RatingScale:
    def __init__(self, screen, title_ignored, min_val=0, max_val=100, scale_type="unpleasantness"):
        self.screen = screen; self.min_val = min_val; self.max_val = max_val
        self.value = min_val; self.scale_type = scale_type 
        self.pygame_scale_factor = max(0.5, min(3.0, screen.get_height() / PYGAME_REFERENCE_SCREEN_HEIGHT))
        
        fs_n, fs_l, fs_b = int(36*self.pygame_scale_factor), int(48*self.pygame_scale_factor), int(30*self.pygame_scale_factor)
        try:
            self.font = pygame.font.Font(None, fs_n)
            self.val_font = pygame.font.Font(None, fs_l)
            self.button_font = pygame.font.Font(None, fs_b)
        except: 
            self.font = pygame.font.SysFont("arial", fs_n)
            self.val_font = pygame.font.SysFont("arial", fs_l)
            self.button_font = pygame.font.SysFont("arial", fs_b)
        
        if self.scale_type == "unpleasantness":
            self.title = "Please rate the unpleasantness of the image you just viewed."
        elif self.scale_type == "brightness":
            self.title = "Please rate the brightness of the image you just viewed."
        else: 
            self.title = title_ignored 
            
        self.scale_width = min(int(800 * self.pygame_scale_factor), int(screen.get_width() * 0.85))
        self.scale_height = max(5, int(10 * self.pygame_scale_factor))
        self.scale_x = (screen.get_width() - self.scale_width) // 2
        self.scale_y = screen.get_height() // 2
        self.slider_width = max(10, int(20 * self.pygame_scale_factor))
        self.slider_height = max(20, int(40 * self.pygame_scale_factor))
        self.dragging = False; self.slider_rect = pygame.Rect(0,0,0,0) 
        
        self.confirm_button_width = int(150 * self.pygame_scale_factor)
        self.confirm_button_height = int(50 * self.pygame_scale_factor)
        self.confirm_button_x = (screen.get_width() - self.confirm_button_width) // 2
        self.confirm_button_y = self.scale_y + int(120 * self.pygame_scale_factor) 
        self.confirm_button_rect = pygame.Rect(self.confirm_button_x, self.confirm_button_y, self.confirm_button_width, self.confirm_button_height)
        self.confirm_button_text = "Confirm"; self.button_color = GREEN; self.button_hover_color = DARK_GREEN

    def get_scale_labels(self):
        if self.scale_type == "unpleasantness":
            return "Not\nUnpleasant", "Most Unpleasant\nImage\nImaginable"
        elif self.scale_type == "brightness": 
            return "No Image\nVisible", "Brightest Image\nImaginable" 
        else: 
            return "Low", "High"

    def draw(self):
        ts = self.font.render(self.title, True, WHITE)
        self.screen.blit(ts, ts.get_rect(centerx=self.screen.get_width()//2, bottom=self.scale_y - int(60*self.pygame_scale_factor)))
        pygame.draw.rect(self.screen, GRAY_COLOR, (self.scale_x-1, self.scale_y-1, self.scale_width+2, self.scale_height+2))
        pygame.draw.rect(self.screen, WHITE, (self.scale_x, self.scale_y, self.scale_width, self.scale_height))
        
        num_ticks = 11; tick_h = int(10*self.pygame_scale_factor); num_off = int(15*self.pygame_scale_factor); tick_w = max(1,int(1*self.pygame_scale_factor))
        for i in range(num_ticks):
            val = self.min_val + i * (self.max_val - self.min_val) / (num_ticks-1)
            tx = self.scale_x + (val - self.min_val) / (self.max_val - self.min_val) * self.scale_width
            pygame.draw.line(self.screen, WHITE, (tx, self.scale_y+self.scale_height), (tx, self.scale_y+self.scale_height+tick_h), tick_w)
            if i % 2 == 0:
                tns = self.font.render(str(int(val)), True, WHITE)
                self.screen.blit(tns, tns.get_rect(centerx=tx, top=self.scale_y+self.scale_height+num_off))
        
        ll, rl = self.get_scale_labels()
        loff = self.scale_y + self.scale_height + num_off + self.font.get_height() + int(10*self.pygame_scale_factor)
        lspace = int(self.font.get_linesize() * 0.9) 
        for i, line in enumerate(ll.split('\n')):
            ls = self.font.render(line, True, WHITE); self.screen.blit(ls, ls.get_rect(centerx=self.scale_x, top=loff+i*lspace))
        for i, line in enumerate(rl.split('\n')):
            ls = self.font.render(line, True, WHITE); self.screen.blit(ls, ls.get_rect(centerx=self.scale_x+self.scale_width, top=loff+i*lspace))
            
        slider_x = self.scale_x + (self.value - self.min_val) / (self.max_val - self.min_val) * self.scale_width
        slider_x = max(self.scale_x, min(self.scale_x + self.scale_width, slider_x))
        self.slider_rect.size = (self.slider_width, self.slider_height)
        self.slider_rect.center = (slider_x, self.scale_y + self.scale_height//2)
        sbr = max(1, int(3*self.pygame_scale_factor)); sbw = max(1, int(2*self.pygame_scale_factor))
        pygame.draw.rect(self.screen, (200,200,200), self.slider_rect, border_radius=sbr)
        pygame.draw.rect(self.screen, WHITE, self.slider_rect, width=sbw, border_radius=sbr)
        
        vt = self.val_font.render(str(int(self.value)), True, WHITE)
        vr = vt.get_rect(centerx=slider_x, bottom=self.slider_rect.top - int(10*self.pygame_scale_factor))
        self.screen.blit(vt, vr.clamp(self.screen.get_rect()))
        
        btn_col = self.button_hover_color if self.confirm_button_rect.collidepoint(pygame.mouse.get_pos()) else self.button_color
        bbr = max(2, int(5*self.pygame_scale_factor))
        pygame.draw.rect(self.screen, btn_col, self.confirm_button_rect, border_radius=bbr)
        cts = self.button_font.render(self.confirm_button_text, True, WHITE)
        self.screen.blit(cts, cts.get_rect(center=self.confirm_button_rect.center))

    def handle_event(self, event):
        mp = pygame.mouse.get_pos()
        ir = pygame.Rect(self.scale_x - self.slider_width, self.scale_y - self.slider_height,
                         self.scale_width + 2*self.slider_width, self.scale_height + 2*self.slider_height)
        
        def update_value_from_mouse():
            raw_x = mp[0] - self.scale_x
            continuous_value = self.min_val + (raw_x / self.scale_width) * (self.max_val - self.min_val)
            clamped_value = max(self.min_val, min(self.max_val, continuous_value))
            self.value = round(clamped_value)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.confirm_button_rect.collidepoint(mp): return "confirmed"
            if ir.collidepoint(mp):
                self.dragging = True
                update_value_from_mouse()
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1: self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            update_value_from_mouse()
        return None

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

# --- Pygame Helper Functions ---
def load_checkerboard_images(screen_width, screen_height, img1_path, img2_path):
    try:
        if not os.path.exists(img1_path): raise FileNotFoundError(f"Img1 not found: {img1_path}")
        if not os.path.exists(img2_path): raise FileNotFoundError(f"Img2 not found: {img2_path}")
        b1_orig, b2_orig = pygame.image.load(img1_path), pygame.image.load(img2_path)
        b1_orig, b2_orig = b1_orig.convert(), b2_orig.convert() 
        b1_scaled = pygame.transform.scale(b1_orig, (screen_width, screen_height))
        b2_scaled = pygame.transform.scale(b2_orig, (screen_width, screen_height))
        return b1_scaled, b2_scaled
    except Exception as e:
        messagebox.showerror("Image Load Error", f"Failed to load/scale images:\n{e}")
        return None, None

def adjust_surface_brightness(surface, factor):
    if factor >= 1.0: return surface
    if factor <= 0.0: sf = pygame.Surface(surface.get_size()).convert(); sf.fill(BLACK); return sf
    adj_sf = surface.copy()
    try: adj_sf.fill((int(255*factor),)*3, special_flags=pygame.BLEND_RGB_MULT)
    except: 
        try:
            arr = pygame.surfarray.pixels3d(adj_sf).astype(np.float32) * factor
            pygame.surfarray.blit_array(adj_sf, np.clip(arr, 0, 255).astype(np.uint8))
        except Exception as e_np:
            print(f"NumPy brightness failed ({e_np}), slow fallback.")
            for x in range(adj_sf.get_width()):
                for y in range(adj_sf.get_height()):
                    r,g,b,a = adj_sf.get_at((x,y)); adj_sf.set_at((x,y), (int(r*factor),int(g*factor),int(b*factor),a))
    return adj_sf

def show_message(screen, text, wait_for_key=True, escape_quits=True):
    if not screen: print(f"show_message: No screen. Msg: {text}"); return True
    screen.fill(BLACK)
    pg_sf = max(0.5, min(3.0, screen.get_height() / PYGAME_REFERENCE_SCREEN_HEIGHT))
    font_size = int(38 * pg_sf) 
    try: font = pygame.font.Font(None, font_size)
    except: font = pygame.font.SysFont("arial", font_size)
    
    lines = [l.strip() for l in text.split('\n')]
    r_lines, total_h = [], 0
    base_line_h = font.get_linesize() 
    scaled_line_h = base_line_h * 1.2 

    for l_txt in lines:
        if l_txt: 
            ts = font.render(l_txt, True, WHITE)
            r_lines.append(ts)
            total_h += ts.get_height()
        else: 
            r_lines.append(None) 
            total_h += scaled_line_h // 2 
    
    num_text_lines = sum(1 for line in r_lines if line is not None)
    if num_text_lines > 1:
        total_h += (num_text_lines - 1) * (scaled_line_h - base_line_h) 
            
    curr_y = (screen.get_height() - total_h) // 2
    
    for ts in r_lines:
        if ts: 
            tr = ts.get_rect(centerx=screen.get_width()//2, top=curr_y)
            screen.blit(ts, tr)
            curr_y += ts.get_height() + (scaled_line_h - base_line_h) 
        else: 
             curr_y += scaled_line_h // 2
    pygame.display.flip()
    
    if wait_for_key:
        while True:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
                if ev.type == pygame.KEYDOWN: return not (escape_quits and ev.key == pygame.K_ESCAPE)
            pygame.time.wait(10)
    return True

def get_rating_with_click(screen, title_ignored, scale_type="unpleasantness"): 
    pygame.mouse.set_visible(True)
    scale = RatingScale(screen, title_ignored, scale_type=scale_type) 
    clock = pygame.time.Clock()
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE: pygame.mouse.set_visible(False); return None
            if scale.handle_event(ev) == "confirmed": pygame.mouse.set_visible(False); return scale.value
        screen.fill(BLACK); scale.draw(); pygame.display.flip(); clock.tick(60)

def show_fixation(screen, duration, escape_quits=True):
    pygame.mouse.set_visible(False); screen.fill(BLACK)
    pg_sf = max(0.5, min(3.0, screen.get_height() / PYGAME_REFERENCE_SCREEN_HEIGHT))
    font_size = int(72 * pg_sf) 
    try: font = pygame.font.Font(None, font_size)
    except: font = pygame.font.SysFont("arial", font_size)
    ts = font.render('+', True, WHITE)
    screen.blit(ts, ts.get_rect(center=(screen.get_width()//2, screen.get_height()//2)))
    pygame.display.flip()
    start_t = time.perf_counter()
    while time.perf_counter() - start_t < duration:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: return False
            if escape_quits and ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE: return False
        time.sleep(0.01)
    return True

def run_alternating_stimulus(screen, board1, board2, duration, hz, brightness_factor, escape_quits=True):
    pygame.mouse.set_visible(False)
    if hz <= 0: 
        stim_board = adjust_surface_brightness(board1, brightness_factor) 
        screen.fill(BLACK); screen.blit(stim_board, (0,0)); pygame.display.flip()
        start_t = time.perf_counter()
        while time.perf_counter() - start_t < duration:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT: return False
                if escape_quits and ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE: return False
            time.sleep(0.01)
        return True

    frame_dur = 1.0 / hz / 2.0 
    start_t, end_t = time.perf_counter(), time.perf_counter() + duration
    b_b1 = adjust_surface_brightness(board1, brightness_factor)
    b_b2 = adjust_surface_brightness(board2, brightness_factor)
    curr_b1, last_flip_t = True, start_t
    
    while time.perf_counter() < end_t:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: return False
            if escape_quits and ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE: return False
        
        now_t = time.perf_counter()
        if now_t >= last_flip_t + frame_dur:
            screen.fill(BLACK)
            screen.blit(b_b1 if curr_b1 else b_b2, (0,0))
            pygame.display.flip()
            curr_b1 = not curr_b1
            last_flip_t += frame_dur 
        
        time_to_next = (last_flip_t + frame_dur) - now_t
        if time_to_next > 0.002: time.sleep(max(0.001, time_to_next * 0.5)) 
    return True

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

# --- Main Application Entry Point ---
if __name__ == '__main__':
    app = MVAST3Application()
    app.run()
