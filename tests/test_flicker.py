# -*- coding: utf-8 -*-
"""run_flicker driven by a virtual clock: exact grid timing, stall handling,
board parity, aborts, trigger capture, and randomized stress runs."""

import gc
import math
import random
import statistics

import pygame
import pytest

import stimulus
from conftest import key_event

DARK, LIGHT = 10, 200   # red channel of the two test boards
HALF_MS = 1000.0 / 7.5 / 2.0


def run(screen, boards, clock, duration, hz, frame_period=None, **kw):
    """Run the flicker, recording which board each flip put on screen."""
    shown = []
    clock.on_flip = lambda t: shown.append((t, screen.get_at((0, 0))[0]))
    result = stimulus.run_flicker(screen, *boards, duration, hz, frame_period=frame_period, **kw)
    return result, shown


def intervals_ms(flips):
    return [(b - a) * 1000.0 for a, b in zip(flips, flips[1:])]


def assert_parity(shown, flips, hz, skip=(), frame_period=None, anchor=None):
    """Each flip put up the board belonging to the grid slot it actually
    landed in (screen truth: `shown` holds the real flip times recorded by
    the fake display, which can differ from the loop's logged timestamps
    when a stall falls between flip() and the timestamp). With vsync a change
    lands on the vblank nearest the slot boundary, up to half a frame early."""
    assert len(shown) == len(flips)
    half = 1.0 / hz / 2.0
    onset = shown[0][0] if anchor is None else anchor
    tol = (frame_period / 2.0 if frame_period else 0.0) + 1e-6
    for n, (t, color) in enumerate(shown, start=1):
        if n in skip: continue   # this flip was delayed by a stall inside flip()
        slot = math.floor((t - onset + tol) / half)
        assert color == (DARK if slot % 2 == 0 else LIGHT), f"wrong board at +{(t - onset) * 1000:.1f} ms (slot {slot})"


def screen_intervals_ms(shown):
    """Intervals between real (on-screen) image changes."""
    return [(b[0] - a[0]) * 1000.0 for a, b in zip(shown, shown[1:])]


# --- Nominal timing ---------------------------------------------------------

def test_no_vsync_exact_grid(screen, boards, fake_clock):
    clock = fake_clock()
    r, shown = run(screen, boards, clock, 3.0, 7.5)
    assert r.completed
    assert len(r.flips) == 45                      # slots 0..44 start before 3.0 s
    assert all(abs(i - 66.667) < 1.0 for i in intervals_ms(r.flips))
    assert r.offset - r.flips[0] == pytest.approx(3.0, abs=0.006)
    assert_parity(shown, r.flips, 7.5)


def test_vsync_flips_land_on_vblanks(screen, boards, fake_clock):
    fp = 1 / 60
    clock = fake_clock(frame_period=fp)
    r, shown = run(screen, boards, clock, 2.0, 7.5, frame_period=fp)
    assert r.completed
    for a, b in zip(r.flips, r.flips[1:]):
        assert (b - a) / fp == pytest.approx(4.0, abs=1e-6)   # exactly 4 frames per half-cycle
    assert_parity(shown, r.flips, 7.5, frame_period=fp)


def test_vsync_non_integer_frames_alternate(screen, boards, fake_clock):
    """8 Hz at 60 Hz is 3.75 frames per half-cycle: intervals must be whole
    frames (3 or 4), never sub-frame, with the right average."""
    fp = 1 / 60
    clock = fake_clock(frame_period=fp)
    r, _ = run(screen, boards, clock, 3.0, 8.0, frame_period=fp)
    frames = [(b - a) / fp for a, b in zip(r.flips, r.flips[1:])]
    assert all(abs(f - round(f)) < 1e-6 and round(f) in (3, 4) for f in frames)
    assert statistics.mean(frames) == pytest.approx(3.75, abs=0.1)


def test_first_frame_is_onset_and_duration_matches(screen, boards, fake_clock):
    clock = fake_clock()
    r, shown = run(screen, boards, clock, 1.0, 7.5)
    assert shown[0][1] == DARK                     # board 1 shown at onset, not after a half-period
    s = stimulus.summarize_flips(r, 7.5, r.flips[0])
    assert float(s['Stim_Onset_s']) == 0.0
    assert float(s['Actual_Stimulus_Duration_s']) == pytest.approx(1.0, abs=0.006)


def test_duration_shorter_than_half_period(screen, boards, fake_clock):
    clock = fake_clock()
    r, _ = run(screen, boards, clock, 0.3, 1.0)    # half-period 0.5 s > duration
    assert r.completed and len(r.flips) == 1


