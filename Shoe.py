from __future__ import annotations
import random
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass, field
from typing import List, Tuple
from config import *

def build_deck() -> List[Card]:
    return [(r, s) for s in SUITS for r in RANKS]


class Shoe:
    def __init__(self, decks: int = DEFAULT_DECKS) -> None:
        self.decks = decks
        self.cards: List[Card] = []
        self.just_reshuffled: bool = False
        self._reshuffle()

    def _reshuffle(self) -> None:
        self.cards = []
        for _ in range(self.decks):
            self.cards.extend(build_deck())
        random.shuffle(self.cards)
        self.just_reshuffled = True

    def draw(self) -> Card:
        if len(self.cards) < RESHUFFLE_PENETRATION:
            self._reshuffle()
        c = self.cards.pop()
        if self.just_reshuffled:
            self.just_reshuffled = False
        return c