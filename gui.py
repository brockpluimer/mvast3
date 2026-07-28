# -*- coding: utf-8 -*-
"""M-VAST 3 - Tkinter GUI: main menu and run configuration windows."""

import os
import csv
import random
import shutil
import webbrowser

import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk

from config import (
    APP_VERSION, HELP_FILE_NAME, APP_BASE_PATH,
    DEFAULT_LOG_DIR_BASE,
    SCHEDULES_SUBDIR, SETUPS_SUBDIR,
    DEFAULT_STIMULUS_DURATION, DEFAULT_FIXATION_DURATION,
    DEFAULT_CHECKERBOARD_HZ, DEFAULT_RANDOMIZED_BLOCKS_COUNT,
    DEFAULT_TONIC_DURATION, DEFAULT_TONIC_BRIGHTNESS, DEFAULT_TONIC_HZ,
    DEFAULT_TRIGGER_KEY, DEFAULT_TONIC_SHOW_FIXATION,
    BRIGHTNESS_LEVELS_BASE, RAMP_UP_TRIALS_COUNT, TRIALS_PER_BLOCK,
    resource_path, RunConfig, TonicRunConfig,
)
from runner import execute_experiment_run, execute_tonic_run

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
            self.root.style.configure('danger.TButton', anchor=CENTER)
            self.root.style.configure('secondary.TButton', anchor=CENTER)

            self.help_btn = ttk.Button(footer_frame, text="Help / How to Use",
                                  command=self.show_help,
                                  style='danger.TButton', padding=(14, 4))
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