def test_static_image_hz_zero(screen, boards, fake_clock):
    clock = fake_clock()
    r, shown = run(screen, boards, clock, 2.0, 0)
    assert r.completed and len(r.flips) == 1 and shown[0][1] == DARK
    assert r.offset - r.flips[0] == pytest.approx(2.0, abs=0.006)
    assert stimulus.summarize_flips(r, 0, r.flips[0])['Median_Interval_ms'] == ""


# --- Stalls -----------------------------------------------------------------

@pytest.mark.parametrize("stall_before", [True, False], ids=["stall-before-flip", "stall-after-flip"])
@pytest.mark.parametrize("vsync", [False, True], ids=["no-vsync", "vsync"])
@pytest.mark.parametrize("stall_ms", [5, 20, 40, 70, 130, 140, 200, 500, 1000])
def test_stall_never_causes_catch_up_flips(screen, boards, fake_clock, vsync, stall_ms, stall_before):
    fp = 1 / 60 if vsync else None
    clock = fake_clock(frame_period=fp, stall_at={10: stall_ms / 1000.0}, stall_before=stall_before)
    r, shown = run(screen, boards, clock, 4.0, 7.5, frame_period=fp)
    assert r.completed
    assert_parity(shown, r.flips, 7.5, skip={10} if stall_before else (), frame_period=fp)
    on_screen = screen_intervals_ms(shown)
    assert min(on_screen) >= 0.5 * HALF_MS - 1e-6, on_screen        # nothing flashes briefly on screen
    if vsync:
        assert min(on_screen) >= fp * 1000 - 1e-6            # never shorter than one frame
    if stall_ms >= 40:
        assert max(on_screen) > 1.5 * HALF_MS                 # the stall is one long interval
    s = stimulus.summarize_flips(r, 7.5, r.flips[0])
    if stall_before:
        # Logged times are accurate, so the logged stats match the screen.
        assert s['N_Intervals_Under_0p5x'] == 0, intervals_ms(r.flips)
        if stall_ms >= 40: assert s['N_Intervals_Over_1p5x'] >= 1
    else:
        # A stall between flip() and the timestamp makes that timestamp late:
        # it can only show up as a long logged interval followed by a short one.
        logged = intervals_ms(r.flips)
        for i, iv in enumerate(logged):
            if iv < 0.5 * HALF_MS - 1e-6: assert i > 0 and logged[i - 1] > 1.5 * HALF_MS, logged
    assert r.offset - r.flips[0] == pytest.approx(4.0, abs=0.02)   # schedule doesn't drift


def test_v1_loop_would_have_produced_catch_up(screen, boards, fake_clock):
    """Documents the bug the new loop fixes: chaining off the previous flip
    (v1 behaviour) yields sub-0.5x intervals after a stall."""
    half, t, last, flips = 1 / 15, 0.0, 0.0, []
    for _ in range(30):
        t = max(t, last + half)
        flips.append(t)
        if len(flips) == 10: t += 0.130
        last += half
    assert min(intervals_ms(flips)) < 0.5 * half * 1000


# --- Aborts, events, triggers ----------------------------------------------

def test_escape_mid_run_stops_promptly(screen, boards, fake_clock):
    clock = fake_clock()
    clock.at(1.234, key_event(pygame.K_ESCAPE))
    r, _ = run(screen, boards, clock, 5.0, 7.5)
    assert not r.completed
    assert r.offset - 1000.0 == pytest.approx(1.234, abs=0.01)
    assert all(f < 1000.0 + 1.234 + 0.01 for f in r.flips)


def test_escape_ignored_when_disabled(screen, boards, fake_clock):
    clock = fake_clock()
    clock.at(0.5, key_event(pygame.K_ESCAPE))
    r, _ = run(screen, boards, clock, 1.0, 7.5, escape_quits=False)
    assert r.completed


def test_window_close_stops_run(screen, boards, fake_clock):
    clock = fake_clock()
    clock.at(0.4, pygame.event.Event(pygame.QUIT))
    r, _ = run(screen, boards, clock, 2.0, 7.5)
    assert not r.completed


def test_escape_during_static_image(screen, boards, fake_clock):
    clock = fake_clock()
    clock.at(0.7, key_event(pygame.K_ESCAPE))
    r, _ = run(screen, boards, clock, 3.0, 0)
    assert not r.completed and r.offset - 1000.0 == pytest.approx(0.7, abs=0.01)


def test_trigger_pulses_recorded_and_other_keys_ignored(screen, boards, fake_clock):
    clock = fake_clock()
    for t in (0.5, 1.0, 1.5): clock.at(t, key_event(pygame.K_5, "5"))
    clock.at(0.75, key_event(pygame.K_a, "a"))
    r, _ = run(screen, boards, clock, 2.0, 7.5, trigger_key="5")
    assert r.completed
    assert [round(p - 1000.0, 2) for p in r.pulses] == [0.5, 1.0, 1.5]


