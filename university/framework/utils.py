import json
import os
import random
import string
import sys
import time
from decimal import Decimal

from django.conf import settings


def get_config(name, default=None):
    """Config lookup:
    1. Django Settings
    2. Environment Variables
    3. Default
    """
    return getattr(settings, name, os.getenv(name, default))


def get_random_string(length=12):
    letters = f"{string.digits}{string.ascii_letters}"
    chosen = [random.choice(letters) for _ in range(length)]
    return "".join(chosen)


def choices_help_text(choices_cls):
    json_choices = json.dumps(dict(choices_cls.choices), indent=4)
    return f"```json\n{json_choices}\n```"


def format_currency(amount):
    return f"\u20B1{Decimal(amount):,.2f}"


class LoadScreen:
    colors = {
        "HEADER": "\033[95m",
        "UPDATED": "\033[1;33m",
        "CREATED": "\033[1;32m",
        "INVALID": "\033[91m",
    }

    def __init__(self):
        self.last_spin_at = time.time()
        self.speed = 0.1

    def spinning_cursor(self):
        while True:
            for cursor in "|/-\\":
                yield cursor

    def print_statement(self, message, type):
        color = self.colors.get("HEADER")
        if type == "created":
            color = self.colors.get("CREATED")
        elif type == "updated":
            color = self.colors.get("UPDATED")
        elif type == "invalid":
            color = self.colors.get("INVALID")
        else:
            color = self.colors.get("HEADER")

        # print(f"{color} {message}\033[0m")
        print(message)

    def spinner(self, spinner):
        now = time.time()
        diff = now - self.last_spin_at

        if diff >= self.speed:
            self.last_spin_at = now
            sys.stdout.write(next(spinner))
            sys.stdout.flush()
            sys.stdout.write("\b")
