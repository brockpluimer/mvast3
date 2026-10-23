# -*- coding: utf-8 -*-
"""M-VAST 3 - Tkinter GUI: main menu and run configuration windows."""

import os
import csv
import webbrowser
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk

from config import (
    APP_VERSION, HELP_FILE_NAME, APP_BASE_PATH,
    DEFAULT_LOG_DIR_BASE, DEFAULT_LOG_DIR_PARTICIPANT, DEFAULT_LOG_DIR_PARTICIPANT_NAME,
    SCHEDULES_SUBDIR, SETUPS_SUBDIR,
    DEFAULT_STIMULUS_DURATION, DEFAULT_FIXATION_DURATION,
    DEFAULT_CHECKERBOARD_HZ, DEFAULT_RANDOMIZED_BLOCKS_COUNT,
    DEFAULT_TONIC_DURATION, DEFAULT_TONIC_BRIGHTNESS, DEFAULT_TONIC_HZ,
    DEFAULT_TRIGGER_KEY, DEFAULT_TONIC_SHOW_FIXATION,
    BRIGHTNESS_LEVELS_BASE, RAMP_UP_TRIALS_COUNT, TRIALS_PER_BLOCK,
    EXPECTED_DISPLAY_SIZE, CANONICAL_IMAGE1, CANONICAL_IMAGE2,
    CANONICAL_ORDER_SEED, BRIGHT_THRESHOLD,
    resource_path, RunConfig, TonicRunConfig,
)
from data import build_randomized_schedule, count_runs_using_master
from runner import execute_experiment_run, execute_tonic_run
from stimulus import describe_display, frames_per_half_cycle
from gui_widgets import (
    HINT_FONT, ScrollFrame, ImageRow, DisplayPicker, PreflightPanel,
    load_settings, save_settings, load_master_csv, estimate_minutes, short_hash,
    check_image, display_checks, folder_check, image_checks, participant_check,
    ask_choice, show_run_summary,
)

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

            tonic_card = self.create_action_card(centering_frame, "Run Tonic fMRI", "Continuous constant-brightness run\nsynced to the MRI scanner trigger", "#a142f4", self.open_tonic_runner)
            tonic_card.pack(side=LEFT, padx=30, pady=20, fill=Y)

            # Spacer to push the footer down
            ttk.Frame(main_frame).pack(side=TOP, fill=BOTH, expand=YES)

            # --- FOOTER SECTION ---
            footer_frame = ttk.Frame(main_frame)
            footer_frame.pack(side=BOTTOM, pady=(5, 8), padx=0, fill=X)

            # Ensure footer button text is centered within the button box
            self.root.style.configure('info.TButton', anchor=CENTER)
            self.root.style.configure('secondary.TButton', anchor=CENTER)

            self.help_btn = ttk.Button(footer_frame, text="Help / How to Use",
                                  command=self.show_help,
                                  style='info.TButton', padding=(14, 4))
            self.help_btn.pack(side=LEFT)

            self.signature_label = ttk.Label(footer_frame, text="Brock Pluimer (University of California, Irvine) & Steven Harte (University of Michigan)",
                                             font=("Helvetica", 10, "italic"), foreground="grey50")
            self.signature_label.pack(side=LEFT, padx=(20,0), expand=True, anchor='w')

            self.version_label = ttk.Label(footer_frame, text=APP_VERSION,
                                           font=("Helvetica", 10), foreground="grey50")
            self.version_label.pack(side=RIGHT, padx=(10, 0))
            
            self.exit_btn = ttk.Button(footer_frame, text="Exit",
                                 command=self.root.quit,
                                 style='secondary.TButton', padding=(14, 4))
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
    *   Browse for the 'Master Trial CSV' you generated in step 1. It is
        checked as soon as you pick it (trial count, value ranges, duration).
    *   Enter a 'Participant ID'. You are warned if this ID already has data.
    *   Images default to the canonical blue/yellow pair (acheck_by).
    *   Under 'Display', pick the participant's screen ("Identify" shows
        each screen's number on that screen).
    *   Choose a 'Participant Data Log Directory'.
    *   Review the Pre-flight Check, then click "Start Experiment".
    *   If the display isn't 1600x1200 you are asked before the run starts.
    *   Settings are remembered for next time (untick to stop).
    *   After the run, a summary shows the run status, timing checks and
        the files written.

Step 3.  DURING EXPERIMENT (for Participant):
    *   Follow on-screen instructions.
    *   Focus on the fixation cross (+).
    *   After each stimulus, rate Unpleasantness and Brightness using the sliders (0-100) and click "Confirm".
    *   Press ESC to quit at any time.