def test_no_trigger_recording_without_trigger_key(screen, boards, fake_clock):
    clock = fake_clock()
    clock.at(0.5, key_event(pygame.K_5, "5"))
    r, _ = run(screen, boards, clock, 1.0, 7.5)
    assert r.pulses == []


def test_focus_loss_is_counted(screen, boards, fake_clock):
    stimulus.take_focus_events()
    clock = fake_clock()
    clock.at(0.3, pygame.event.Event(pygame.WINDOWFOCUSLOST))
    clock.at(0.6, pygame.event.Event(pygame.WINDOWMINIMIZED))
    run(screen, boards, clock, 1.0, 7.5)
    assert stimulus.take_focus_events() == 2
    assert stimulus.take_focus_events() == 0     # reset after reading


def test_overlay_drawn_on_every_flip(screen, boards, fake_clock):
    cross = pygame.Surface((10, 10)).convert(); cross.fill((255, 0, 0))
    rect = cross.get_rect(center=(80, 60))
    seen = []
    clock = fake_clock()
    clock.on_flip = lambda t: seen.append(tuple(screen.get_at(rect.center))[:3])
    stimulus.run_flicker(screen, *boards, 1.0, 7.5, overlay=(cross, rect))
    assert seen and all(c == (255, 0, 0) for c in seen)


@pytest.mark.parametrize("initially_enabled", [True, False])
def test_gc_state_restored(screen, boards, fake_clock, initially_enabled):
    (gc.enable if initially_enabled else gc.disable)()
    try:
        clock = fake_clock()
        clock.at(0.2, key_event(pygame.K_ESCAPE))   # also via the abort path
        run(screen, boards, clock, 1.0, 7.5)
        assert gc.isenabled() == initially_enabled
    finally:
        gc.enable()


# --- Randomized stress ------------------------------------------------------

def test_randomized_stress(screen, boards, fake_clock):
    """400 seeded runs (MVAST_STRESS_CASES / MVAST_STRESS_SEED to change) with random rate, duration, vsync, flip cost and stalls
    (before or after the flip). The invariants must always hold."""
    import os
    rng = random.Random(int(os.environ.get("MVAST_STRESS_SEED", 1234)))
    for case in range(int(os.environ.get("MVAST_STRESS_CASES", 400))):
        hz = rng.choice([1, 2, 3.75, 5, 7.5, 10, 12, 15, 20, 30])
        duration = rng.uniform(0.2, 6.0)
        fp = rng.choice([None, 1 / 60, 1 / 120, 1 / 144])
        if fp and 1 / hz / 2 < fp: fp = None        # half-period shorter than a frame isn't displayable
        stalls = {rng.randint(1, 40): rng.uniform(0.0, 0.4) for _ in range(rng.randint(0, 4))}
        stall_before = rng.random() < 0.5
        flip_cost = rng.uniform(0.0001, 0.003)
        clock = fake_clock(frame_period=fp, stall_at=stalls, flip_cost=flip_cost, stall_before=stall_before)
        r, shown = run(screen, boards, clock, duration, hz, frame_period=fp)
        half_ms = 1000.0 / hz / 2.0
        ctx = f"case {case}: hz={hz} dur={duration:.2f} fp={fp} stalls={stalls} before={stall_before}"
        assert r.completed, ctx
        assert shown[0][1] == DARK, ctx
        # A stall between the onset flip and its timestamp shifts the loop's
        # whole grid (it can only know the logged onset), so anchor there.
        anchor = r.flips[0] if (not stall_before and 1 in stalls) else None
        skip = set(stalls) if stall_before else ({1} if anchor is not None else set())
        assert_parity(shown, r.flips, hz, skip=skip, frame_period=fp, anchor=anchor)
        on_screen = screen_intervals_ms(shown)
        assert not on_screen or min(on_screen) >= 0.5 * half_ms - 1e-6, ctx + f" screen={on_screen}"
        if stall_before:
            s = stimulus.summarize_flips(r, hz, r.flips[0])
            assert s['N_Intervals_Under_0p5x'] in ("", 0), ctx + f" logged={intervals_ms(r.flips)}"
        stalled_inside = set(stalls) if stall_before else set()   # committed before the stall hit
        # a flip decided before the end may finish up to one flip's drawing time later
        start = shown[0][0] if anchor is None else anchor
        assert all(t < start + duration + flip_cost + 1e-4 for n, (t, _) in enumerate(shown, 1) if n not in stalled_inside), ctx
        assert duration - 1e-9 <= r.offset - r.flips[0] <= duration + 0.45, ctx
