# -*- coding: utf-8 -*-
"""stimulus.py helpers: flip summaries, display checks, brightness, image
loading, message/rating/fixation screens, trigger matching, display setup."""


import pygame
import pytest

import stimulus
from config import EXPECTED_DISPLAY_SIZE
from conftest import IMG1, IMG2, key_event


def result(flips, offset, pulses=()):
    return stimulus.FlickerResult(True, list(flips), offset, list(pulses))


# --- summarize_flips --------------------------------------------------------

def test_summarize_exact_values():
    half = 1 / 15
    flips = [10.0 + i * half for i in range(10)]
    s = stimulus.summarize_flips(result(flips, 10.6), 7.5, 9.5)
    assert s['Stim_Onset_s'] == "0.5000"
    assert s['Stim_Offset_s'] == "1.1000"
    assert s['Actual_Stimulus_Duration_s'] == "0.6000"
    assert s['N_Flips'] == 10
    assert s['Median_Interval_ms'] == s['Min_Interval_ms'] == s['Max_Interval_ms'] == "66.67"
    assert s['N_Intervals_Over_1p5x'] == 0 and s['N_Intervals_Under_0p5x'] == 0
    assert list(s) == stimulus.FLIP_STAT_COLUMNS


def test_summarize_counts_and_strict_thresholds():
    half = 1 / 15
    # intervals: just inside 1.5x (not counted), just over, just inside 0.5x (not counted), just under
    ivs = [half, 1.5 * half - 1e-4, 1.5 * half + 1e-4, 0.5 * half + 1e-4, 0.5 * half - 1e-4, half]
    flips = [0.0]
    for iv in ivs: flips.append(flips[-1] + iv)
    s = stimulus.summarize_flips(result(flips, flips[-1] + half), 7.5, 0.0)
    assert s['N_Intervals_Over_1p5x'] == 1
    assert s['N_Intervals_Under_0p5x'] == 1


def test_summarize_single_flip_and_static():
    s = stimulus.summarize_flips(result([5.0], 7.0), 7.5, 5.0)
    assert s['N_Flips'] == 1 and s['Median_Interval_ms'] == "" and s['N_Intervals_Over_1p5x'] == ""
    assert s['Actual_Stimulus_Duration_s'] == "2.0000"
    s0 = stimulus.summarize_flips(result([5.0, 5.5], 7.0), 0, 5.0)
    assert s0['Median_Interval_ms'] == ""   # no nominal half-period for a static image


def test_summarize_no_flips():
    s = stimulus.summarize_flips(stimulus.FlickerResult(False, [], None, []), 7.5, 0.0)
    assert s['Stim_Onset_s'] == "" and s['Stim_Offset_s'] == "" and s['N_Flips'] == 0


# --- display checks ---------------------------------------------------------

def test_display_check_result():
    w, h = EXPECTED_DISPLAY_SIZE
    assert stimulus.display_check_result((w, h)) == f"OK {w}x{h}"
    m = stimulus.display_check_result((1920, 1080))
    assert m.startswith("MISMATCH 1920x1080") and "operator continued" not in m
    assert stimulus.display_check_result((1920, 1080), True).endswith("operator continued")


@pytest.mark.parametrize("hz,rr,expected", [
    (7.5, 60, 4.0), (7.5, 120, 8.0), (8, 60, 3.75), (7.5, 144, 9.6),
    (0, 60, None), (-1, 60, None), (7.5, None, None), (7.5, 0, None),
])
def test_frames_per_half_cycle(hz, rr, expected):
    got = stimulus.frames_per_half_cycle(hz, rr)
    assert got == (pytest.approx(expected) if expected is not None else None)


def test_describe_display():
    d = {'index': 1, 'name': "EIZO RX", 'size': (1600, 1200), 'refresh_hz': 60, 'bounds': None}
    assert stimulus.describe_display(d) == "Display 2: EIZO RX (1600×1200 @ 60 Hz)"
    d.update(name="", refresh_hz=None)
    assert stimulus.describe_display(d) == "Display 2 (1600×1200)"


def test_list_displays_under_dummy_driver():
    pygame.display.quit()
    ds = stimulus.list_displays()
    assert len(ds) >= 1 and ds[0]['index'] == 0 and len(ds[0]['size']) == 2
    assert not pygame.display.get_init()        # left uninitialized as found


def test_open_display_dummy_and_bad_index():
    try:
        screen, info = stimulus.open_display(0)
        assert screen.get_size() == info['size']
        assert info['vsync'] is False and info['frame_period'] is None   # dummy flips don't block
        assert set(info) >= {'display_index', 'size', 'refresh_hz_os', 'vsync', 'frame_period', 'refresh_hz_measured'}
    finally:
        pygame.quit()
    with pytest.raises(RuntimeError, match="not connected"):
        try: stimulus.open_display(7)
        finally: pygame.quit()


