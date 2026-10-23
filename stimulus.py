# -*- coding: utf-8 -*-
"""M-VAST 3 - pygame stimulus presentation, rating scale, and helpers."""

import os
import gc
import glob
import math
import time
import ctypes
import statistics
import numpy as np
import pygame
from datetime import datetime

from config import (
    WHITE, BLACK, GREEN, DARK_GREEN, GRAY_COLOR,
    PYGAME_REFERENCE_SCREEN_HEIGHT, EXPECTED_DISPLAY_SIZE,
    INTERVAL_OVER_FACTOR, INTERVAL_UNDER_FACTOR,
)

# Keep the full-screen window up if focus moves to another screen (SDL
# minimizes full-screen windows on focus loss by default).
os.environ.setdefault("SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS", "0")

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


# --- Display Discovery and Setup ---
class _SDLDisplayMode(ctypes.Structure):
    _fields_ = [("format", ctypes.c_uint32), ("w", ctypes.c_int), ("h", ctypes.c_int),
                ("refresh_rate", ctypes.c_int), ("driverdata", ctypes.c_void_p)]

class _SDLRect(ctypes.Structure):
    _fields_ = [("x", ctypes.c_int), ("y", ctypes.c_int), ("w", ctypes.c_int), ("h", ctypes.c_int)]

_sdl_lib_cache = []
def _sdl_lib():
    """The SDL2 library pygame itself loaded, for the few display queries
    pygame 2.6 doesn't expose (name, OS refresh rate, bounds). None if it
    can't be found; callers fall back to pygame-only information."""
    if _sdl_lib_cache: return _sdl_lib_cache[0]
    lib = None
    base = os.path.dirname(pygame.__file__)
    candidates = (glob.glob(os.path.join(base, ".dylibs", "libSDL2-*.dylib")) +
                  glob.glob(os.path.join(base, "SDL2.dll")) +
                  glob.glob(os.path.join(base + ".libs", "libSDL2-*.so*")))
    for path in candidates:
        try:
            lib = ctypes.CDLL(path)
            lib.SDL_GetDisplayName.restype = ctypes.c_char_p
            break
        except (OSError, AttributeError):
            lib = None
    _sdl_lib_cache.append(lib)
    return lib

def list_displays():
    """Describe each connected display: index, name, desktop size, OS refresh
    rate and bounds. Initializes the pygame display subsystem if needed and
    shuts it down again if it wasn't already running."""
    was_init = pygame.display.get_init()
    if not was_init: pygame.display.init()
    displays = []
    try:
        sizes = pygame.display.get_desktop_sizes()
        lib = _sdl_lib()
        for i, (w, h) in enumerate(sizes):
            d = {'index': i, 'name': "", 'size': (w, h), 'refresh_hz': None, 'bounds': None}
            if lib:
                try:
                    mode, rect = _SDLDisplayMode(), _SDLRect()
                    if lib.SDL_GetDesktopDisplayMode(i, ctypes.byref(mode)) == 0 and mode.refresh_rate > 0:
                        d['refresh_hz'] = mode.refresh_rate
                    if lib.SDL_GetDisplayBounds(i, ctypes.byref(rect)) == 0:
                        d['bounds'] = (rect.x, rect.y, rect.w, rect.h)
                    name = lib.SDL_GetDisplayName(i)
                    # macOS reports the index as the name; only keep real names
                    if name and name.decode(errors='replace') != str(i):
                        d['name'] = name.decode(errors='replace')
                except Exception:
                    pass
            displays.append(d)
    finally:
        if not was_init: pygame.display.quit()
    return displays

def describe_display(d):
    """One-line label used in the GUI display picker."""
    label = f"Display {d['index'] + 1}"
    if d['name']: label += f": {d['name']}"
    w, h = d['size']
    label += f" ({w}×{h}"
    if d['refresh_hz']: label += f" @ {d['refresh_hz']} Hz"
    return label + ")"

