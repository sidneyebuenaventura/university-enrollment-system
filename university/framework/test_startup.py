import os
import subprocess
import sys

import pytest
from django.conf import settings


@pytest.mark.parametrize("module", ["config.wsgi", "config.celery"])
def test_starts_without_settings_module(module):
    # gunicorn and celery import the config package before any settings are set
    env = {k: v for k, v in os.environ.items() if k != "DJANGO_SETTINGS_MODULE"}

    result = subprocess.run(
        [sys.executable, "-c", f"import {module}"],
        cwd=settings.BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
