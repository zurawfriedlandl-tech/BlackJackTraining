from __future__ import annotations

import random
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass, field
from typing import List, Tuple

# --------------------------- Config -----------------------------------------

DEFAULT_DECKS = 6
STAND_ON_SOFT_17 = True
MIN_BET = 10
START_BANKROLL = 1000
RESHUFFLE_PENETRATION = 30  # reshuffle when shoe has fewer than this many cards

CARD_W, CARD_H = 96, 136
CARD_SPACING = 36

BACKGROUND_COLOR = "#325656"  # felt green
CARD_FACE_COLOR = "#ffffff"
CARD_BACK_COLOR = "#2b6cb0"
TABLE_TEXT = "#f1f5f9"

# P/L chart
PL_CHART_W = 260
PL_CHART_H = 150
PL_CHART_PAD = 8

# --------------------------- Card / Shoe ------------------------------------

SUITS = ["♠", "♥", "♦", "♣"]
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
VALUES = {"A": 11, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10, "J": 10, "Q": 10, "K": 10}

Card = Tuple[str, str]  # (rank, suit)
