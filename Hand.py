from __future__ import annotations
import random
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass, field
from typing import List, Tuple
from config import *

# --------------------------- Hand logic -------------------------------------

@dataclass
class Hand:
    cards: List[Card] = field(default_factory=list)

    def add(self, c: Card) -> None:
        self.cards.append(c)

    def clear(self) -> None:
        self.cards.clear()

    def is_blackjack(self) -> bool:
        return len(self.cards) == 2 and self.value() == 21

    def is_pair(self) -> bool:
        return len(self.cards) == 2 and self.cards[0][0] == self.cards[1][0]

    def value(self) -> int:
        total = 0
        aces = 0
        for r, _ in self.cards:
            total += VALUES[r]
            if r == "A":
                aces += 1
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total

    def value_hard(self) -> int:
        total = 0
        for r, _ in self.cards:
            total += 1 if r == "A" else VALUES[r]
        return total

    def is_soft(self) -> bool:
        return any(r == "A" for r, _ in self.cards) and self.value() != self.value_hard()

    def is_bust(self) -> bool:
        return self.value() > 21


@dataclass
class PlayerHand:
    hand: Hand
    bet: int
    doubled: bool = False
    split_aces: bool = False  # split Aces receive one card only

    def can_double(self) -> bool:
        return (len(self.hand.cards) == 2) and (not self.doubled) and (not self.split_aces)