RUN TONIC fMRI (concurrent MRI acquisition):
    *   Use this instead of "Run Experiment" for the tonic M-VAST + fMRI run.
    *   No setup CSV is needed. Enter a 'Participant ID', pick the two
        checkerboard images, and set the constant brightness, flicker Hz,
        duration (~6 min), and scanner trigger key (default '5').
    *   "Draw fixation cross (+)" is OFF by default because the acheck_by
        images already have a cross built in. Turn it on only for image sets
        (e.g., the strobe images) that do not include one.
    *   Click "Start Tonic Run". A "waiting for scanner" screen appears.
    *   Start the fMRI sequence. When the scanner sends its trigger pulse
        (delivered as the trigger keystroke), the flickering checkerboard
        begins automatically and runs at constant brightness for the full
        duration while the participant fixates the central cross.
    *   Trigger time and stimulus onset/offset are logged for fMRI alignment.
    *   Press ESC to abort at any time.
        """
        self._show_help_dialog(help_text)

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
        self.window.geometry("700x900")
        self.window.minsize(650, 780)
        
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
        btn_container = ttk.Frame(main_frame, padding=(0, 10))
        btn_container.pack(side=BOTTOM, fill=X, pady=(10, 5))

        self.generate_button = ttk.Button(
            btn_container,
            text="Generate Experiment Files",
            command=self.process_generation,
            style='success.TButton'
        )
        self.generate_button.pack(pady=10, ipadx=20, ipady=8)

        # ============================================================
        # SECTION 5: Info Label (pinned just above the button)
        # ============================================================
        info_container = ttk.Frame(main_frame, padding=(5, 10))
        info_container.pack(side=BOTTOM, fill=X, pady=(5, 5))

        self.info_label = ttk.Label(
            info_container,
            text="",
            justify="left",
            wraplength=600,
            font=small_font
        )
        self.info_label.pack(fill=X, anchor="w")
        
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

        csv_frame = ttk.Labelframe(main_frame, text="Experiment Setup File")
        csv_frame.pack(fill=X, pady=(0, 10))
        ttk.Label(csv_frame, text="Master Trial CSV:", font=("",lbl_font_size)).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.master_csv_var = tk.StringVar()
        self.csv_entry = ttk.Entry(csv_frame, textvariable=self.master_csv_var, width=50, state="readonly", font=("",lbl_font_size))
        self.csv_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(csv_frame, text="Browse...", command=self.browse_master_csv, style='outline.TButton').grid(row=0, column=2, padx=5, pady=5)
        csv_frame.columnconfigure(1, weight=1)

        part_id_frame = ttk.Labelframe(main_frame, text="Participant Information")
        part_id_frame.pack(fill=X, pady=(0,10))
        ttk.Label(part_id_frame, text="Participant ID:", font=("",lbl_font_size)).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.participant_id_var = tk.StringVar()
        self.part_id_entry = ttk.Entry(part_id_frame, textvariable=self.participant_id_var, width=30, font=("",lbl_font_size))
        self.part_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        part_id_frame.columnconfigure(1, weight=1)

        img_frame = ttk.Labelframe(main_frame, text="Stimulus Image Files")
        img_frame.pack(fill=X, pady=(0, 10))
        self.img1_path_var, self.img2_path_var = tk.StringVar(), tk.StringVar()
        ttk.Label(img_frame, text="Image 1:", font=("",lbl_font_size)).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(img_frame, textvariable=self.img1_path_var, width=40, state='readonly', font=("",lbl_font_size)).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(img_frame, text="Browse...", command=self.browse_image1, style='outline.TButton').grid(row=0, column=2, padx=5, pady=5)
        ttk.Label(img_frame, text="Image 2:", font=("",lbl_font_size)).grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(img_frame, textvariable=self.img2_path_var, width=40, state='readonly', font=("",lbl_font_size)).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(img_frame, text="Browse...", command=self.browse_image2, style='outline.TButton').grid(row=1, column=2, padx=5, pady=5)
        img_frame.columnconfigure(1, weight=1)

        log_dir_frame = ttk.Labelframe(main_frame, text="Participant Data Log Directory")
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

# --- Tonic fMRI Runner Window ---
class TonicRunnerWindow:
    """Runner for the tonic M-VAST + fMRI paradigm: a single continuous,
    constant-brightness flickering run started by the scanner trigger. No
    randomization schedule / master CSV and no button responses are used."""
    def __init__(self, parent, app):
        self.parent = parent; self.app = app
        self.window = ttk.Toplevel(parent)
        self.window.title("M-VAST 3 - Run Tonic fMRI")
        self.window.geometry("800x760")
        self.window.minsize(700, 700)
        self.window.grab_set()
        self.config = TonicRunConfig()
        self.create_runner_gui()

    def create_runner_gui(self):
        main_frame = ttk.Frame(self.window, padding=(20, 20))
        main_frame.pack(fill=BOTH, expand=YES)

        ttk.Button(main_frame, text="← Back to Main Menu", command=self.back_to_main, style='secondary.TButton').pack(anchor='w', pady=(0, 15))

        lbl_font_size = 10

        # --- Tkinter variables ---
        self.participant_id_var = tk.StringVar()
        self.scanner_var = tk.StringVar(value="Outpatient (GE Architect)")
        self.img1_path_var, self.img2_path_var = tk.StringVar(), tk.StringVar()
        self.brightness_var = tk.DoubleVar(value=DEFAULT_TONIC_BRIGHTNESS)
        self.hz_var = tk.DoubleVar(value=DEFAULT_TONIC_HZ)
        self.duration_var = tk.DoubleVar(value=DEFAULT_TONIC_DURATION)
        self.trigger_key_var = tk.StringVar(value=DEFAULT_TRIGGER_KEY)
        self.show_fixation_var = tk.BooleanVar(value=DEFAULT_TONIC_SHOW_FIXATION)
        self.log_dir_participant_var = tk.StringVar(value=self.config.log_dir_participant)

        # --- Participant / scanner ---
        part_frame = ttk.Labelframe(main_frame, text="Participant Information")
        part_frame.pack(fill=X, pady=(0, 10))
        ttk.Label(part_frame, text="Participant ID:", font=("", lbl_font_size)).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.part_id_entry = ttk.Entry(part_frame, textvariable=self.participant_id_var, width=30, font=("", lbl_font_size))
        self.part_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Label(part_frame, text="Scanner / Site:", font=("", lbl_font_size)).grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ttk.Combobox(part_frame, textvariable=self.scanner_var,
                     values=["Outpatient (GE Architect)", "Inpatient (Siemens Prisma)"],
                     font=("", lbl_font_size)).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        part_frame.columnconfigure(1, weight=1)

        # --- Images ---
        img_frame = ttk.Labelframe(main_frame, text="Stimulus Image Files")
        img_frame.pack(fill=X, pady=(0, 10))
        ttk.Label(img_frame, text="Image 1:", font=("", lbl_font_size)).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(img_frame, textvariable=self.img1_path_var, width=40, state='readonly', font=("", lbl_font_size)).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(img_frame, text="Browse...", command=lambda: self.browse_image(self.img1_path_var), style='outline.TButton').grid(row=0, column=2, padx=5, pady=5)
        ttk.Label(img_frame, text="Image 2:", font=("", lbl_font_size)).grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(img_frame, textvariable=self.img2_path_var, width=40, state='readonly', font=("", lbl_font_size)).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(img_frame, text="Browse...", command=lambda: self.browse_image(self.img2_path_var), style='outline.TButton').grid(row=1, column=2, padx=5, pady=5)
        img_frame.columnconfigure(1, weight=1)

        # --- Tonic parameters ---
        param_frame = ttk.Labelframe(main_frame, text="Tonic Run Parameters")
        param_frame.pack(fill=X, pady=(0, 10))
        param_frame.columnconfigure(1, weight=0)
        param_frame.columnconfigure(2, weight=1)

        ttk.Label(param_frame, text="Constant Brightness (0.1–1.0):", font=("", lbl_font_size)).grid(row=0, column=0, padx=5, pady=6, sticky="w")
        ttk.Spinbox(param_frame, from_=0.1, to=1.0, increment=0.1, textvariable=self.brightness_var, width=10, format="%.1f", font=("", lbl_font_size)).grid(row=0, column=1, padx=5, pady=6, sticky="w")
        ttk.Label(param_frame, text="(1.0 = full image brightness)", font=("", 9), foreground="gray").grid(row=0, column=2, padx=5, pady=6, sticky="w")

        ttk.Label(param_frame, text="Flicker Frequency (Hz):", font=("", lbl_font_size)).grid(row=1, column=0, padx=5, pady=6, sticky="w")
        ttk.Spinbox(param_frame, from_=0.0, to=60.0, increment=0.5, textvariable=self.hz_var, width=10, format="%.1f", font=("", lbl_font_size)).grid(row=1, column=1, padx=5, pady=6, sticky="w")
        ttk.Label(param_frame, text="(0 = static image, no flicker)", font=("", 9), foreground="gray").grid(row=1, column=2, padx=5, pady=6, sticky="w")

        ttk.Label(param_frame, text="Duration (seconds):", font=("", lbl_font_size)).grid(row=2, column=0, padx=5, pady=6, sticky="w")
        ttk.Spinbox(param_frame, from_=5.0, to=1800.0, increment=5.0, textvariable=self.duration_var, width=10, format="%.1f", font=("", lbl_font_size)).grid(row=2, column=1, padx=5, pady=6, sticky="w")
        self.duration_hint = ttk.Label(param_frame, text="", font=("", 9), foreground="gray")
        self.duration_hint.grid(row=2, column=2, padx=5, pady=6, sticky="w")
        self.duration_var.trace_add("write", lambda *a: self._update_duration_hint())
        self._update_duration_hint()

        ttk.Label(param_frame, text="Scanner Trigger Key:", font=("", lbl_font_size)).grid(row=3, column=0, padx=5, pady=6, sticky="w")
        ttk.Entry(param_frame, textvariable=self.trigger_key_var, width=10, font=("", lbl_font_size)).grid(row=3, column=1, padx=5, pady=6, sticky="w")
        ttk.Label(param_frame, text="(keystroke the scanner sends at each pulse; can also be pressed manually)", font=("", 9), foreground="gray").grid(row=3, column=2, padx=5, pady=6, sticky="w")

        ttk.Checkbutton(param_frame, text="Draw fixation cross (+)", variable=self.show_fixation_var
                        ).grid(row=4, column=0, columnspan=2, padx=5, pady=6, sticky="w")
        ttk.Label(param_frame, text="(leave off for image sets that already contain a cross, e.g. acheck_by)", font=("", 9), foreground="gray").grid(row=4, column=2, padx=5, pady=6, sticky="w")

        # --- Log directory ---
        log_dir_frame = ttk.Labelframe(main_frame, text="Participant Data Log Directory")
        log_dir_frame.pack(fill=X, pady=(0, 15))
        ttk.Label(log_dir_frame, text="Directory:", font=("", lbl_font_size)).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(log_dir_frame, textvariable=self.log_dir_participant_var, width=40, state="readonly", font=("", lbl_font_size)).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(log_dir_frame, text="Browse...", command=self.browse_log_dir_participant, style='outline.TButton').grid(row=0, column=2, padx=5, pady=5)
        log_dir_frame.columnconfigure(1, weight=1)

        btn_frame = ttk.Frame(main_frame, padding=(0, 10)); btn_frame.pack(fill=X)
        ttk.Button(btn_frame, text="Start Tonic Run", command=self.start_tonic_run, style='success.TButton', padding=(10, 5)).pack(side=RIGHT)

        self.part_id_entry.focus()

    def _update_duration_hint(self):
        try:
            secs = float(self.duration_var.get())
            self.duration_hint.config(text=f"(≈ {secs / 60.0:.1f} min)")
        except (tk.TclError, ValueError):
            self.duration_hint.config(text="")

    def back_to_main(self): self.window.destroy()

    def browse_image(self, var):
        init_img_dir = os.path.join(APP_BASE_PATH, "images")
        fp = filedialog.askopenfilename(parent=self.window, title="Select Image",
                                        filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.gif")],
                                        initialdir=init_img_dir if os.path.exists(init_img_dir) else APP_BASE_PATH)
        if fp: var.set(fp)

    def browse_log_dir_participant(self):
        dp = filedialog.askdirectory(parent=self.window, initialdir=self.log_dir_participant_var.get(), title="Select Participant Log Directory")
        if dp: self.log_dir_participant_var.set(dp)

    def validate_inputs(self):
        c = self.config
        c.participant_id = self.participant_id_var.get().strip()
        c.scanner = self.scanner_var.get().strip()
        c.image1_path = self.img1_path_var.get()
        c.image2_path = self.img2_path_var.get()
        c.log_dir_participant = self.log_dir_participant_var.get()
        c.trigger_key = self.trigger_key_var.get().strip()
        c.show_fixation = bool(self.show_fixation_var.get())

        if not c.participant_id:
            messagebox.showerror("Input Error", "Participant ID required.", parent=self.window); return False
        if any(ch in c.participant_id for ch in r'/\:*?"<>|'):
            messagebox.showerror("Input Error", "Participant ID has invalid chars.", parent=self.window); return False
        if not (c.image1_path and os.path.exists(c.image1_path)):
            messagebox.showerror("Input Error", "Valid Image 1 required.", parent=self.window); return False
        if not (c.image2_path and os.path.exists(c.image2_path)):
            messagebox.showerror("Input Error", "Valid Image 2 required.", parent=self.window); return False
        try:
            c.brightness = float(self.brightness_var.get())
            c.hz = float(self.hz_var.get())
            c.duration = float(self.duration_var.get())
        except (tk.TclError, ValueError):
            messagebox.showerror("Input Error", "Brightness, frequency and duration must be numbers.", parent=self.window); return False
        if not (0.1 <= c.brightness <= 1.0):
            messagebox.showerror("Input Error", "Constant brightness must be between 0.1 and 1.0.", parent=self.window); return False
        if not (0.0 <= c.hz <= 60.0):
            messagebox.showerror("Input Error", "Flicker frequency must be between 0 and 60 Hz.", parent=self.window); return False
        if not (5.0 <= c.duration <= 1800.0):
            messagebox.showerror("Input Error", "Duration must be between 5 and 1800 seconds.", parent=self.window); return False
        if len(c.trigger_key) != 1:
            messagebox.showerror("Input Error", "Trigger key must be a single character (e.g., 5 or t).", parent=self.window); return False
        if c.image1_path == c.image2_path and c.hz > 0 and \
           not messagebox.askyesno("Warning", "Images are the same (no flicker will be visible). Continue?", parent=self.window):
            return False
        try:
            os.makedirs(c.log_dir_participant, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Directory Error", f"Cannot create log dir:\n{e}", parent=self.window); return False
        return True

    def start_tonic_run(self):
        if not self.validate_inputs(): return
        self.window.withdraw()
        execute_tonic_run(self.config)
        self.window.deiconify()