@pytest.mark.parametrize("fp", [1 / 60, 1 / 120, 1 / 144])
def test_measure_frame_period_detects_blocking_flip(screen, fake_clock, fp):
    fake_clock(frame_period=fp)
    assert stimulus.measure_frame_period(screen, n_flips=12) == pytest.approx(fp, rel=1e-3)


def test_measure_frame_period_none_without_vsync(screen, fake_clock):
    fake_clock(flip_cost=0.0005)
    assert stimulus.measure_frame_period(screen, n_flips=12) is None


# --- brightness ---------------------------------------------------------------

def test_adjust_surface_brightness(screen):
    white = pygame.Surface((4, 4)).convert(); white.fill((255, 255, 255))
    assert stimulus.adjust_surface_brightness(white, 1.0) is white
    assert stimulus.adjust_surface_brightness(white, 0.0).get_at((0, 0))[:3] == (0, 0, 0)
    for f in (0.1, 0.2, 0.4, 0.6, 0.8):
        v = stimulus.adjust_surface_brightness(white, f).get_at((0, 0))[0]
        assert abs(v - 255 * f) <= 1.5, (f, v)
    assert white.get_at((0, 0))[:3] == (255, 255, 255)   # original untouched


def test_brightness_cache(screen, boards):
    cache = stimulus.build_brightness_cache(*boards, [0.6, 0.1, 0.6, 1.0, 0.1])
    assert sorted(cache) == [0.1, 0.6, 1.0]
    assert cache[1.0][0] is boards[0]
    assert cache[0.1][1].get_at((0, 0))[0] < boards[1].get_at((0, 0))[0]


# --- image loading -------------------------------------------------------------

def test_load_images_ok(screen):
    b1, b2 = stimulus.load_checkerboard_images(160, 120, IMG1, IMG2)
    assert b1.get_size() == b2.get_size() == (160, 120)


def test_load_images_missing_raises(screen, tmp_path):
    with pytest.raises(RuntimeError, match="not found"):
        stimulus.load_checkerboard_images(160, 120, str(tmp_path / "nope.png"), IMG2)


def test_load_images_corrupt_raises(screen, tmp_path):
    bad = tmp_path / "bad.png"; bad.write_bytes(b"not an image")
    with pytest.raises(RuntimeError):
        stimulus.load_checkerboard_images(160, 120, IMG1, str(bad))


# --- screens --------------------------------------------------------------------

def test_show_message_any_key(screen):
    pygame.event.post(key_event(pygame.K_a, "a"))
    assert stimulus.show_message(screen, "hello") is True


def test_show_message_escape_and_quit(screen):
    pygame.event.post(key_event(pygame.K_ESCAPE))
    assert stimulus.show_message(screen, "x") is False
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    assert stimulus.show_message(screen, "x") is False


def test_show_message_escape_allowed_when_not_quitting(screen):
    pygame.event.post(key_event(pygame.K_ESCAPE))
    assert stimulus.show_message(screen, "x", escape_quits=False) is True


def test_show_message_continue_keys_ignore_trigger(screen):
    for _ in range(5): pygame.event.post(key_event(pygame.K_5, "5"))
    pygame.event.post(key_event(pygame.K_SPACE, " "))
    assert stimulus.show_message(screen, "intro", continue_keys=(pygame.K_SPACE,)) is True
    assert not pygame.event.peek(pygame.KEYDOWN)


def test_show_message_continue_keys_still_honours_escape(screen):
    pygame.event.post(key_event(pygame.K_5, "5"))
    pygame.event.post(key_event(pygame.K_ESCAPE))
    assert stimulus.show_message(screen, "intro", continue_keys=(pygame.K_SPACE,)) is False


def test_show_message_no_wait_and_no_screen(screen):
    assert stimulus.show_message(screen, "line 1\n\nline 3", wait_for_key=False) is True
    assert stimulus.show_message(None, "x") is True


def test_show_fixation(screen):
    assert stimulus.show_fixation(screen, 0.05) is True
    pygame.event.post(key_event(pygame.K_ESCAPE))
    assert stimulus.show_fixation(screen, 5.0) is False
    pygame.event.post(key_event(pygame.K_ESCAPE))
    assert stimulus.show_fixation(screen, 0.05, escape_quits=False) is True


