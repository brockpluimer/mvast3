# -*- coding: utf-8 -*-
"""Shared fixtures. Tests run headless: SDL uses its dummy video driver, so
no window opens and no real display or vsync is involved."""

import os
import sys
import csv
import heapq

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import pytest
import pygame

IMG1 = os.path.join(REPO, "images", "acheck_by.png")
IMG2 = os.path.join(REPO, "images", "acheck_by_.png")
MASTER_HEADER = ['trial_number', 'block_number', 'trial_in_block', 'brightness_factor',
                 'stimulus_duration', 'fixation_duration', 'checkerboard_hz']


@pytest.fixture
def screen():
    pygame.init()
    s = pygame.display.set_mode((160, 120))
    yield s
    pygame.quit()


@pytest.fixture
def boards(screen):
    a = pygame.Surface(screen.get_size()).convert(); a.fill((10, 10, 10))
    b = pygame.Surface(screen.get_size()).convert(); b.fill((200, 200, 200))
    return a, b


def write_master(path, rows, header=MASTER_HEADER):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return str(path)


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


class FakeClock:
    """Virtual time for stimulus.py. perf_counter() returns the virtual time;
    sleep() advances it. `flip()` costs `flip_cost` seconds, or with
    `frame_period` blocks until the next vblank like a vsynced flip. `stall_at`
    maps a flip number (1-based) to an extra delay after that flip. `events`
    are (time, pygame.Event) pairs posted once virtual time reaches them."""
    def __init__(self, frame_period=None, flip_cost=0.0003, stall_at=None, events=(), stall_before=False):
        self.t = 1000.0
        self.frame_period = frame_period
        self.flip_cost = flip_cost
        self.stall_at = dict(stall_at or {})
        # False: stall hits after the flip, before the loop reads the clock
        # (logged time is late). True: stall hits before the flip (the image
        # change itself is late; logged time is accurate).
        self.stall_before = stall_before
        self.events = []
        self.n_flips = 0
        self.flip_times = []
        self.on_flip = None   # optional callback(t) after each flip
        for t_rel, ev in events: self.at(t_rel, ev)

    def perf_counter(self):
        self.t += 1e-5   # reading the clock takes time; lets busy-wait loops progress
        self._post_due()
        return self.t

    def sleep(self, s):
        self.t += max(s, 0.0)
        self._post_due()

    def _post_due(self):
        while self.events and self.events[0][0] <= self.t:
            _, _, ev = heapq.heappop(self.events)
            pygame.event.post(ev)

    def flip(self):
        if self.stall_before: self.t += self.stall_at.get(self.n_flips + 1, 0.0)
        if self.frame_period:
            k = int((self.t - 1000.0) / self.frame_period) + 1
            self.t = 1000.0 + k * self.frame_period   # next vblank
        else:
            self.t += self.flip_cost
        self.n_flips += 1
        self.flip_times.append(self.t)
        if self.on_flip: self.on_flip(self.t)
        if not self.stall_before: self.t += self.stall_at.get(self.n_flips, 0.0)

    def at(self, t_rel, event):
        """Schedule `event` at `t_rel` seconds after the clock's start."""
        heapq.heappush(self.events, (1000.0 + t_rel, id(event), event))


@pytest.fixture
def fake_clock(monkeypatch):
    """Install a FakeClock into stimulus.py; call it with FakeClock kwargs."""
    import stimulus
    def install(**kw):
        clock = FakeClock(**kw)
        class _Time:
            perf_counter = staticmethod(clock.perf_counter)
            sleep = staticmethod(clock.sleep)
        monkeypatch.setattr(stimulus, "time", _Time)
        monkeypatch.setattr(pygame.display, "flip", clock.flip)
        return clock
    return install


def key_event(key, unicode=""):
    return pygame.event.Event(pygame.KEYDOWN, key=key, unicode=unicode, mod=0, scancode=0)
