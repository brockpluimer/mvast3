# -*- coding: utf-8 -*-
"""M-VAST 3 - pygame stimulus presentation, rating scale, and helpers."""

import os
import sys
import time
import numpy as np
import pygame
from datetime import datetime
from tkinter import messagebox

from config import (
    WHITE, BLACK, GREEN, DARK_GREEN, GRAY_COLOR,
    PYGAME_REFERENCE_SCREEN_HEIGHT,
)

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
    the operator aborts with ESC."""
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

def run_tonic_stimulus(screen, board1, board2, duration, hz, brightness_factor, escape_quits=True):
    """Continuous constant-brightness flicker for `duration` seconds with a
    central fixation cross. Mirrors run_alternating_stimulus timing but adds
    the fixation cross and is intended to run for the full ~6-minute run.
    Returns True if it ran to completion, False if aborted."""
    pygame.mouse.set_visible(False)

    pg_sf = max(0.5, min(3.0, screen.get_height() / PYGAME_REFERENCE_SCREEN_HEIGHT))
    cross_font_size = int(72 * pg_sf)
    try: cross_font = pygame.font.Font(None, cross_font_size)
    except: cross_font = pygame.font.SysFont("arial", cross_font_size)
    cross_surf = cross_font.render('+', True, WHITE)
    cross_rect = cross_surf.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))

    b_b1 = adjust_surface_brightness(board1, brightness_factor)
    b_b2 = adjust_surface_brightness(board2, brightness_factor)

    start_t = time.perf_counter()
    end_t = start_t + duration

    # Static (no flicker) case: draw once, then hold.
    if hz <= 0:
        screen.fill(BLACK); screen.blit(b_b1, (0, 0)); screen.blit(cross_surf, cross_rect)
        pygame.display.flip()
        while time.perf_counter() < end_t:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT: return False
                if escape_quits and ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE: return False
            time.sleep(0.01)
        return True

    frame_dur = 1.0 / hz / 2.0
    curr_b1, last_flip_t = True, start_t
    while time.perf_counter() < end_t:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: return False
            if escape_quits and ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE: return False

        now_t = time.perf_counter()
        if now_t >= last_flip_t + frame_dur:
            screen.fill(BLACK)
            screen.blit(b_b1 if curr_b1 else b_b2, (0, 0))
            screen.blit(cross_surf, cross_rect)
            pygame.display.flip()
            curr_b1 = not curr_b1
            last_flip_t += frame_dur

        time_to_next = (last_flip_t + frame_dur) - now_t
        if time_to_next > 0.002: time.sleep(max(0.001, time_to_next * 0.5))
    return True