@pytest.mark.parametrize("ev", [pygame.event.Event(pygame.QUIT), key_event(pygame.K_ESCAPE)])
def test_rating_abort_returns_none(screen, ev):
    pygame.event.post(ev)
    assert stimulus.get_rating_with_click(screen, "", "brightness") is None


def test_rating_scale_mouse(screen, monkeypatch):
    scale = stimulus.RatingScale(screen, "", scale_type="unpleasantness")
    pos = [(0, 0)]
    monkeypatch.setattr(pygame.mouse, "get_pos", lambda: pos[0])
    y = scale.scale_y
    down = lambda: pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos[0])
    move = lambda: pygame.event.Event(pygame.MOUSEMOTION, pos=pos[0], rel=(0, 0), buttons=(1, 0, 0))
    pos[0] = (scale.scale_x + scale.scale_width * 0.37, y); scale.handle_event(down())
    assert scale.value == 37
    pos[0] = (scale.scale_x - 500, y); scale.handle_event(move())
    assert scale.value == 0                                   # clamped low while dragging
    pos[0] = (scale.scale_x + scale.scale_width + 500, y); scale.handle_event(move())
    assert scale.value == 100                                 # clamped high
    scale.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=pos[0]))
    pos[0] = (scale.scale_x, y); scale.handle_event(move())
    assert scale.value == 100                                 # no drag after release
    pos[0] = scale.confirm_button_rect.center
    assert scale.handle_event(down()) == "confirmed"
    scale.draw()                                              # renders without error


def test_rating_scale_labels(screen):
    for kind, title in (("unpleasantness", "unpleasantness"), ("brightness", "brightness")):
        s = stimulus.RatingScale(screen, "", scale_type=kind)
        assert title in s.title


# --- trigger matching -------------------------------------------------------------

@pytest.mark.parametrize("ev,key,expected", [
    (key_event(pygame.K_5, "5"), "5", True),
    (key_event(pygame.K_KP5, "5"), "5", True),     # keypad 5 produces '5'
    (key_event(pygame.K_t, "T"), "t", True),       # case-insensitive
    (key_event(pygame.K_t, ""), "t", True),        # matched by key name when no unicode
    (key_event(pygame.K_6, "6"), "5", False),
    (pygame.event.Event(pygame.KEYUP, key=pygame.K_5, unicode="5", mod=0, scancode=0), "5", False),
])
def test_event_matches_trigger(ev, key, expected):
    assert stimulus._event_matches_trigger(ev, key) is expected


def test_wait_for_scanner_trigger(screen):
    pygame.event.post(key_event(pygame.K_a, "a"))
    pygame.event.post(key_event(pygame.K_5, "5"))
    got = stimulus.wait_for_scanner_trigger(screen, "5")
    assert got is not None and len(got) == 2
    pygame.event.post(key_event(pygame.K_ESCAPE))
    assert stimulus.wait_for_scanner_trigger(screen, "5") is None
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    assert stimulus.wait_for_scanner_trigger(screen, "5") is None


def test_fixation_overlay_centered(screen):
    surf, rect = stimulus.make_fixation_overlay(screen)
    assert rect.center == (screen.get_width() // 2, screen.get_height() // 2)


# --- approved rating scales (must match v1 exactly) ---------------------------------

def test_rating_scales_match_approved_v1(screen):
    """Prompts, anchors, range and start value were approved by Steve in v1.
    Any change here must be a deliberate protocol decision."""
    u = stimulus.RatingScale(screen, "", scale_type="unpleasantness")
    b = stimulus.RatingScale(screen, "", scale_type="brightness")
    assert u.title == "Please rate the unpleasantness of the image you just viewed."
    assert b.title == "Please rate the brightness of the image you just viewed."
    assert u.get_scale_labels() == ("Not\nUnpleasant", "Most Unpleasant\nImage\nImaginable")
    assert b.get_scale_labels() == ("No Image\nVisible", "Brightest Image\nImaginable")
    for s in (u, b):
        assert (s.min_val, s.max_val, s.value) == (0, 100, 0)
        assert s.confirm_button_text == "Confirm"


def test_rating_scale_code_identical_to_v1():
    """The RatingScale class is byte-for-byte the v1 code (ignoring blank lines)."""
    import subprocess, inspect
    from conftest import REPO
    try:
        v1 = subprocess.run(["git", "-C", REPO, "show", "ee205e4:stimulus.py"],
                            capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("v1 source not available from git")
    v1_cls = v1[v1.index("class RatingScale"):v1.index("# --- Pygame Helper Functions")]
    now = inspect.getsource(stimulus.RatingScale)
    strip = lambda t: [l.rstrip() for l in t.splitlines() if l.strip()]
    assert strip(now) == strip(v1_cls)