def identify_displays(seconds=2.0):
    """Show a large display number on every connected screen for `seconds`,
    so the operator can tell which index is the participant's display."""
    from pygame._sdl2.video import Window, Renderer, Texture
    displays = list_displays()
    pygame.display.init(); pygame.font.init()
    windows = []
    try:
        font = pygame.font.Font(None, 360)
        for d in displays:
            size = (420, 420)
            if d['bounds']:
                x, y, w, h = d['bounds']
                pos = (x + (w - size[0]) // 2, y + (h - size[1]) // 2)
            else:
                pos = (0x2FFF0000 | d['index'],) * 2   # SDL_WINDOWPOS_CENTERED_DISPLAY(i)
            win = Window(f"Display {d['index'] + 1}", size=size, position=pos, borderless=True, always_on_top=True)
            ren = Renderer(win)
            ren.draw_color = (26, 115, 232, 255); ren.clear()
            tex = Texture.from_surface(ren, font.render(str(d['index'] + 1), True, WHITE))
            tex.draw(dstrect=tex.get_rect(center=(size[0] // 2, size[1] // 2)))
            ren.present()
            windows.append((win, ren, tex))
        end = time.perf_counter() + seconds
        while time.perf_counter() < end:
            pygame.event.pump(); time.sleep(0.02)
    finally:
        for win, _, _ in windows: win.destroy()
        pygame.display.quit()

def open_display(display_index=0, caption="M-VAST 3"):
    """Open the full-screen stimulus window on `display_index` and measure the
    real refresh interval. Vsync is requested so board changes land on frame
    boundaries; if the driver can't provide it the window opens without vsync
    and `info['vsync']` is False. Returns (screen, info)."""
    pygame.init()
    if not pygame.font.get_init(): pygame.font.init()
    n = pygame.display.get_num_displays()
    if not (0 <= display_index < n):
        raise RuntimeError(f"Display {display_index + 1} is not connected ({n} display(s) found).")
    size = pygame.display.get_desktop_sizes()[display_index]
    try:
        screen = pygame.display.set_mode(size, pygame.FULLSCREEN | pygame.SCALED, vsync=1, display=display_index)
    except pygame.error:
        screen = pygame.display.set_mode(size, pygame.FULLSCREEN, display=display_index)
    pygame.display.set_caption(caption)
    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)   # keep the cursor confined to the task window

    os_refresh = next((d['refresh_hz'] for d in list_displays() if d['index'] == display_index), None)
    frame_period = measure_frame_period(screen)
    info = {
        'display_index': display_index,
        'size': screen.get_size(),
        'refresh_hz_os': os_refresh,
        # A blocking flip of >= 4 ms means vsync is actually pacing the loop.
        'vsync': frame_period is not None,
        'frame_period': frame_period,
        'refresh_hz_measured': (1.0 / frame_period) if frame_period else None,
    }
    return screen, info

def measure_frame_period(screen, n_flips=40):
    """Median time between back-to-back flips of a black screen. Returns None
    when flips don't block (no vsync), so callers fall back to pure timing."""
    screen.fill(BLACK); pygame.display.flip()
    times = []
    for _ in range(n_flips + 1):
        pygame.event.pump()
        screen.fill(BLACK); pygame.display.flip()
        times.append(time.perf_counter())
    period = statistics.median(b - a for a, b in zip(times, times[1:]))
    return period if period >= 0.004 else None

def display_check_result(size, mismatch_accepted=False):
    """Value for the Display_Check log row."""
    w, h = size
    if (w, h) == EXPECTED_DISPLAY_SIZE: return f"OK {w}x{h}"
    result = f"MISMATCH {w}x{h} (expected {EXPECTED_DISPLAY_SIZE[0]}x{EXPECTED_DISPLAY_SIZE[1]})"
    return result + (" - operator continued" if mismatch_accepted else "")

def frames_per_half_cycle(hz, refresh_hz):
    """How many display frames one half-cycle of the flicker lasts, or None."""
    if not hz or hz <= 0 or not refresh_hz: return None
    return refresh_hz / (2.0 * hz)

# --- Pygame Helper Functions ---
def load_checkerboard_images(screen_width, screen_height, img1_path, img2_path):
    """Load and scale both stimulus images. Raises RuntimeError on failure; a
    Tk dialog here would open behind the full-screen window."""
    try:
        if not os.path.exists(img1_path): raise FileNotFoundError(f"Img1 not found: {img1_path}")
        if not os.path.exists(img2_path): raise FileNotFoundError(f"Img2 not found: {img2_path}")
        b1_orig, b2_orig = pygame.image.load(img1_path), pygame.image.load(img2_path)
        b1_orig, b2_orig = b1_orig.convert(), b2_orig.convert()
        b1_scaled = pygame.transform.scale(b1_orig, (screen_width, screen_height))
        b2_scaled = pygame.transform.scale(b2_orig, (screen_width, screen_height))
        return b1_scaled, b2_scaled
    except Exception as e:
        raise RuntimeError(f"Failed to load/scale images:\n{e}") from e

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

def build_brightness_cache(board1, board2, factors):
    """Pre-compute the brightness-adjusted board pair for each distinct factor
    once, before the first trial, so no image work happens at stimulus onset."""
    return {f: (adjust_surface_brightness(board1, f), adjust_surface_brightness(board2, f))
            for f in sorted(set(factors))}

# Window focus/minimize events seen since the last take_focus_events() call.
_focus_events = [0]
def take_focus_events():
    """Return and reset the count of focus-loss / minimize events."""
    n = _focus_events[0]; _focus_events[0] = 0
    return n

def _poll_events(escape_quits=True, trigger_key=None, on_trigger=None):
    """Drain the event queue. Returns False if the run should stop (window
    closed, or ESC when escape_quits). Counts focus loss, and calls
    on_trigger(perf_time) for each scanner trigger keystroke."""
    for ev in pygame.event.get():
        if ev.type == pygame.QUIT: return False
        if ev.type in (pygame.WINDOWFOCUSLOST, pygame.WINDOWMINIMIZED):
            _focus_events[0] += 1
        elif ev.type == pygame.KEYDOWN:
            if escape_quits and ev.key == pygame.K_ESCAPE: return False
            if on_trigger and _event_matches_trigger(ev, trigger_key):
                on_trigger(time.perf_counter())
    return True

def show_message(screen, text, wait_for_key=True, escape_quits=True, continue_keys=None):
    """Draw centered text. When wait_for_key, waits for a key and returns
    False on ESC (if escape_quits) or window close, True otherwise. With
    continue_keys, only those keys continue; all other keys are ignored."""
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
                if ev.type == pygame.QUIT: return False
                if ev.type in (pygame.WINDOWFOCUSLOST, pygame.WINDOWMINIMIZED): _focus_events[0] += 1
                if ev.type == pygame.KEYDOWN:
                    if escape_quits and ev.key == pygame.K_ESCAPE: return False
                    if continue_keys is None or ev.key in continue_keys: return True
            pygame.time.wait(10)
    return True

def get_rating_with_click(screen, title_ignored, scale_type="unpleasantness"):
    """Returns the confirmed rating, or None if the participant pressed ESC
    or the window was closed."""
    pygame.mouse.set_visible(True)
    scale = RatingScale(screen, title_ignored, scale_type=scale_type)
    clock = pygame.time.Clock()
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.mouse.set_visible(False); return None
            if ev.type in (pygame.WINDOWFOCUSLOST, pygame.WINDOWMINIMIZED): _focus_events[0] += 1
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
        if not _poll_events(escape_quits): return False
        time.sleep(0.01)
    return True

def make_fixation_overlay(screen):
    """A '+' surface and its centered rect, for drawing over the stimulus."""
    pg_sf = max(0.5, min(3.0, screen.get_height() / PYGAME_REFERENCE_SCREEN_HEIGHT))
    cross_font_size = int(72 * pg_sf)
    try: cross_font = pygame.font.Font(None, cross_font_size)
    except: cross_font = pygame.font.SysFont("arial", cross_font_size)
    cross_surf = cross_font.render('+', True, WHITE)
    return cross_surf, cross_surf.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))

class FlickerResult:
    """Outcome of run_flicker. `flips` holds the perf_counter time right after
    each flip that changed the image (the first is stimulus onset); `offset`
    is when the loop exited; `pulses` holds trigger keystroke times."""
    def __init__(self, completed, flips, offset, pulses):
        self.completed = completed
        self.flips = flips
        self.offset = offset
        self.pulses = pulses

def run_flicker(screen, board1, board2, duration, hz, frame_period=None,
                overlay=None, escape_quits=True, trigger_key=None):
    """Alternate two pre-adjusted boards at `hz` for `duration` seconds.

    Board changes follow a fixed time grid anchored at onset (k * half-period)
    instead of chaining off the previous flip. After a stall the loop jumps to
    the grid slot that is current, so a stall shows up as one long interval and
    never as a burst of catch-up flips. With vsync (`frame_period` known) each
    flip is issued half a frame early so it lands on the vblank that starts the
    slot. Flips are timestamped in software right after flip() returns, not at
    photon onset.

    `overlay` is an optional (surface, rect) drawn over every board (e.g. a
    fixation cross). If `trigger_key` is given, its keystrokes are recorded.
    Returns a FlickerResult."""
    pygame.mouse.set_visible(False)
    pulses = []
    on_trigger = pulses.append if trigger_key else None
    boards = (board1, board2)
    # Latest timestamp known to sit on a vblank. Only flips that returned
    # promptly update it: a slow return means the timestamp may be late
    # (e.g. a stall right after the flip), which would skew the frame grid.
    vblank_ref = [None]

    def draw(i):
        screen.blit(boards[i], (0, 0))
        if overlay: screen.blit(*overlay)
        called = time.perf_counter()
        pygame.display.flip()
        t = time.perf_counter()
        if vblank_ref[0] is None or (frame_period and t - called <= frame_period + 0.002):
            vblank_ref[0] = t
        return t

    def wait_until(t):
        """Sleep/poll until perf_counter() >= t. False if the run was stopped."""
        while True:
            now = time.perf_counter()
            if now >= t: return True
            if not _poll_events(escape_quits, trigger_key, on_trigger): return False
            remaining = t - now
            if remaining > 0.003: time.sleep(min(remaining - 0.002, 0.005))  # spin the last ~2 ms

    gc_was_enabled = gc.isenabled()
    gc.disable()   # a collection mid-stimulus can stall a flip
    try:
        onset = draw(0)
        flips, shown = [onset], 0
        end = onset + duration
        if hz <= 0:   # static image: hold until the end
            ok = wait_until(end)
            return FlickerResult(ok, flips, time.perf_counter(), pulses)

        half = 1.0 / hz / 2.0
        lead = frame_period / 2.0 if frame_period else 0.0
        # Shortest time an image may stay up: just above the QC threshold
        # (INTERVAL_UNDER_FACTOR), so the loop never creates a flagged interval.
        min_show = INTERVAL_UNDER_FACTOR * half + 0.001
        k = 1
        while True:
            t_switch = onset + k * half
            if t_switch >= end:
                ok = wait_until(end)
                return FlickerResult(ok, flips, time.perf_counter(), pulses)
            if not wait_until(t_switch - lead):
                return FlickerResult(False, flips, time.perf_counter(), pulses)
            # If a stall made us late, move to the slot this flip would land
            # in. Skip that slot if less than half of it is left, or if the
            # previous image went up less than half a slot ago (a flip that
            # itself landed late): either way an image would only flash briefly.
            now = time.perf_counter()
            if frame_period:   # the first vblank after now (and after the last flip)
                ref = vblank_ref[0]
                lands = ref + max(1, math.ceil((max(now, flips[-1]) - ref) / frame_period - 1e-3)) * frame_period
            else:
                lands = now
            k = max(k, int((lands - onset) / half))
            if (onset + (k + 1) * half - lands < min_show or
                    lands - flips[-1] < min_show):
                k += 1
                continue
            if onset + k * half >= end or lands >= end: continue
            if k % 2 != shown:
                shown = k % 2
                flips.append(draw(shown))
            k += 1
    finally:
        if gc_was_enabled: gc.enable()

def summarize_flips(result, hz, ref_time):
    """Per-trial timing columns from a FlickerResult. Onset/offset are seconds
    since `ref_time`; intervals are between successive image changes."""
    onset = result.flips[0] if result.flips else None
    stats = {
        'Stim_Onset_s': f"{onset - ref_time:.4f}" if onset is not None else "",
        'Stim_Offset_s': f"{result.offset - ref_time:.4f}" if result.offset is not None else "",
        'Actual_Stimulus_Duration_s': f"{result.offset - onset:.4f}" if onset is not None and result.offset is not None else "",
        'N_Flips': len(result.flips),
        'Median_Interval_ms': "", 'Min_Interval_ms': "", 'Max_Interval_ms': "",
        'N_Intervals_Over_1p5x': "", 'N_Intervals_Under_0p5x': "",
    }
    intervals = [(b - a) * 1000.0 for a, b in zip(result.flips, result.flips[1:])]
    if intervals and hz > 0:
        nominal = 1000.0 / hz / 2.0
        stats.update({
            'Median_Interval_ms': f"{statistics.median(intervals):.2f}",
            'Min_Interval_ms': f"{min(intervals):.2f}",
            'Max_Interval_ms': f"{max(intervals):.2f}",
            'N_Intervals_Over_1p5x': sum(i > INTERVAL_OVER_FACTOR * nominal for i in intervals),
            'N_Intervals_Under_0p5x': sum(i < INTERVAL_UNDER_FACTOR * nominal for i in intervals),
        })
    return stats

FLIP_STAT_COLUMNS = ['Stim_Onset_s', 'Stim_Offset_s', 'Actual_Stimulus_Duration_s', 'N_Flips',
                     'Median_Interval_ms', 'Min_Interval_ms', 'Max_Interval_ms',
                     'N_Intervals_Over_1p5x', 'N_Intervals_Under_0p5x']

def _event_matches_trigger(event, trigger_key):
    """True if a KEYDOWN event corresponds to the configured trigger key.
    Matches both the produced character (event.unicode) and the key name so
    it works for scanner boxes and for a manual key press."""
    if event.type != pygame.KEYDOWN: return False
    tk_lower = trigger_key.lower()
    if event.unicode and event.unicode.lower() == tk_lower: return True
    try:
        if pygame.key.name(event.key).lower() == tk_lower: return True
    except Exception:
        pass
    return False

def wait_for_scanner_trigger(screen, trigger_key):
    """Display a hold screen until the scanner trigger key is received.
    Returns the (wall_clock, perf_counter) time of the trigger, or None if
    the operator aborts with ESC or the window is closed."""
    pygame.mouse.set_visible(False)
    msg = (f"Waiting for scanner...\n\n"
           f"Start the fMRI sequence now.\n\n"
           f"The run will begin automatically on the scanner trigger ('{trigger_key}').\n\n"
           f"(Press ESC to abort.)")
    show_message(screen, msg, wait_for_key=False, escape_quits=False)
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: return None
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE: return None
            if _event_matches_trigger(ev, trigger_key):
                return datetime.now(), time.perf_counter()
        pygame.time.wait(2)
