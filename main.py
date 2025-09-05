#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Blackjack GUI (Tkinter) — Fullscreen + In-GUI Insurance (v2)
- Fullscreen toggle (F11), exit (Esc), resizable canvas with responsive redraws.
- Insurance prompt shown inline in the UI (no popup), with Yes/No buttons and Y/N hotkeys.
- Hotkeys remain active after interacting with insurance.
"""

from __future__ import annotations

import random
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass, field
from typing import List, Tuple
from config import *
import Shoe
import Hand
from GUI import BlackjackApp

# --------------------------- Main -------------------------------------------

def main() -> None:
    try:
        app = BlackjackApp()
        app.mainloop()
    except tk.TclError:
        sys.stderr.write(
            "Tkinter GUI failed to launch. If you're on Linux, install Tk: e.g. `sudo apt-get install python3-tk` "
            "or `sudo dnf install python3-tkinter`.\n"
        )
        raise

if __name__ == "__main__":
    main()