RUN TONIC fMRI (concurrent MRI acquisition):
    *   Use this instead of "Run Experiment" for the tonic M-VAST + fMRI run.
    *   No setup CSV is needed. Enter a 'Participant ID', pick the two
        checkerboard images, and set the constant brightness, flicker Hz,
        duration (~6 min), and scanner trigger key (default '5').
    *   "Draw fixation cross (+)" is OFF by default because the acheck_by
        images already have a cross built in. Turn it on only for image sets
        (e.g., the strobe images) that do not include one.
    *   "Test Trigger..." listens for 10 s so you can confirm the scanner's
        keystroke reaches this computer and see the TR.
    *   Click "Start Tonic Run". On the intro screen the OPERATOR presses
        SPACE (trigger pulses are ignored there). A "waiting for scanner"
        screen appears.
    *   Start the fMRI sequence. When the scanner sends its trigger pulse
        (delivered as the trigger keystroke), the flickering checkerboard
        begins automatically and runs at constant brightness for the full
        duration while the participant fixates the central cross.
    *   Trigger time, the measured first frame (onset), offset, and every
        scanner pulse during the run are logged for fMRI alignment.
    *   Press ESC to abort at any time.
        """
        self._show_help_dialog(help_text)

        # Open the full manual in the browser straight from the app folder
        try:
            manual_path = resource_path(HELP_FILE_NAME)
            if os.path.exists(manual_path):
                webbrowser.open(Path(manual_path).resolve().as_uri())
            else:
                print(f"Manual file not found at: {manual_path}")
        except Exception as e:
            print(f"Could not open the help file: {e}")
            messagebox.showwarning("Help File Error",
                                   "Could not automatically open the manual.\n"
                                   f"Please look for {HELP_FILE_NAME} in the application folder.",
                                   parent=self.root)

    def _show_help_dialog(self, help_text):
        """Show the help text in a scrollable window with an always-visible
        Close button (the native messagebox can push its OK button off-screen
        when the text is very long)."""
        dialog = ttk.Toplevel(self.root)
        dialog.title("How to Use - M-VAST 3 Application")
        dialog.geometry("720x640")
        dialog.minsize(500, 400)
        dialog.transient(self.root)

        container = ttk.Frame(dialog, padding=10)
        container.pack(fill=BOTH, expand=YES)

        # Close button pinned to the bottom so it is always reachable
        btn_frame = ttk.Frame(container)
        btn_frame.pack(side=BOTTOM, fill=X, pady=(10, 0))
        close_btn = ttk.Button(btn_frame, text="Close", command=dialog.destroy,
                               style='secondary.TButton', padding=(20, 6))
        close_btn.pack()

        # Scrollable text area for the help content
        text_frame = ttk.Frame(container)
        text_frame.pack(side=TOP, fill=BOTH, expand=YES)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical")
        scrollbar.pack(side=RIGHT, fill=Y)
        text_widget = tk.Text(text_frame, wrap="word", yscrollcommand=scrollbar.set,
                              font=("TkDefaultFont", 11), relief="flat",
                              padx=10, pady=10, borderwidth=0)
        text_widget.pack(side=LEFT, fill=BOTH, expand=YES)
        scrollbar.config(command=text_widget.yview)
        text_widget.insert("1.0", help_text.strip())
        text_widget.config(state="disabled")

        dialog.bind("<Escape>", lambda e: dialog.destroy())
        dialog.grab_set()
        dialog.focus_force()
        close_btn.focus_set()

    def open_setup_generator(self): SetupGeneratorWindow(self.root, self)
    def open_experiment_runner(self): ExperimentRunnerWindow(self.root, self)
    def open_tonic_runner(self): TonicRunnerWindow(self.root, self)
    def run(self): self.root.mainloop()

# --- Setup Generator Window ---
class SetupGeneratorWindow:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.window = ttk.Toplevel(parent)
        self.window.title("M-VAST 3 - Generate Experiment Setup")
        
        # Set geometry BEFORE creating widgets
        self.window.geometry(f"780x{min(980, self.window.winfo_screenheight() - 80)}")
        self.window.minsize(700, 560)
        
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
        self.order_mode_var = tk.StringVar(value="Standard")
        self.seed_var = tk.IntVar(value=CANONICAL_ORDER_SEED)
        self.space_bright_var = tk.BooleanVar(value=True)
        
    def create_setup_gui(self):
        # Generate button + info pinned at the bottom; the form scrolls above
        outer = ttk.Frame(self.window)
        outer.pack(fill=BOTH, expand=YES)
        self.bottom_frame = ttk.Frame(outer, padding=(20, 0))
        self.bottom_frame.pack(side=BOTTOM, fill=X)
        ttk.Separator(outer).pack(side=BOTTOM, fill=X)
        scroll = ScrollFrame(outer, padding=(20, 20))
        scroll.pack(fill=BOTH, expand=YES)
        main_frame = scroll.inner
        
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
        id_frame = ttk.Labelframe(main_frame, text="Experiment Identifier", padding=(10, 10))
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
        dir_frame = ttk.Labelframe(main_frame, text="Base Output Directory", padding=(10, 10))
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
        # SECTION 2b: Trial Order (one fixed order for every participant)
        # ============================================================
        order_frame = ttk.Labelframe(main_frame, text="Trial Order", padding=(10, 10))
        order_frame.pack(fill=X, pady=(0, 10), ipady=5)
        order_frame.columnconfigure(1, weight=1)

        ttk.Radiobutton(
            order_frame, text="Standard fixed order (recommended)",
            variable=self.order_mode_var, value="Standard", command=self.toggle_order_mode
        ).grid(row=0, column=0, padx=5, pady=4, sticky="w")
        ttk.Label(
            order_frame, font=small_font, foreground="gray",
            text=f"Every participant gets the same order; bright trials (≥ {BRIGHT_THRESHOLD:g}) are never back-to-back."
        ).grid(row=0, column=1, columnspan=3, padx=5, pady=4, sticky="w")

        ttk.Radiobutton(
            order_frame, text="Generate a new order",
            variable=self.order_mode_var, value="Custom", command=self.toggle_order_mode
        ).grid(row=1, column=0, padx=5, pady=4, sticky="w")
        seed_row = ttk.Frame(order_frame)
        seed_row.grid(row=1, column=1, columnspan=3, padx=5, pady=4, sticky="w")
        ttk.Label(seed_row, text="Advanced. Seed:", font=small_font, foreground="gray").pack(side=LEFT)
        self.seed_entry = ttk.Spinbox(seed_row, from_=0, to=999999, increment=1, textvariable=self.seed_var, width=8, font=entry_font)
        self.seed_entry.pack(side=LEFT, padx=(6, 14))
        self.space_check = ttk.Checkbutton(seed_row, text="Space out bright trials", variable=self.space_bright_var)
        self.space_check.pack(side=LEFT)

        self.order_canvas = tk.Canvas(order_frame, height=124, highlightthickness=0, background=ttk.Style().colors.bg)
        self.order_canvas.grid(row=2, column=0, columnspan=4, padx=5, pady=(8, 0), sticky="ew")
        self.order_note = ttk.Label(order_frame, text="", font=small_font, foreground="gray")
        self.order_note.grid(row=3, column=0, columnspan=4, padx=5, pady=(2, 0), sticky="w")
        self.order_canvas.bind("<Configure>", lambda e: self.update_order_preview())
        for var in (self.seed_var, self.space_bright_var, self.rand_blocks_var):
            var.trace_add("write", lambda *a: self.update_order_preview())

        # ============================================================
        # SECTION 3: Parameter Mode Selection
        # ============================================================
        mode_frame = ttk.Labelframe(main_frame, text="Parameter Mode", padding=(10, 10))
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
        self.custom_params_frame = ttk.Labelframe(
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
        # SECTION 6: Generate Button (pinned to bottom so it is always
        # visible regardless of window height)
        # ============================================================
        btn_container = ttk.Frame(self.bottom_frame, padding=(0, 0))
        btn_container.pack(side=BOTTOM, fill=X, pady=(10, 5))

        self.generate_button = ttk.Button(
            btn_container,
            text="Generate Experiment Files",
            command=self.process_generation,
            style='success.TButton'
        )
        self.generate_button.pack(pady=(4, 10), ipadx=20, ipady=8)

        # ============================================================
        # SECTION 5: Info Label (pinned just above the button)
        # ============================================================
        info_container = ttk.Frame(self.bottom_frame, padding=(5, 8))
        info_container.pack(side=BOTTOM, fill=X)

        self.info_label = ttk.Label(
            info_container,
            text="",
            justify="left",
            wraplength=700,
            font=small_font
        )
        self.info_label.pack(fill=X, anchor="w")
        
        # ============================================================
        # Final Setup
        # ============================================================
        
        # Apply initial state to custom params (disable them by default)
        self.toggle_custom_params()
        self.toggle_order_mode()
        
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
        
        seed, space = self.get_order_settings() if hasattr(self, 'seed_entry') else (CANONICAL_ORDER_SEED, True)
        order_txt = "standard fixed order" if self.order_mode_var.get() == "Standard" else f"new order, seed {seed}"
        info_text = (
            f"Mode: {self.param_mode_var.get()} · Trial order: {order_txt}\n"
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

    def toggle_order_mode(self):
        """Standard mode locks the seed and spacing to the canonical values."""
        standard = self.order_mode_var.get() == "Standard"
        if standard:
            self.seed_var.set(CANONICAL_ORDER_SEED)
            self.space_bright_var.set(True)
        state = "disabled" if standard else "normal"
        self.seed_entry.config(state=state)
        self.space_check.config(state=state)
        self.update_order_preview()
        self.update_info_label()

    def get_order_settings(self):
        """(seed, space_bright) for the selected order mode."""
        if self.order_mode_var.get() == "Standard":
            return CANONICAL_ORDER_SEED, True
        return int(self.seed_var.get()), bool(self.space_bright_var.get())

    def build_order(self, num_blocks):
        seed, space = self.get_order_settings()
        return build_randomized_schedule(num_blocks, seed, space)

    def update_order_preview(self):
        """Bar strip of the full trial order: ramp-up, then each block."""
        c = self.order_canvas
        c.delete("all")
        try:
            blocks = int(self.rand_blocks_var.get())
            order = self.build_order(blocks)
        except (tk.TclError, ValueError, RuntimeError) as e:
            self.order_note.config(text=f"Preview unavailable: {e}")
            return
        seq = BRIGHTNESS_LEVELS_BASE[:] + order
        groups = [("Ramp-up", seq[:RAMP_UP_TRIALS_COUNT])] + [
            (f"Block {b + 1}", order[b * TRIALS_PER_BLOCK:(b + 1) * TRIALS_PER_BLOCK]) for b in range(blocks)]
        width = max(c.winfo_width(), 300)
        gap_group, n = 10, len(seq)
        bar_w = max(2.0, (width - 10 - gap_group * (len(groups) - 1)) / n - 2)
        top, base_y = 16, 98
        colors = ttk.Style().colors
        x = 4
        for label, vals in groups:
            if bar_w >= 10 or label == "Ramp-up": c.create_text(x, 2, text=label, anchor="nw", font=("", 8), fill=colors.secondary)
            for v in vals:
                h = (base_y - top) * v
                fill = colors.primary if v >= BRIGHT_THRESHOLD else "#b8c4d6"
                c.create_rectangle(x, base_y - h, x + bar_w, base_y, fill=fill, outline="")
                if bar_w >= 14: c.create_text(x + bar_w / 2, base_y + 4, text=f"{v:g}", anchor="n", font=("", 7), fill=colors.secondary)
                x += bar_w + 2
            x += gap_group
        c.create_line(0, base_y + 0.5, x, base_y + 0.5, fill="#dee2e6")
        seed, space = self.get_order_settings()
        self.order_note.config(text=f"Bar height = brightness; blue = bright (≥ {BRIGHT_THRESHOLD:g}). "
                                    f"Seed {seed}{', bright trials spaced' if space else ''}.")

    def save_brightness_schedule(self, factors):
        """Write the randomized-block factors to the schedule CSV (kept for records)."""
        sched_dir = os.path.join(self.log_dir_base, SCHEDULES_SUBDIR)
        os.makedirs(sched_dir, exist_ok=True)
        sched_file = os.path.join(sched_dir, f"{self.exp_id}_brightness_schedule.csv")
        with open(sched_file, 'w', newline='') as f:
            csv.writer(f).writerows([[f_val] for f_val in factors])
        return sched_file

    def confirm_overwrite(self):
        """If the master CSV already exists, ask before replacing it. May change
        self.exp_id (save under a new name). Returns False to cancel."""
        setups_dir = os.path.join(self.log_dir_base, SETUPS_SUBDIR)
        master_name = f"{self.exp_id}_master_trials.csv"
        if not os.path.exists(os.path.join(setups_dir, master_name)): return True
        n_runs = count_runs_using_master(os.path.join(self.log_dir_base, DEFAULT_LOG_DIR_PARTICIPANT_NAME), master_name)
        v = 2
        while os.path.exists(os.path.join(setups_dir, f"{self.exp_id}_v{v}_master_trials.csv")): v += 1
        new_id = f"{self.exp_id}_v{v}"
        used = f"has been used for {n_runs} participant run(s)" if n_runs else "exists"
        choice = ask_choice(self.window, "Master CSV Exists", f"{master_name} already exists",
                            [f"It {used}. Regenerating changes its SHA-256, so it would no longer match those runs' logs."],
                            [('keep', "Keep Existing", 'secondary-outline'),
                             ('new', f"Save as {new_id}_master_trials.csv", 'primary-outline'),
                             ('overwrite', "Overwrite", 'warning')], default='keep')
        if choice == 'keep': return False
        if choice == 'new': self.exp_id = new_id; self.exp_id_var.set(new_id)
        return True

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
                f"Master CSV ({len(full_brightness_schedule)} trials) generated:\n\n{master_file}\n\n"
                f"Schedule saved in '{SCHEDULES_SUBDIR}/'.", 
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
        
        # Build the randomized-block order (deterministic for the seed)
        try:
            rand_bf = self.build_order(int(params["randomized_blocks"]))
        except RuntimeError as e:
            messagebox.showerror("Order Error", str(e), parent=self.window)
            return

        if not self.confirm_overwrite():
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

        try:
            self.save_brightness_schedule(rand_bf)
        except OSError as e:
            messagebox.showerror("Schedule Save Error", f"Could not save the schedule:\n{e}", parent=self.window)
            return
        
        # Generate the master trial CSV
        self.generate_master_trial_csv(full_schedule, params)

# --- Shared base for the two run windows ---
class _RunWindowBase:
    """Common layout and behavior for the standard and tonic run windows:
    scrollable form, image rows with thumbnails, display picker, log folder,
    pre-flight checks, remembered settings, and the display-check dialog."""
    TITLE = ""
    SETTINGS_SECTION = ""
    START_LABEL = "Start"

    def __init__(self, parent, app):
        self.parent = parent; self.app = app
        self.window = ttk.Toplevel(parent)
        self.window.title(self.TITLE)
        screen_h = self.window.winfo_screenheight()
        self.window.geometry(f"860x{min(900, screen_h - 80)}")
        self.window.minsize(760, 520)
        self.window.grab_set()
        self.settings = load_settings(self.SETTINGS_SECTION)
        self._preflight_job = None
        self.create_runner_gui()
        self.window.bind("<Return>", lambda e: self.start())
        self.refresh_preflight()

    # Subclass hooks
    def build_top_sections(self, body): pass
    def build_middle_sections(self, body): pass
    def extra_checks(self, display): return []
    def flicker_rates(self): return []
    def current_settings(self): return {}
    def start(self): pass

    def create_runner_gui(self):
        outer = ttk.Frame(self.window); outer.pack(fill=BOTH, expand=YES)
        # Footer pinned to the bottom so Start is always visible
        footer = ttk.Frame(outer, padding=(20, 10)); footer.pack(side=BOTTOM, fill=X)
        ttk.Separator(outer).pack(side=BOTTOM, fill=X)
        self.remember_var = tk.BooleanVar(value=self.settings.get('remember', True))
        ttk.Checkbutton(footer, text="Remember these settings for next session", variable=self.remember_var).pack(side=LEFT)
        ttk.Button(footer, text=self.START_LABEL, command=self.start, style='success.TButton', padding=(14, 6)).pack(side=RIGHT)

        scroll = ScrollFrame(outer); scroll.pack(fill=BOTH, expand=YES)
        body = scroll.inner
        ttk.Button(body, text="← Back to Main Menu", command=self.back_to_main, style='secondary.TButton').pack(anchor='w', pady=(0, 15))

        self.build_top_sections(body)

        img_frame = ttk.Labelframe(body, text="Stimulus Image Files")
        img_frame.pack(fill=X, pady=(0, 10))
        self.img1_path_var = tk.StringVar(value=self.settings.get('image1') or resource_path(CANONICAL_IMAGE1))
        self.img2_path_var = tk.StringVar(value=self.settings.get('image2') or resource_path(CANONICAL_IMAGE2))
        ImageRow(img_frame, 0, "Image 1:", self.img1_path_var, self.schedule_preflight)
        ImageRow(img_frame, 1, "Image 2:", self.img2_path_var, self.schedule_preflight)
        self.canonical_label = ttk.Label(img_frame, text="", font=HINT_FONT, foreground="gray")
        self.canonical_label.grid(row=2, column=2, columnspan=2, padx=5, pady=(0, 5), sticky="w")

        self.build_middle_sections(body)

        self.display_picker = DisplayPicker(body, self.settings.get('display_index', 0), self.schedule_preflight)
        self.display_picker.frame.pack(fill=X, pady=(0, 10))

        log_dir_frame = ttk.Labelframe(body, text="Participant Data Log Directory")
        log_dir_frame.pack(fill=X, pady=(0, 10))
        ttk.Label(log_dir_frame, text="Directory:", font=("", 10)).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.log_dir_participant_var = tk.StringVar(value=self.settings.get('log_dir') or DEFAULT_LOG_DIR_PARTICIPANT)
        ttk.Entry(log_dir_frame, textvariable=self.log_dir_participant_var, width=40, state="readonly", font=("", 10)).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(log_dir_frame, text="Browse...", command=self.browse_log_dir_participant, style='outline.TButton').grid(row=0, column=2, padx=5, pady=5)
        log_dir_frame.columnconfigure(1, weight=1)
        self.log_dir_participant_var.trace_add("write", lambda *a: self.schedule_preflight())

        self.preflight = PreflightPanel(body)
        self.preflight.frame.pack(fill=X, pady=(0, 10))

    def build_participant_frame(self, body, extra_rows=None):
        part_frame = ttk.Labelframe(body, text="Participant Information")
        part_frame.pack(fill=X, pady=(0, 10))
        ttk.Label(part_frame, text="Participant ID:", font=("", 10)).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.participant_id_var = tk.StringVar()
        self.part_id_entry = ttk.Entry(part_frame, textvariable=self.participant_id_var, width=30, font=("", 10))
        self.part_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.participant_note = ttk.Label(part_frame, text="", font=HINT_FONT, bootstyle="warning", wraplength=600, justify="left")
        self.participant_note.grid(row=1, column=1, padx=5, pady=(0, 5), sticky="w")
        part_frame.columnconfigure(1, weight=1)
        self.participant_id_var.trace_add("write", lambda *a: self.schedule_preflight())
        if extra_rows: extra_rows(part_frame)
        return part_frame

    def back_to_main(self): self.window.destroy()

    def browse_log_dir_participant(self):
        dp = filedialog.askdirectory(parent=self.window, initialdir=self.log_dir_participant_var.get(), title="Select Participant Log Directory")
        if dp: self.log_dir_participant_var.set(dp)

    # --- Pre-flight ---
    def schedule_preflight(self):
        """Debounced refresh, so typing doesn't re-run file checks per keystroke."""
        if not hasattr(self, 'preflight'): return
        if self._preflight_job: self.window.after_cancel(self._preflight_job)
        self._preflight_job = self.window.after(250, self.refresh_preflight)

    def refresh_preflight(self):
        self._preflight_job = None
        display = self.display_picker.selected()
        checks = list(self.extra_checks(display))
        checks += display_checks(display, self.flicker_rates())
        checks.append(folder_check(self.log_dir_participant_var.get()))
        checks += image_checks(self.img1_path_var.get(), self.img2_path_var.get(), display)
        pid = self.participant_id_var.get().strip()
        pcheck = participant_check(self.log_dir_participant_var.get(), pid)
        self.participant_note.configure(text=pcheck[1] if pcheck else "")
        if pcheck: checks.append(('warn', "Participant ID already has data (see above)"))
        self.preflight.set(checks)
        canonical = (os.path.abspath(self.img1_path_var.get()) == os.path.abspath(resource_path(CANONICAL_IMAGE1)) and
                     os.path.abspath(self.img2_path_var.get()) == os.path.abspath(resource_path(CANONICAL_IMAGE2)))
        self.canonical_label.configure(text="Canonical blue/yellow pair · hashes are logged" if canonical
                                       else "Not the canonical acheck_by pair · hashes are logged")

    # --- Shared validation ---
    def validate_common(self, c):
        c.participant_id = self.participant_id_var.get().strip()
        c.image1_path = self.img1_path_var.get()
        c.image2_path = self.img2_path_var.get()
        c.log_dir_participant = self.log_dir_participant_var.get()
        c.display_index = self.display_picker.index()
        c.display_mismatch_accepted = False
        if not c.participant_id:
            messagebox.showerror("Input Error", "Participant ID required.", parent=self.window); return False
        if any(ch in c.participant_id for ch in r'/\:*?"<>|'):
            messagebox.showerror("Input Error", "Participant ID has invalid chars.", parent=self.window); return False
        for label, p in (("Image 1", c.image1_path), ("Image 2", c.image2_path)):
            ok, info = check_image(p)
            if not ok:
                messagebox.showerror("Input Error", f"{label} {info}.", parent=self.window); return False
        if not c.log_dir_participant:
            messagebox.showerror("Input Error", "Participant Log Directory required.", parent=self.window); return False
        try: os.makedirs(c.log_dir_participant, exist_ok=True)
        except Exception as e: messagebox.showerror("Directory Error", f"Cannot create log dir:\n{e}", parent=self.window); return False
        return True

    def confirm_display(self, c):
        """Display-check dialog before going full-screen. Returns False to go
        back to the form ("Choose Another Display" focuses the picker)."""
        display = self.display_picker.selected()
        if not display or tuple(display['size']) == EXPECTED_DISPLAY_SIZE: return True
        w, h = display['size']; ew, eh = EXPECTED_DISPLAY_SIZE
        body = [f"Expected:  {ew} × {eh}",
                f"Found:  {w} × {h} on {describe_display(display)}",
                f"The {ew}×{eh} checkerboards would be scaled by {w / ew:.2f} × {h / eh:.2f} to fit, "
                "so the checks may come out uneven or stretched. On Windows, also check display scaling is 100%.",
                f"If you continue, the data file records Display_Check = MISMATCH {w}x{h}."]
        choice = ask_choice(self.window, "Display Check", "This display doesn't match the protocol", body,
                            [('continue', "Continue Anyway", 'secondary-outline'),
                             ('choose', "Choose Another Display…", 'primary-outline'),
                             ('cancel', "Cancel", 'primary')], default='cancel')
        if choice == 'continue': c.display_mismatch_accepted = True; return True
        if choice == 'choose':
            self.display_picker.reload()
            self.display_picker.combo.focus_set()
        return False

    def remember(self):
        values = {'remember': bool(self.remember_var.get())}
        if self.remember_var.get():
            values.update({'image1': self.img1_path_var.get(), 'image2': self.img2_path_var.get(),
                           'log_dir': self.log_dir_participant_var.get(),
                           'display_index': self.display_picker.index()})
            values.update(self.current_settings())
        save_settings(self.SETTINGS_SECTION, values)

    def run_and_summarize(self, run_fn, config, title, tonic=False):
        self.remember()
        self.window.withdraw()
        try:
            result = run_fn(config)
        finally:
            self.window.deiconify()
        show_run_summary(self.window, title, result, tonic=tonic)
        self.refresh_preflight()

