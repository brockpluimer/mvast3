# -*- coding: utf-8 -*-
"""config.py: the default data folder must not depend on where the app is
launched from, and resource paths must resolve to files in the app folder."""

import os
import sys
import subprocess

import config
from conftest import REPO


def app_base_from(cwd):
    out = subprocess.run([sys.executable, "-c", "import config; print(config.APP_BASE_PATH)"],
                         cwd=cwd, env={**os.environ, "PYTHONPATH": REPO}, capture_output=True, text=True, check=True)
    return out.stdout.strip().splitlines()[-1]


def test_app_base_path_independent_of_cwd(tmp_path):
    real = os.path.realpath
    assert real(app_base_from(str(tmp_path))) == real(app_base_from(REPO)) == real(REPO)
    assert config.DEFAULT_LOG_DIR_BASE.startswith(config.APP_BASE_PATH)


def test_resource_path_is_quiet_and_resolves(capsys):
    p = config.resource_path(config.CANONICAL_IMAGE1)
    assert os.path.exists(p) and os.path.exists(config.resource_path(config.CANONICAL_IMAGE2))
    assert os.path.exists(config.resource_path(config.HELP_FILE_NAME))
    assert capsys.readouterr().out == ""


def test_settings_file_is_gitignored():
    with open(os.path.join(REPO, ".gitignore")) as f:
        assert "mvast3_settings.json" in f.read()


def test_run_configs_have_display_fields():
    for c in (config.RunConfig(), config.TonicRunConfig()):
        assert c.display_index == 0 and c.display_mismatch_accepted is False