# --- Experiment Runner Window ---
class ExperimentRunnerWindow(_RunWindowBase):
    TITLE = "M-VAST 3 - Run Experiment"
    SETTINGS_SECTION = "run"
    START_LABEL = "Start Experiment"

    def __init__(self, parent, app):
        self.config = RunConfig()
        self.trials, self.csv_errors = [], []
        super().__init__(parent, app)
        self.csv_entry.focus()

    def build_top_sections(self, body):
        csv_frame = ttk.Labelframe(body, text="Experiment Setup File")
        csv_frame.pack(fill=X, pady=(0, 10))
        ttk.Label(csv_frame, text="Master Trial CSV:", font=("", 10)).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.master_csv_var = tk.StringVar(value=self.settings.get('master_csv', ""))
        self.csv_entry = ttk.Entry(csv_frame, textvariable=self.master_csv_var, width=50, state="readonly", font=("", 10))
        self.csv_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(csv_frame, text="Browse...", command=self.browse_master_csv, style='outline.TButton').grid(row=0, column=2, padx=5, pady=5)
        self.csv_summary = ttk.Label(csv_frame, text="", font=HINT_FONT, wraplength=600, justify="left")
        self.csv_summary.grid(row=1, column=1, columnspan=2, padx=5, pady=(0, 5), sticky="w")
        csv_frame.columnconfigure(1, weight=1)
        self.master_csv_var.trace_add("write", lambda *a: self.load_csv_summary())
        self.load_csv_summary()
        self.build_participant_frame(body)

    def load_csv_summary(self):
        path = self.master_csv_var.get()
        if not path:
            self.trials, self.csv_errors = [], []
            self.csv_summary.configure(text="Select the master trial CSV made by Generate Experiment Setup.", bootstyle="secondary")
        elif not os.path.exists(path):
            self.trials, self.csv_errors = [], ["File not found"]
            self.csv_summary.configure(text="✗ File not found.", bootstyle="danger")
        else:
            self.trials, self.csv_errors = load_master_csv(path)
            if self.csv_errors:
                more = f" (+{len(self.csv_errors) - 3} more)" if len(self.csv_errors) > 3 else ""
                self.csv_summary.configure(text="✗ " + "; ".join(self.csv_errors[:3]) + more, bootstyle="danger")
            else:
                self.csv_summary.configure(
                    text=f"✓ {len(self.trials)} trials, values in range · ≈ {estimate_minutes(self.trials):.0f} min incl. ratings · "
                         f"SHA-256 {short_hash(path)}", bootstyle="success")
        self.schedule_preflight()

    def flicker_rates(self):
        return [t['checkerboard_hz'] for t in self.trials]

    def extra_checks(self, display):
        if not self.master_csv_var.get(): return [('bad', "No master trial CSV selected")]
        if self.csv_errors: return [('bad', "Master trial CSV has problems (see above)")]
        return []

    def current_settings(self):
        return {'master_csv': self.master_csv_var.get()}

    def browse_master_csv(self):
        init_dir = os.path.join(DEFAULT_LOG_DIR_BASE, SETUPS_SUBDIR)
        fp = filedialog.askopenfilename(parent=self.window, title="Select Master CSV", filetypes=[("CSV files", "*.csv")], initialdir=init_dir if os.path.exists(init_dir) else APP_BASE_PATH)
        if fp: self.master_csv_var.set(fp)

    def start(self):
        c = self.config
        c.master_csv_path = self.master_csv_var.get()
        if not (c.master_csv_path and os.path.exists(c.master_csv_path)):
            messagebox.showerror("Input Error", "Valid Master CSV required.", parent=self.window); return
        trials, errors = load_master_csv(c.master_csv_path)   # re-read: the file may have changed
        if errors:
            messagebox.showerror("CSV Error", "The master CSV has problems:\n\n" + "\n".join(errors[:10]), parent=self.window); return
        c.trials_data = trials
        if not self.validate_common(c): return
        if not self.confirm_display(c): return
        self.run_and_summarize(execute_experiment_run, c, f"Run Summary - {c.participant_id}")

# --- Tonic fMRI Runner Window ---
class TonicRunnerWindow(_RunWindowBase):
    """Runner for the tonic M-VAST + fMRI paradigm: a single continuous,
    constant-brightness flickering run started by the scanner trigger. No
    randomization schedule / master CSV and no button responses are used."""
    TITLE = "M-VAST 3 - Run Tonic fMRI"
    SETTINGS_SECTION = "tonic"
    START_LABEL = "Start Tonic Run"

    def __init__(self, parent, app):
        self.config = TonicRunConfig()
        self._listen_job = None
        super().__init__(parent, app)
        self.part_id_entry.focus()

    def build_top_sections(self, body):
        s = self.settings
        def scanner_row(frame):
            self.scanner_var = tk.StringVar(value=s.get('scanner', "Outpatient (GE Architect)"))
            ttk.Label(frame, text="Scanner / Site:", font=("", 10)).grid(row=2, column=0, padx=5, pady=5, sticky="w")
            ttk.Combobox(frame, textvariable=self.scanner_var,
                         values=["Outpatient (GE Architect)", "Inpatient (Siemens Prisma)"],
                         font=("", 10)).grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.build_participant_frame(body, scanner_row)

    def build_middle_sections(self, body):
        s = self.settings
        self.brightness_var = tk.DoubleVar(value=s.get('brightness', DEFAULT_TONIC_BRIGHTNESS))
        self.hz_var = tk.DoubleVar(value=s.get('hz', DEFAULT_TONIC_HZ))
        self.duration_var = tk.DoubleVar(value=s.get('duration', DEFAULT_TONIC_DURATION))
        self.trigger_key_var = tk.StringVar(value=s.get('trigger_key', DEFAULT_TRIGGER_KEY))
        self.show_fixation_var = tk.BooleanVar(value=s.get('show_fixation', DEFAULT_TONIC_SHOW_FIXATION))

        param_frame = ttk.Labelframe(body, text="Tonic Run Parameters")
        param_frame.pack(fill=X, pady=(0, 10))
        param_frame.columnconfigure(2, weight=1)
        ttk.Label(param_frame, text="Constant Brightness (0.1–1.0):", font=("", 10)).grid(row=0, column=0, padx=5, pady=6, sticky="w")
        ttk.Spinbox(param_frame, from_=0.1, to=1.0, increment=0.1, textvariable=self.brightness_var, width=10, format="%.1f", font=("", 10)).grid(row=0, column=1, padx=5, pady=6, sticky="w")
        ttk.Label(param_frame, text="(1.0 = full image brightness)", font=HINT_FONT, foreground="gray").grid(row=0, column=2, padx=5, pady=6, sticky="w")

        ttk.Label(param_frame, text="Flicker Frequency (Hz):", font=("", 10)).grid(row=1, column=0, padx=5, pady=6, sticky="w")
        ttk.Spinbox(param_frame, from_=0.0, to=60.0, increment=0.5, textvariable=self.hz_var, width=10, format="%.1f", font=("", 10)).grid(row=1, column=1, padx=5, pady=6, sticky="w")
        self.hz_hint = ttk.Label(param_frame, text="", font=HINT_FONT, foreground="gray")
        self.hz_hint.grid(row=1, column=2, padx=5, pady=6, sticky="w")
        self.hz_var.trace_add("write", lambda *a: self.schedule_preflight())

        ttk.Label(param_frame, text="Duration (seconds):", font=("", 10)).grid(row=2, column=0, padx=5, pady=6, sticky="w")
        ttk.Spinbox(param_frame, from_=5.0, to=1800.0, increment=5.0, textvariable=self.duration_var, width=10, format="%.1f", font=("", 10)).grid(row=2, column=1, padx=5, pady=6, sticky="w")
        self.duration_hint = ttk.Label(param_frame, text="", font=HINT_FONT, foreground="gray")
        self.duration_hint.grid(row=2, column=2, padx=5, pady=6, sticky="w")
        self.duration_var.trace_add("write", lambda *a: self._update_duration_hint())
        self._update_duration_hint()

        ttk.Checkbutton(param_frame, text="Draw fixation cross (+)", variable=self.show_fixation_var
                        ).grid(row=3, column=0, columnspan=2, padx=5, pady=6, sticky="w")
        ttk.Label(param_frame, text="(leave off for image sets that already contain a cross, e.g. acheck_by)", font=HINT_FONT, foreground="gray").grid(row=3, column=2, padx=5, pady=6, sticky="w")

        trig_frame = ttk.Labelframe(body, text="Scanner Trigger")
        trig_frame.pack(fill=X, pady=(0, 10))
        trig_frame.columnconfigure(3, weight=1)
        ttk.Label(trig_frame, text="Trigger Key:", font=("", 10)).grid(row=0, column=0, padx=5, pady=6, sticky="w")
        ttk.Entry(trig_frame, textvariable=self.trigger_key_var, width=6, font=("", 10)).grid(row=0, column=1, padx=5, pady=6, sticky="w")
        self.test_btn = ttk.Button(trig_frame, text="Test Trigger…", command=self.test_trigger, style='outline.TButton')
        self.test_btn.grid(row=0, column=2, padx=5, pady=6)
        self.trigger_result = ttk.Label(trig_frame, text="", font=("", 10))
        self.trigger_result.grid(row=0, column=3, padx=5, pady=6, sticky="w")
        ttk.Label(trig_frame, text="Test Trigger listens for 10 s: start a scan (or press the key) to confirm the keystroke reaches this computer.\n"
                                   "During the run every pulse is logged as a Scanner_Pulse row. The intro screen continues only on SPACE.",
                  font=HINT_FONT, foreground="gray", justify="left").grid(row=1, column=1, columnspan=3, padx=5, pady=(0, 6), sticky="w")

    def _update_duration_hint(self):
        try:
            secs = float(self.duration_var.get())
            self.duration_hint.config(text=f"(≈ {secs / 60.0:.1f} min)")
        except (tk.TclError, ValueError):
            self.duration_hint.config(text="")

    def flicker_rates(self):
        try: return [float(self.hz_var.get())]
        except (tk.TclError, ValueError): return []

    def refresh_preflight(self):
        super().refresh_preflight()
        display = self.display_picker.selected()
        rates = self.flicker_rates()
        if not rates: self.hz_hint.configure(text="", bootstyle="secondary"); return
        hz = rates[0]
        fph = frames_per_half_cycle(hz, display and display['refresh_hz'])
        if hz <= 0: self.hz_hint.configure(text="(0 = static image, no flicker)", bootstyle="secondary")
        elif fph is None: self.hz_hint.configure(text="(refresh rate is measured at run start)", bootstyle="secondary")
        elif abs(fph - round(fph)) < 0.01:
            self.hz_hint.configure(text=f"✓ {round(fph)} frames per half-cycle at {display['refresh_hz']} Hz", bootstyle="success")
        else:
            self.hz_hint.configure(text=f"! {fph:.2f} frames per half-cycle at {display['refresh_hz']} Hz (not a whole number)", bootstyle="warning")

    def current_settings(self):
        out = {'scanner': self.scanner_var.get(), 'trigger_key': self.trigger_key_var.get(),
               'show_fixation': bool(self.show_fixation_var.get())}
        for k, var in (('brightness', self.brightness_var), ('hz', self.hz_var), ('duration', self.duration_var)):
            try: out[k] = float(var.get())
            except (tk.TclError, ValueError): pass
        return out

    def test_trigger(self, seconds=10):
        """Listen for the trigger keystroke for `seconds` and report the count
        and the interval between pulses (the scanner's TR)."""
        key = self.trigger_key_var.get().strip().lower()
        if len(key) != 1:
            messagebox.showerror("Input Error", "Trigger key must be a single character (e.g., 5 or t).", parent=self.window); return
        if self._listen_job: return
        times = []
        def on_key(e):
            if (e.char and e.char.lower() == key) or e.keysym.lower() == key:
                times.append(e.time / 1000.0)   # Tk event time, ms
                self.trigger_result.configure(text=f"Listening… received '{key}' ×{len(times)}", bootstyle="info")
        def finish():
            self._listen_job = None
            self.window.unbind("<KeyPress>")
            self.test_btn.configure(state="normal")
            if not times:
                self.trigger_result.configure(text=f"✗ No '{key}' received in {seconds} s", bootstyle="danger"); return
            text = f"✓ Received '{key}' ×{len(times)}"
            if len(times) > 1:
                iv = [b - a for a, b in zip(times, times[1:])]
                text += f" · interval ≈ {sorted(iv)[len(iv) // 2]:.2f} s (the TR)"
            self.trigger_result.configure(text=text, bootstyle="success")
        self.window.bind("<KeyPress>", on_key)
        self.window.focus_force()
        self.test_btn.configure(state="disabled")
        self.trigger_result.configure(text=f"Listening for '{key}' for {seconds} s…", bootstyle="info")
        self._listen_job = self.window.after(seconds * 1000, finish)

    def start(self):
        c = self.config
        c.scanner = self.scanner_var.get().strip()
        c.trigger_key = self.trigger_key_var.get().strip()
        c.show_fixation = bool(self.show_fixation_var.get())
        if not self.validate_common(c): return
        try:
            c.brightness = float(self.brightness_var.get())
            c.hz = float(self.hz_var.get())
            c.duration = float(self.duration_var.get())
        except (tk.TclError, ValueError):
            messagebox.showerror("Input Error", "Brightness, frequency and duration must be numbers.", parent=self.window); return
        if not (0.1 <= c.brightness <= 1.0):
            messagebox.showerror("Input Error", "Constant brightness must be between 0.1 and 1.0.", parent=self.window); return
        if not (0.0 <= c.hz <= 60.0):
            messagebox.showerror("Input Error", "Flicker frequency must be between 0 and 60 Hz.", parent=self.window); return
        if not (5.0 <= c.duration <= 1800.0):
            messagebox.showerror("Input Error", "Duration must be between 5 and 1800 seconds.", parent=self.window); return
        if len(c.trigger_key) != 1:
            messagebox.showerror("Input Error", "Trigger key must be a single character (e.g., 5 or t).", parent=self.window); return
        if c.image1_path == c.image2_path and c.hz > 0 and \
           not messagebox.askyesno("Warning", "Images are the same (no flicker will be visible). Continue?", parent=self.window):
            return
        if not self.confirm_display(c): return
        if self._listen_job:
            self.window.after_cancel(self._listen_job); self._listen_job = None; self.window.unbind("<KeyPress>")
            self.test_btn.configure(state="normal")
        self.run_and_summarize(execute_tonic_run, c, f"Tonic Run Summary - {c.participant_id}", tonic=True)
