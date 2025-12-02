from __future__ import annotations
import random
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass, field
from typing import List, Tuple
from Shoe import Shoe
from Hand import Hand, PlayerHand
from config import *

# --------------------------- GUI Application --------------------------------

class BlackjackApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Blackjack — Fullscreen + In-GUI Insurance (v2)")
        self.configure(bg=BACKGROUND_COLOR)
        

        # Window is resizable; start with a comfortable size
        self.geometry("1280x800")
        self.minsize(1024, 700)
        self.resizable(True, True)

        # Main Menu vars
        self.mode: str | None = None
        self.in_menu: bool = False

        # Fullscreen state
        self._is_fullscreen = False
        self.bind("<F11>", lambda e: self.toggle_fullscreen())
        self.bind("<Escape>", lambda e: self.exit_fullscreen())

        self.shoe = Shoe(decks=DEFAULT_DECKS)
        self.bankroll = START_BANKROLL
        self.min_bet = MIN_BET
        self.stand_on_soft_17 = STAND_ON_SOFT_17

        # Game round state
        self.dealer = Hand()
        self.player_hands: List[PlayerHand] = []
        self.active_hand_index: int = 0
        self.in_round: bool = False
        self.animating: bool = False
        self.insurance_bet: int = 0
        self.dealer_blackjack: bool = False
        self.discard_count: int = 0  # number of cards in discard pile
        self.round_complete: bool = False

        # Track last "hide dealer hole" state to redraw on window resizes
        self._last_hide_dealer_hole: bool = False

        # Insurance prompt state
        self.insurance_prompt_visible: bool = False
        self.insurance_max_allowed: int = 0
        self._insurance_frame: tk.Frame | None = None

        # Speed control (ms)
        self.deal_delay_var = tk.IntVar(value=300)

        # Decks control
        self.decks_var = tk.IntVar(value=self.shoe.decks)

        # P/L series
        self.pl_points: List[int] = [self.bankroll]

        # Hi-Lo running & true count
        self.running_count: int = 0
        self.true_count: float = 0.0

        # Hint toggle
        self.show_hint = tk.BooleanVar(value=False)
        self.advice_text = tk.StringVar(value="")

        # Drill mode filters
        self.drill_include_hard = tk.BooleanVar(value=True)
        self.drill_include_soft = tk.BooleanVar(value=True)
        self.drill_include_pairs = tk.BooleanVar(value=True)

        self.cc_visible: bool = True
        # Decision stats
        self.stats = {
            'total': 0, 'correct': 0,
            'HIT': {'t': 0, 'c': 0},
            'STAND': {'t': 0, 'c': 0},
            'DOUBLE': {'t': 0, 'c': 0},
            'SPLIT': {'t': 0, 'c': 0},
        }
        self.stats_total_var = tk.StringVar(value="Total: 0")
        self.stats_correct_var = tk.StringVar(value="Correct: 0 (0.0%)")
        self.stats_hit_var = tk.StringVar(value="Hit: 0/0")
        self.stats_stand_var = tk.StringVar(value="Stand: 0/0")
        self.stats_double_var = tk.StringVar(value="Double: 0/0")
        self.stats_split_var = tk.StringVar(value="Split: 0/0")

        self._build_ui()
        self._enter_main_menu()
        #self._update_status("Welcome! Set your bet and click Deal.  Press F11 to toggle fullscreen.")

    # ----------------------- Fullscreen Helpers ------------------------------

    def toggle_fullscreen(self) -> None:
        self._is_fullscreen = not self._is_fullscreen
        self.attributes('-fullscreen', self._is_fullscreen)

    def exit_fullscreen(self) -> None:
        if self._is_fullscreen:
            self._is_fullscreen = False
            self.attributes('-fullscreen', False)


    # ----------------------- Side Panel Layout Modes -------------------------

    def _set_trainer_side_panel_layout(self) -> None:
        """Standard mode: show everything except drill filters."""
        widgets = [
            self.hud_panel,
            self.outcome_lbl,
            self.hint_panel,
            self.stats_panel,
            self.drill_panel,
            self.info_panel,
            self.chart_frame,
        ]
        # Clear existing packing
        for w in widgets:
            try:
                w.pack_forget()
            except Exception:
                pass

        # Trainer layout: HUD → outcome → hint → stats → info → chart
        self.hud_panel.pack(fill=tk.X, pady=(0,8))
        self.outcome_lbl.pack(fill=tk.X, pady=(0,8))
        self.hint_panel.pack(fill=tk.X, pady=(0,8))
        self.stats_panel.pack(fill=tk.X, pady=(0,8))
        # drill_panel intentionally hidden in trainer mode
        self.info_panel.pack(fill=tk.X)
        self.chart_frame.pack(fill=tk.X, pady=(8,0))

    def _set_drill_side_panel_layout(self) -> None:
        """drill mode: only show hint + drill filters."""
        widgets = [
            self.hud_panel,
            self.outcome_lbl,
            self.hint_panel,
            self.stats_panel,
            self.drill_panel,
            self.info_panel,
            self.chart_frame,
        ]
        for w in widgets:
            try:
                w.pack_forget()
            except Exception:
                pass

        # drill layout: only hint and drill filters
        self.hint_panel.pack(fill=tk.X, pady=(0,8))
        self.stats_panel.pack(fill=tk.X, pady=(0,8))
        self.drill_panel.pack(fill=tk.X, pady=(0,8))



    # ----------------------- Utilities --------------------------------------

    def _enable_actions(self, hit=True, stand=True, double=False, split=False) -> None:
        # When insurance prompt is up, only allow responding to insurance.
        if self.insurance_prompt_visible:
            hit = stand = double = split = False
        self.hit_btn.config(state=("normal" if hit else "disabled"))
        self.stand_btn.config(state=("normal" if stand else "disabled"))
        self.double_btn.config(state=("normal" if double else "disabled"))
        self.split_btn.config(state=("normal" if split else "disabled"))

    def _disable_actions(self) -> None:
        self._enable_actions(False, False, False, False)

    def _bind_hotkeys(self) -> None:
        # Gameplay
        self.bind_all('<h>', lambda e: self.on_hit())
        self.bind_all('<H>', lambda e: self.on_hit())
        self.bind_all('<s>', lambda e: self.on_stand())
        self.bind_all('<S>', lambda e: self.on_stand())
        self.bind_all('<d>', lambda e: self.on_double())
        self.bind_all('<D>', lambda e: self.on_double())
        self.bind_all('<p>', lambda e: self.on_split())
        self.bind_all('<P>', lambda e: self.on_split())
        self.bind_all('<space>', self._on_deal_hotkey)
        self.bind_all('<Return>', self._on_deal_hotkey)
        self.bind_all('<r>', lambda e: self.on_shuffle())
        self.bind_all('<R>', lambda e: self.on_shuffle())

        # Insurance hotkeys
        self.bind_all('<y>', lambda e: self._on_insurance_yes())
        self.bind_all('<Y>', lambda e: self._on_insurance_yes())
        self.bind_all('<n>', lambda e: self._on_insurance_no())
        self.bind_all('<N>', lambda e: self._on_insurance_no())

        for cls in ("Button", "TButton", "Checkbutton", "TCheckbutton"):
            try:
                self.unbind_class(cls, "<space>")
                self.unbind_class(cls, "<Return>")
            except Exception:
                pass

    def _on_deal_hotkey(self, event) -> str | None:
        if getattr(self, "in_menu", False):
            return "break"
       
        self.on_deal()
        return "break"

    def _delay(self) -> int:
        return max(0, int(self.deal_delay_var.get()))

    def _on_speed_change(self, _val: str) -> None:
        ms = int(float(self.speed_slider.get()))
        self.deal_delay_var.set(ms)
        self.speed_val_lbl.config(text=f"{ms} ms")

    def _toggle_hint(self) -> None:
        if self.show_hint.get():
            self._update_hint()
        else:
            self.advice_text.set("")
            self._highlight_buttons(None)

    def toggle_card_count_menu(self) -> None:
        """Show/hide the Card Counting panel. Also bound to 'c'/'C' keys."""
        try:
            self.cc_visible = not getattr(self, "cc_visible", True)
            if self.cc_visible:
                # Repack the content area
                if hasattr(self, "cc_content"):
                    self.cc_content.pack(fill=tk.X)
                if hasattr(self, "cc_toggle_btn"):
                    self.cc_toggle_btn.config(text="Hide")
                self._update_status("Card counting panel shown.")
            else:
                if hasattr(self, "cc_content"):
                    self.cc_content.pack_forget()
                if hasattr(self, "cc_toggle_btn"):
                    self.cc_toggle_btn.config(text="Show")
                self._update_status("Card counting panel hidden.")
        except Exception:
            # Fail-safe: do nothing if widgets not yet built
            pass


    def _update_status(self, msg: str) -> None:
        self.msg_var.set(msg)

    def _refresh_bankroll(self) -> None:
        self.bank_var.set(f"Bankroll: {self.bankroll}")

    def _refresh_info_panel(self) -> None:
        self.decks_info_var.set(f"Decks in shoe: {self.shoe.decks}")
        self.discard_info_var.set(f"Discard pile: {self.discard_count} cards")
        self.count_info_var.set(self._format_counts())

    def _format_counts(self) -> str:
        remaining_decks = max(0.01, len(self.shoe.cards) / 52.0)
        self.true_count = round(self.running_count / remaining_decks, 2)
        sign = "+" if self.true_count >= 0 else ""
        return f"Running Count: {self.running_count}    True Count: {sign}{self.true_count:.2f}"

    def _count_value(self, rank: str) -> int:
        if rank in ("2","3","4","5","6"):
            return +1
        if rank in ("7","8","9"):
            return 0
        return -1  # 10,J,Q,K,A

    def _deal_to(self, target_hand: Hand) -> None:
        c = self.shoe.draw()
        if self.shoe.just_reshuffled:
            self.running_count = 0
            self.discard_count = 0
        target_hand.add(c)
        self.running_count += self._count_value(c[0])
        self._refresh_info_panel()

    # ----------------------- UI Layout --------------------------------------

    def _build_ui(self) -> None:
        # Top info bar
        self.top_bar = tk.Frame(self, bg=BACKGROUND_COLOR)
        self.top_bar.pack(side=tk.TOP, fill=tk.X, padx=10, pady=8)

        self.menu_btn = ttk.Button(self.top_bar, text="Main Menu", command=self._enter_main_menu)
        self.menu_btn.pack(side=tk.LEFT, padx=6)

        self.bank_var = tk.StringVar(value=f"Bankroll: {self.bankroll}")
        self.bet_var = tk.IntVar(value=self.min_bet)

        bank_lbl = tk.Label(self.top_bar, textvariable=self.bank_var, fg=TABLE_TEXT, bg=BACKGROUND_COLOR, font=("Arial", 16, "bold"))
        bank_lbl.pack(side=tk.LEFT, padx=(0,12))

        bet_lbl = tk.Label(self.top_bar, text="Bet:", fg=TABLE_TEXT, bg=BACKGROUND_COLOR, font=("Arial", 12))
        bet_lbl.pack(side=tk.LEFT)
        self.bet_spin = tk.Spinbox(self.top_bar, from_=self.min_bet, to=999999, increment=5, width=8, textvariable=self.bet_var, font=("Arial", 12))
        self.bet_spin.pack(side=tk.LEFT, padx=6)

        self.deal_btn = ttk.Button(self.top_bar, text="Deal", command=self.on_deal)
        self.deal_btn.pack(side=tk.LEFT, padx=6)

        self.new_shoe_btn = ttk.Button(self.top_bar, text="Shuffle Shoe", command=self.on_shuffle)
        self.new_shoe_btn.pack(side=tk.LEFT, padx=6)

        # Deck controls
        decks_lbl = tk.Label(self.top_bar, text="Decks:", fg=TABLE_TEXT, bg=BACKGROUND_COLOR, font=("Arial", 12))
        decks_lbl.pack(side=tk.LEFT, padx=(20,6))
        self.decks_spin = tk.Spinbox(self.top_bar, from_=1, to=12, increment=1, width=5, textvariable=self.decks_var, font=("Arial", 12))
        self.decks_spin.pack(side=tk.LEFT, padx=(0,6))
        self.set_decks_btn = ttk.Button(self.top_bar, text="Set Decks", command=self.on_set_decks)
        self.set_decks_btn.pack(side=tk.LEFT, padx=6)

        # Fullscreen toggle button
        self.full_btn = ttk.Button(self.top_bar, text="Fullscreen (F11)", command=self.toggle_fullscreen)
        self.full_btn.pack(side=tk.RIGHT, padx=(6,0))

        # Speed slider block
        speed_frame = tk.Frame(self.top_bar, bg=BACKGROUND_COLOR)
        speed_frame.pack(side=tk.RIGHT)

        speed_lbl = tk.Label(speed_frame, text="Deal speed:", fg=TABLE_TEXT, bg=BACKGROUND_COLOR, font=("Arial", 11))
        speed_lbl.pack(side=tk.LEFT, padx=(0,4))

        self.speed_val_lbl = tk.Label(speed_frame, text=f"{self.deal_delay_var.get()} ms", fg="#e2e8f0", bg=BACKGROUND_COLOR, font=("Arial", 11, "bold"))
        self.speed_val_lbl.pack(side=tk.RIGHT, padx=(4,0))

        self.speed_slider = ttk.Scale(
            speed_frame, from_=50, to=4000, orient="horizontal",
            command=self._on_speed_change, length=220
        )
        self.speed_slider.set(self.deal_delay_var.get())
        self.speed_slider.pack(side=tk.RIGHT)

        # Bottom bar: messages + action buttons
        self.actions = tk.Frame(self, bg=BACKGROUND_COLOR)
        self.actions.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=8)

        self.msg_var = tk.StringVar(value="")
        self.msg_lbl = tk.Label(self.actions, textvariable=self.msg_var, fg=TABLE_TEXT, bg=BACKGROUND_COLOR, font=("Arial", 12))
        self.msg_lbl.pack(side=tk.LEFT)

        self.btn_box = tk.Frame(self.actions, bg=BACKGROUND_COLOR)
        self.btn_box.pack(side=tk.RIGHT)

        self.hit_btn = ttk.Button(self.btn_box, text="Hit", command=self.on_hit)
        self.stand_btn = ttk.Button(self.btn_box, text="Stand", command=self.on_stand)
        self.double_btn = ttk.Button(self.btn_box, text="Double", command=self.on_double)
        self.split_btn = ttk.Button(self.btn_box, text="Split", command=self.on_split)

        for b in (self.hit_btn, self.stand_btn, self.double_btn, self.split_btn):
            b.pack(side=tk.LEFT, padx=4)

        # Table + side panel area
        self.middle_frame = tk.Frame(self, bg=BACKGROUND_COLOR)
        self.middle_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(2,8))

        # Left: main table canvas (expand with window)
        self.canvas = tk.Canvas(self.middle_frame, bg=BACKGROUND_COLOR, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,8))
        self.canvas.bind("<Configure>", lambda e: self._draw_table(getattr(self, "_last_hide_dealer_hole", False)))

        # Right: info panel
        self.side_panel = tk.Frame(self.middle_frame, bg=BACKGROUND_COLOR)
        self.side_panel.pack(side=tk.LEFT, fill=tk.Y)

        # Player HUD
        self.hud_panel = tk.Frame(self.side_panel, bg="#0a3d27", bd=0, highlightbackground="#134e4a", highlightthickness=1)
        self.hud_panel.pack(fill=tk.X, pady=(0,8))
        tk.Label(self.hud_panel, text="PLAYER", fg="#e2e8f0", bg="#0a3d27", font=("Arial", 12, "bold")).pack(anchor="w", padx=8, pady=(6,0))
        self.player_value_var = tk.StringVar(value="Value: —")
        self.player_bet_var = tk.StringVar(value="Bet: —")
        tk.Label(self.hud_panel, textvariable=self.player_value_var, fg="#fef08a", bg="#0a3d27", font=("Arial", 18, "bold")).pack(anchor="w", padx=8, pady=(4,0))
        tk.Label(self.hud_panel, textvariable=self.player_bet_var, fg="#93c5fd", bg="#0a3d27", font=("Arial", 14)).pack(anchor="w", padx=8, pady=(2,6))

        # Outcome banner
        self.outcome_var = tk.StringVar(value="")
        self.outcome_lbl = tk.Label(self.side_panel, textvariable=self.outcome_var, fg="#111111", bg="#d1fae5", font=("Arial", 14, "bold"))
        self.outcome_lbl.pack(fill=tk.X, pady=(0,8))

        # Basic Strategy Hint panel
        self.hint_panel = tk.Frame(self.side_panel, bg="#0a3d27", bd=0, highlightbackground="#134e4a", highlightthickness=1)
        self.hint_panel.pack(fill=tk.X, pady=(0,8))
        tk.Label(self.hint_panel, text="Basic Strategy Hint", fg="#e2e8f0", bg="#0a3d27", font=("Arial", 12, "bold")).pack(anchor="w", padx=8, pady=(6,0))
        cb = ttk.Checkbutton(self.hint_panel, text="Show hint while playing", variable=self.show_hint, command=self._toggle_hint)
        cb.pack(anchor="w", padx=8, pady=(0,4))
        self.advice_lbl = tk.Label(self.hint_panel, textvariable=self.advice_text, fg="#c7d2fe", bg="#0a3d27", font=("Arial", 11), justify="left", wraplength=PL_CHART_W-16)
        self.advice_lbl.pack(fill=tk.X, padx=8, pady=(2,8))

        # Decision Stats panel
        self.stats_panel = tk.Frame(self.side_panel, bg="#0a3d27", bd=0, highlightbackground="#134e4a", highlightthickness=1)
        self.stats_panel.pack(fill=tk.X, pady=(0,8))
        tk.Label(self.stats_panel, text="Decision Stats", fg="#e2e8f0", bg="#0a3d27", font=("Arial", 12, "bold")).pack(anchor="w", padx=8, pady=(6,0))
        tk.Label(self.stats_panel, textvariable=self.stats_total_var, fg="#c7d2fe", bg="#0a3d27", font=("Arial", 12)).pack(anchor="w", padx=12)
        tk.Label(self.stats_panel, textvariable=self.stats_correct_var, fg="#bbf7d0", bg="#0a3d27", font=("Arial", 12, "bold")).pack(anchor="w", padx=12, pady=(0,4))
        row_stats = tk.Frame(self.stats_panel, bg="#0a3d27")
        row_stats.pack(anchor="w", padx=12, pady=(0,8))
        tk.Label(row_stats, textvariable=self.stats_hit_var, fg="#e2e8f0", bg="#0a3d27", font=("Arial", 11)).grid(row=0, column=0, sticky="w", padx=(0,18))
        tk.Label(row_stats, textvariable=self.stats_stand_var, fg="#e2e8f0", bg="#0a3d27", font=("Arial", 11)).grid(row=0, column=1, sticky="w", padx=(0,18))
        tk.Label(row_stats, textvariable=self.stats_double_var, fg="#e2e8f0", bg="#0a3d27", font=("Arial", 11)).grid(row=1, column=0, sticky="w", padx=(0,18))
        tk.Label(row_stats, textvariable=self.stats_split_var, fg="#e2e8f0", bg="#0a3d27", font=("Arial", 11)).grid(row=1, column=1, sticky="w", padx=(0,18))
        ttk.Button(self.stats_panel, text="Reset Stats", command=self._reset_stats).pack(anchor="w", padx=8, pady=(0,8))

        # Drill filter panel
        self.drill_panel = tk.Frame(self.side_panel, bg="#0a3d27", bd=0,
                              highlightbackground="#134e4a", highlightthickness=1)
        self.drill_panel.pack(fill=tk.X, pady=(0,8))

        tk.Label(
            self.drill_panel,
            text="Drill Filters",
            fg="#e2e8f0", bg="#0a3d27",
            font=("Arial", 12, "bold")
        ).pack(anchor="w", padx=8, pady=(6,0))

        ttk.Checkbutton(
            self.drill_panel,
            text="Hard totals",
            variable=self.drill_include_hard
        ).pack(anchor="w", padx=12, pady=(0,2))

        ttk.Checkbutton(
            self.drill_panel,
            text="Soft totals",
            variable=self.drill_include_soft
        ).pack(anchor="w", padx=12, pady=(0,2))

        ttk.Checkbutton(
            self.drill_panel,
            text="Pairs",
            variable=self.drill_include_pairs
        ).pack(anchor="w", padx=12, pady=(0,6))

        # Discard, decks, counts
        self.info_panel = tk.Frame(self.side_panel, bg="#0a3d27", bd=0, highlightbackground="#134e4a", highlightthickness=1)
        self.info_panel.pack(fill=tk.X)

        self.decks_info_var = tk.StringVar(value=f"Decks in shoe: {self.shoe.decks}")
        self.discard_info_var = tk.StringVar(value=f"Discard pile: {self.discard_count} cards")
        self.count_info_var = tk.StringVar(value=self._format_counts())
        tk.Label(self.info_panel, textvariable=self.decks_info_var, fg="#c7d2fe", bg="#0a3d27", font=("Arial", 12)).pack(anchor="w", padx=8, pady=(6,2))
        tk.Label(self.info_panel, textvariable=self.discard_info_var, fg="#c7d2fe", bg="#0a3d27", font=("Arial", 12)).pack(anchor="w", padx=8, pady=(0,2))
        # Card Counting (toggleable)
        cc_header = tk.Frame(self.info_panel, bg="#0a3d27")
        cc_header.pack(fill=tk.X, padx=4, pady=(4,0))
        tk.Label(cc_header, text="Card Counting", fg="#e2e8f0", bg="#0a3d27", font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=4)
        self.cc_toggle_btn = ttk.Button(cc_header, text="Hide", command=self.toggle_card_count_menu)
        self.cc_toggle_btn.pack(side=tk.RIGHT, padx=8)

        self.cc_content = tk.Frame(self.info_panel, bg="#0a3d27")
        self.cc_content.pack(fill=tk.X)

        self.count_info_lbl = tk.Label(self.cc_content, textvariable=self.count_info_var, fg="#c7d2fe", bg="#0a3d27", font=("Arial", 12, "bold"))
        self.count_info_lbl.pack(anchor="w", padx=8, pady=(0,6))

        # P/L chart
        self.chart_frame = tk.Frame(self.side_panel, bg="#0a3d27", bd=0, highlightbackground="#134e4a", highlightthickness=1)
        self.chart_frame.pack(fill=tk.X, pady=(8,0))
        tk.Label(self.chart_frame, text="P/L Chart", fg="#e2e8f0", bg="#0a3d27", font=("Arial", 12, "bold")).pack(anchor="w", padx=8, pady=(6,0))
        self.pl_canvas = tk.Canvas(self.chart_frame, width=PL_CHART_W, height=PL_CHART_H, bg="#0a3d27", highlightthickness=0)
        self.pl_canvas.pack(padx=8, pady=8)

        self._disable_actions()
        self._draw_pl_chart()
        self._bind_hotkeys()
        self._refresh_stats_panel()

        # ----------------------- Main Menu UI -----------------------------------

    def _build_menu(self) -> None:
        """Create the main menu frame shown at startup and when returning to menu."""
        self.menu_frame = tk.Frame(self, bg=BACKGROUND_COLOR)

        title = tk.Label(
            self.menu_frame,
            text="UConn Blackjack Trainer",
            fg=TABLE_TEXT, bg=BACKGROUND_COLOR,
            font=("Arial", 32, "bold")
        )
        title.pack(pady=(60, 10))

        subtitle = tk.Label(
            self.menu_frame,
            text="Choose a mode to begin training.",
            fg=TABLE_TEXT, bg=BACKGROUND_COLOR,
            font=("Arial", 16)
        )
        subtitle.pack(pady=(0, 30))

        btns = tk.Frame(self.menu_frame, bg=BACKGROUND_COLOR)
        btns.pack()

        trainer_btn = ttk.Button(
            btns,
            text="Standard Training (Basic Strategy)",
            command=lambda: self._start_mode("trainer")
        )
        trainer_btn.grid(row=0, column=0, padx=10, pady=10, ipadx=20, ipady=10)

        drills_btn = ttk.Button(
            btns,
            text="Drill Mode",
            command=lambda: self._start_mode("drill")
        )
        drills_btn.grid(row=1, column=0, padx=10, pady=10, ipadx=20, ipady=10)

        quit_btn = ttk.Button(
            self.menu_frame,
            text="Quit",
            command=self.destroy
        )
        quit_btn.pack(pady=(40, 0))

    def _enter_main_menu(self) -> None:
        """Hide game UI and show the main menu."""
        # Reset round state so nothing is half-running in the background
        self.in_menu = True
        self.in_round = False
        self.animating = False
        self.round_complete = False
        self._disable_actions()
        if hasattr(self, "deal_btn"):
            self.deal_btn.config(state="disabled")

        # Hide game frames if they exist
        if hasattr(self, "top_bar"):
            self.top_bar.pack_forget()
        if hasattr(self, "actions"):
            self.actions.pack_forget()
        if hasattr(self, "middle_frame"):
            self.middle_frame.pack_forget()

        # Build menu frame once
        if not hasattr(self, "menu_frame"):
            self._build_menu()
        self.menu_frame.pack(fill=tk.BOTH, expand=True)
        # Clear status
        if hasattr(self, "msg_var"):
            self._update_status("")

    def _exit_main_menu(self) -> None:
        """Hide the main menu and show the game UI."""
        if hasattr(self, "menu_frame"):
            self.menu_frame.pack_forget()

        self.in_menu = False

        # Show game UI frames again
        self.top_bar.pack(side=tk.TOP, fill=tk.X, padx=10, pady=8)
        self.actions.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=8)
        self.middle_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(2, 8))

        # Re-enable Deal button and reset status text
        self.deal_btn.config(state="normal")
        self._update_status("Welcome! Set your bet and click Deal.  Press F11 to toggle fullscreen.")

    def _setup_trainer_mode(self) -> None:
        """Configure UI/controls for normal trainer mode."""
        self.mode = "trainer"
        # Enable shoe/bet controls
        self.bet_spin.config(state="normal")
        self.new_shoe_btn.config(state="normal")
        self.decks_spin.config(state="normal")
        self.set_decks_btn.config(state="normal")
        self.deal_btn.config(text="Deal", state="normal")

        self._set_trainer_side_panel_layout()

        self._update_status("Welcome! Set your bet and click Deal.  Press F11 to toggle fullscreen.")
        self.outcome_var.set("")
        self.advice_text.set("")
        self._highlight_buttons(None)

    def _setup_drill_mode(self) -> None:
        """Configure UI/controls for drill mode (no bankroll, no shoe use)."""
        self.mode = "drill"

        # Disable shoe / bet controls (not used in drill)
        self.bet_spin.config(state="disabled")
        self.new_shoe_btn.config(state="disabled")
        self.decks_spin.config(state="disabled")
        self.set_decks_btn.config(state="disabled")

        self.deal_btn.config(text="Next Question", state="normal")

        self._set_drill_side_panel_layout()

        # Reset per-drill visuals & stats
        self._reset_stats()
        self.outcome_var.set("")
        self.advice_text.set("")
        self._highlight_buttons(None)

        self._update_status(
            "Drill Mode: choose which hand types to drill (Hard / Soft / Pairs), "
            "then click Next Question."
        )    

    def _start_mode(self, mode: str) -> None:
        """Set the active mode and transition from menu into the game screen."""
        self.mode = mode
        self._exit_main_menu()
        if mode == "trainer":
            self._setup_trainer_mode()
        else:
            self._setup_drill_mode()



    # ----------------------- Insurance Prompt UI -----------------------------

    def _show_insurance_prompt(self, max_ins: int) -> None:
        if self.insurance_prompt_visible:
            return
        self.insurance_prompt_visible = True
        self.insurance_max_allowed = max_ins

        # Build a small inline prompt to the left of the action buttons
        self._insurance_frame = tk.Frame(self.actions, bg="#083344", highlightbackground="#14b8a6", highlightthickness=1)
        self._insurance_frame.pack(side=tk.RIGHT, padx=(0,10))

        prompt = tk.Label(
            self._insurance_frame,
            text=f"Insurance? Up to {min(max_ins, self.bankroll)}  (Y/N)",
            fg="#e0f2fe", bg="#083344", font=("Arial", 11, "bold")
        )
        prompt.pack(side=tk.LEFT, padx=8, pady=4)

        yes_btn = ttk.Button(self._insurance_frame, text="Yes (Y)", command=self._on_insurance_yes)
        no_btn = ttk.Button(self._insurance_frame, text="No (N)", command=self._on_insurance_no)
        yes_btn.pack(side=tk.LEFT, padx=(4,2), pady=4)
        no_btn.pack(side=tk.LEFT, padx=(2,8), pady=4)

        # While insurance is showing, disable other action buttons
        self._enable_actions(False, False, False, False)
        self._update_status("Dealer shows an Ace. Decide on insurance (Y/N).")

    def _hide_insurance_prompt(self) -> None:
        if self._insurance_frame is not None:
            try:
                self._insurance_frame.destroy()
            except Exception:
                pass
            self._insurance_frame = None
        self.insurance_prompt_visible = False
        self.insurance_max_allowed = 0

    def _on_insurance_yes(self) -> None:
        if not self.insurance_prompt_visible:
            return
        max_ins = min(self.insurance_max_allowed, self.bankroll)
        if max_ins > 0:
            self.insurance_bet = max_ins
            self.bankroll -= max_ins
            self._refresh_bankroll()
            self._update_status(f"Insurance purchased for {max_ins}.")
        else:
            self._update_status("No bankroll available for insurance.")
        self._hide_insurance_prompt()
        # Continue flow
        self._after_insurance_decision()

    def _on_insurance_no(self) -> None:
        if not self.insurance_prompt_visible:
            return
        self._update_status("Insurance declined.")
        self._hide_insurance_prompt()
        # Continue flow
        self._after_insurance_decision()

    def _after_insurance_decision(self) -> None:
        # Resume draw state as it was (dealer hole hidden unless dealer has blackjack after peek)
        up = self.dealer.cards[0][0]
        self.dealer_blackjack = self.dealer.is_blackjack() if up in ("A","10","J","Q","K") else False
        self._draw_table(hide_dealer_hole=not self.dealer_blackjack)

        if self.dealer_blackjack:
            self._update_status("Dealer has blackjack.")
            self._finish_round(dealer_blackjack=True)
            return

        player = self.player_hands[0].hand
        if player.is_blackjack():
            self._update_status("Blackjack! Paying 3:2.")
            self._finish_round(dealer_blackjack=False)
            return

        self._update_actions_for_active_hand()

    # ----------------------- Rendering --------------------------------------

    def _draw_table(self, hide_dealer_hole: bool) -> None:
        self._last_hide_dealer_hole = hide_dealer_hole

        self.canvas.delete("all")
        cw = max(300, self.canvas.winfo_width())
        ch = max(300, self.canvas.winfo_height())

        # Vertical layout anchors
        top_margin = int(ch * 0.03)
        dealer_y = top_margin + 20
        dealer_val_y = dealer_y + CARD_H + 14

        player_section_top = int(ch * 0.55)
        label_y = player_section_top - 60

        # Dealer area
        self._draw_label(cw // 2, top_margin, "Dealer", anchor="n", size=14)
        self._draw_hand_centered(self.dealer, y=dealer_y, hide_hole=hide_dealer_hole, slot_index=0, slots=1, canvas_width=cw)

        if not hide_dealer_hole:
            self._draw_label(cw // 2, dealer_val_y, f"Value: {self.dealer.value()}", anchor="n", size=12)

        # Player hands
        if len(self.player_hands) == 1:
            self._draw_label(cw // 2, label_y, "Player", anchor="n", size=14)
            self._draw_player_hand_centered(self.player_hands[0], y=player_section_top, is_active=(self.active_hand_index == 0), slot_index=0, slots=1, canvas_width=cw)
        elif len(self.player_hands) == 2:
            # Two slots side-by-side
            left_center = (cw // 4)
            right_center = (cw * 3) // 4
            self._draw_label(left_center, label_y, "Hand 1", anchor="n", size=14)
            self._draw_label(right_center, label_y, "Hand 2", anchor="n", size=14)
            self._draw_player_hand_centered(self.player_hands[0], y=player_section_top, is_active=(self.active_hand_index == 0), slot_index=0, slots=2, canvas_width=cw)
            self._draw_player_hand_centered(self.player_hands[1], y=player_section_top, is_active=(self.active_hand_index == 1), slot_index=1, slots=2, canvas_width=cw)

        # Update HUD
        if self.player_hands:
            cur = self.player_hands[self.active_hand_index if self.active_hand_index < len(self.player_hands) else 0]
            self.player_value_var.set(f"Value: {cur.hand.value()}{' (soft)' if cur.hand.is_soft() else ''}")
            self.player_bet_var.set(f"Bet: {cur.bet}{' (doubled)' if cur.doubled else ''}")
        else:
            self.player_value_var.set("Value: —")
            self.player_bet_var.set("Bet: —")

    def _draw_label(self, x: int, y: int, text: str, anchor="center", size=12) -> None:
        self.canvas.create_text(x, y, text=text, fill=TABLE_TEXT, font=("Arial", size, "bold"), anchor=anchor)

    # Centered drawing helpers
    def _slot_center_x(self, slot_index: int, slots: int, canvas_width: int) -> int:
        region_w = canvas_width // max(1, slots)
        return region_w * slot_index + region_w // 2

    def _hand_start_x(self, hand: Hand, slot_index: int, slots: int, canvas_width: int) -> int:
        hand_w = CARD_W + max(0, len(hand.cards) - 1) * CARD_SPACING
        cx = self._slot_center_x(slot_index, slots, canvas_width)
        start_x = int(cx - hand_w / 2)
        return max(10, start_x)

    def _draw_player_hand_centered(self, ph: PlayerHand, y: int, is_active: bool, slot_index: int, slots: int, canvas_width: int) -> None:
        start_x = self._hand_start_x(ph.hand, slot_index, slots, canvas_width)
        self._draw_hand(ph.hand, x=start_x, y=y, hide_hole=False)
        status = f"Value: {ph.hand.value()}{' (soft)' if ph.hand.is_soft() else ''}    Bet: {ph.bet}{' (Doubled)' if ph.doubled else ''}"
        self._draw_label(start_x + CARD_W * 3 + CARD_SPACING * 3, y + CARD_H + 6, status, anchor="nw", size=12)
        if is_active:
            pad = 10
            max_w = CARD_W + CARD_SPACING * 5
            self.canvas.create_rectangle(start_x - pad, y - pad, start_x + max_w + pad, y + CARD_H + pad, outline="#ffd166", width=3)

    def _draw_hand_centered(self, hand: Hand, y: int, hide_hole: bool, slot_index: int, slots: int, canvas_width: int) -> None:
        start_x = self._hand_start_x(hand, slot_index, slots, canvas_width)
        self._draw_hand(hand, x=start_x, y=y, hide_hole=hide_hole)

    def _draw_hand(self, hand: Hand, x: int, y: int, hide_hole: bool) -> None:
        for i, c in enumerate(hand.cards):
            xx = x + i * CARD_SPACING
            yy = y
            if hide_hole and i == 1:
                self._draw_card_back(xx, yy)
            else:
                self._draw_card_face(xx, yy, c)

    def _suit_color(self, suit: str) -> str:
        return "#e11d48" if suit in ("♥", "♦") else "#111111"

    def _draw_card_face(self, x: int, y: int, card: Card) -> None:
        r, s = card
        color = self._suit_color(s)
        # shadow
        self.canvas.create_rectangle(x+3, y+3, x + CARD_W+3, y + CARD_H+3, fill="#0e3b28", outline="")
        # face
        self.canvas.create_rectangle(x, y, x + CARD_W, y + CARD_H, fill=CARD_FACE_COLOR, outline="#111111", width=2)
        # corner ranks
        self.canvas.create_text(x + 8, y + 10, text=r, fill=color, font=("Arial", 16, "bold"), anchor="nw")
        self.canvas.create_text(x + CARD_W - 8, y + CARD_H - 10, text=r, fill=color, font=("Arial", 16, "bold"), anchor="se")
        # center content
        if r in ("J", "Q", "K", "A"):
            big = r if r != "A" else s  # show suit big for Ace
            fsize = 40 if r == "A" else 42
            self.canvas.create_text(x + CARD_W/2, y + CARD_H/2, text=big, fill=color, font=("Arial", fsize, "bold"))
        else:
            self._draw_pips(x, y, s, int(r))

    def _draw_pips(self, x: int, y: int, suit: str, count: int) -> None:
        color = self._suit_color(suit)
        cx = x + CARD_W/2
        cy = y + CARD_H/2
        left = x + CARD_W*0.28
        right = x + CARD_W*0.72
        top = y + CARD_H*0.24
        upper = y + CARD_H*0.33
        middle = cy
        lower = y + CARD_H*0.67
        bottom = y + CARD_H*0.76
        layouts = {
            2: [(cx, upper), (cx, lower)],
            3: [(cx, top), (cx, middle), (cx, bottom)],
            4: [(left, upper), (right, upper), (left, lower), (right, lower)],
            5: [(left, upper), (right, upper), (cx, middle), (left, lower), (right, lower)],
            6: [(left, upper), (right, upper), (left, middle), (right, middle), (left, lower), (right, lower)],
            7: [(left, upper), (right, upper), (left, middle), (right, middle), (cx, middle), (left, lower), (right, lower)],
            8: [(left, upper), (right, upper), (left, middle), (right, middle), (left, lower), (right, lower), (cx, upper), (cx, lower)],
            9: [(left, upper), (right, upper), (left, middle), (right, middle), (left, lower), (right, lower), (cx, upper), (cx, lower), (cx, middle)],
            10: [(left, upper), (right, upper), (left, middle), (right, middle), (left, lower), (right, lower), (cx, upper), (cx, lower), (cx, top), (cx, bottom)],
        }
        for px, py in layouts.get(count, []):
            self.canvas.create_text(px, py, text=suit, fill=color, font=("Arial", 22, "bold"))

    def _draw_card_back(self, x: int, y: int) -> None:
        # shadow
        self.canvas.create_rectangle(x+3, y+3, x + CARD_W+3, y + CARD_H+3, fill="#0e3b28", outline="")
        # back
        self.canvas.create_rectangle(x, y, x + CARD_W, y + CARD_H, fill=CARD_BACK_COLOR, outline="#0d3a74", width=2)
        for dy in range(14, CARD_H-14, 22):
            self.canvas.create_line(x + 12, y + dy, x + CARD_W - 12, y + dy + 10, fill="#90cdf4")
            self.canvas.create_line(x + CARD_W - 12, y + dy, x + 12, y + dy + 10, fill="#90cdf4")

    # ----------------------- P/L chart ---------------------------------------

    def _draw_pl_chart(self) -> None:
        c = self.pl_canvas
        c.delete("all")
        c.create_rectangle(PL_CHART_PAD, PL_CHART_PAD, PL_CHART_W-PL_CHART_PAD, PL_CHART_H-PL_CHART_PAD, outline="#334155")
        if len(self.pl_points) < 2:
            c.create_text(PL_CHART_W/2, PL_CHART_H/2, text="No rounds yet", fill="#94a3b8", font=("Arial", 10))
            return

        vals = self.pl_points
        vmin, vmax = min(vals), max(vals)
        if vmin == vmax:
            vmin -= 1; vmax += 1

        x0, y0 = PL_CHART_PAD+4, PL_CHART_PAD+4
        w = (PL_CHART_W - 2*PL_CHART_PAD - 8)
        h = (PL_CHART_H - 2*PL_CHART_PAD - 8)
        step = w / max(1, (len(vals)-1))

        def to_xy(i: int, v: int) -> tuple[float, float]:
            x = x0 + i * step
            y = y0 + h * (1 - (v - vmin) / (vmax - vmin))
            return x, y

        self.pl_canvas.create_text(PL_CHART_PAD+6, PL_CHART_PAD, text=f"${vmax}", fill="#93c5fd", anchor="nw", font=("Arial", 9))
        self.pl_canvas.create_text(PL_CHART_PAD+6, PL_CHART_H-PL_CHART_PAD-14, text=f"${vmin}", fill="#93c5fd", anchor="nw", font=("Arial", 9))

        points = []
        for i, v in enumerate(vals):
            points.extend(to_xy(i, v))
        c.create_line(*points, fill="#22d3ee", width=2)
        x_last, y_last = to_xy(len(vals)-1, vals[-1])
        c.create_oval(x_last-3, y_last-3, x_last+3, y_last+3, outline="#22d3ee", fill="#22d3ee")

    # ----------------------- Basic Strategy Engine ---------------------------

    def _best_move(self, ph: PlayerHand, dealer_up: str) -> Tuple[str, str]:
        """Return ('HIT'|'STAND'|'DOUBLE'|'SPLIT', explanation). Rules: S17, DAS, no surrender."""
        h = ph.hand
        up = dealer_up
        can_double = ph.can_double() and (self.bankroll >= ph.bet)
        can_split = (len(h.cards) == 2 and h.is_pair() and len(self.player_hands) < 2 and self.bankroll >= ph.bet)

        if getattr(self, "mode", None) == "drill":
            can_double = ph.can_double()
            can_split = (len(h.cards) == 2 and h.is_pair())

        # Pair rules
        if len(h.cards) == 2 and h.is_pair():
            r = h.cards[0][0]
            if r in ("A","8"):
                if can_split:
                    return "SPLIT", "Always split A,A and 8,8 — two hands outperform one."
            if r in ("10","J","Q","K"):
                return "STAND", "Never split 10s; 20 is already strong."
            if r == "9":
                if up in ("2","3","4","5","6","8","9"):
                    if can_split:
                        return "SPLIT", "9,9 splits vs 2–6 and 8–9; stand vs 7,10,A."
                return "STAND", "Stand 9,9 vs 7, 10, A."
            if r == "7":
                if up in ("2","3","4","5","6","7") and can_split:
                    return "SPLIT", "7,7 splits vs 2–7."
            if r == "6":
                if up in ("2","3","4","5","6") and can_split:
                    return "SPLIT", "6,6 splits vs 2–6."
            if r == "5":
                if can_double and up in ("2","3","4","5","6","7","8","9"):
                    return "DOUBLE", "5,5 is hard 10 — double vs 2–9."
                return "HIT", "5,5 plays like 10: hit if you can't double."
            if r == "4":
                if up in ("5","6") and can_split:
                    return "SPLIT", "4,4 splits vs 5–6; otherwise treat as 8."
            if r in ("2","3"):
                if up in ("2","3","4","5","6","7") and can_split:
                    return "SPLIT", f"{r},{r} splits vs 2–7."

        # Soft totals (two-card)
        if h.is_soft() and len(h.cards) == 2:
            total = h.value()
            if total >= 19:
                return "STAND", "Soft 19+ stands."
            if total == 18:
                if up in ("3","4","5","6") and can_double:
                    return "DOUBLE", "Soft 18 doubles vs 3–6."
                if up in ("2","7","8"):
                    return "STAND", "Soft 18 stands vs 2,7,8."
                return "HIT", "Soft 18 hits vs 9,10,A."
            if total == 17:
                if up in ("3","4","5","6") and can_double:
                    return "DOUBLE", "Soft 17 doubles vs 3–6."
                return "HIT", "Soft 17 hits otherwise."
            if total in (15,16):
                if up in ("4","5","6") and can_double:
                    return "DOUBLE", "Soft 15/16 doubles vs 4–6."
                return "HIT", "Soft 15/16 hits otherwise."
            if total in (13,14):
                if up in ("5","6") and can_double:
                    return "DOUBLE", "Soft 13/14 doubles vs 5–6."
                return "HIT", "Soft 13/14 hits otherwise."

        # Hard totals
        v = h.value()
        if v >= 17:
            return "STAND", "Hard 17+ stands."
        if v == 16:
            if up in ("2","3","4","5","6"):
                return "STAND", "Hard 16 stands vs 2–6."
            return "HIT", "Hard 16 hits vs 7–A."
        if v == 15:
            if up in ("2","3","4","5","6"):
                return "STAND", "Hard 15 stands vs 2–6."
            return "HIT", "Hard 15 hits vs 7–A."
        if v in (13,14):
            if up in ("2","3","4","5","6"):
                return "STAND", "Hard 13–14 stand vs 2–6."
            return "HIT", "Hard 13–14 hit vs 7–A."
        if v == 12:
            if up in ("4","5","6"):
                return "STAND", "Hard 12 stands vs 4–6."
            return "HIT", "Hard 12 hits vs 2–3 and 7–A."
        if v == 11:
            if can_double and up != "A":
                return "DOUBLE", "11 doubles vs 2–10."
            return "HIT", "Hit 11 vs A (S17)."
        if v == 10:
            if can_double and up in ("2","3","4","5","6","7","8","9"):
                return "DOUBLE", "10 doubles vs 2–9."
            return "HIT", "Hit 10 vs 10 or A."
        if v == 9:
            if can_double and up in ("3","4","5","6"):
                return "DOUBLE", "9 doubles vs 3–6."
            return "HIT", "Hit 9 otherwise."
        return "HIT", "Hit 5–8."

    def _highlight_buttons(self, move: str | None) -> None:
        # Reset labels
        self.hit_btn.config(text="Hit")
        self.stand_btn.config(text="Stand")
        self.double_btn.config(text="Double")
        self.split_btn.config(text="Split")
        if move == "HIT":
            self.hit_btn.config(text="★ Hit")
        elif move == "STAND":
            self.stand_btn.config(text="★ Stand")
        elif move == "DOUBLE":
            self.double_btn.config(text="★ Double")
        elif move == "SPLIT":
            self.split_btn.config(text="★ Split")

    def _update_hint(self) -> None:
        if not self.show_hint.get():
            return
        if not self.player_hands or self.active_hand_index >= len(self.player_hands):
            self.advice_text.set("")
            self._highlight_buttons(None)
            return
        if not self.dealer.cards:
            self.advice_text.set("")
            self._highlight_buttons(None)
            return
        ph = self.player_hands[self.active_hand_index]
        dealer_up = self.dealer.cards[0][0]
        move, why = self._best_move(ph, dealer_up)
        self.advice_text.set(f"Best move: {move}\n{why}")
        self._highlight_buttons(move)

    # ----------------------- Decision Stats Helpers --------------------------

    def _accuracy_pct(self) -> float:
        return (self.stats['correct'] / self.stats['total'] * 100.0) if self.stats['total'] > 0 else 0.0

    def _refresh_stats_panel(self) -> None:
        self.stats_total_var.set(f"Total: {self.stats['total']}")
        self.stats_correct_var.set(f"Correct: {self.stats['correct']} ({self._accuracy_pct():.1f}%)")
        self.stats_hit_var.set(f"Hit: {self.stats['HIT']['c']}/{self.stats['HIT']['t']}")
        self.stats_stand_var.set(f"Stand: {self.stats['STAND']['c']}/{self.stats['STAND']['t']}")
        self.stats_double_var.set(f"Double: {self.stats['DOUBLE']['c']}/{self.stats['DOUBLE']['t']}")
        self.stats_split_var.set(f"Split: {self.stats['SPLIT']['c']}/{self.stats['SPLIT']['t']}")

    def _reset_stats(self) -> None:
        self.stats = {
            'total': 0, 'correct': 0,
            'HIT': {'t': 0, 'c': 0},
            'STAND': {'t': 0, 'c': 0},
            'DOUBLE': {'t': 0, 'c': 0},
            'SPLIT': {'t': 0, 'c': 0},
        }
        self._refresh_stats_panel()

    def _record_action(self, action: str) -> None:
        # Compare the action taken with current basic strategy best move
        if not self.player_hands or not self.dealer.cards or self.active_hand_index >= len(self.player_hands):
            return
        ph = self.player_hands[self.active_hand_index]
        dealer_up = self.dealer.cards[0][0]
        best, _ = self._best_move(ph, dealer_up)
        self.stats['total'] += 1
        if action in self.stats:
            self.stats[action]['t'] += 1
        if action == best:
            self.stats['correct'] += 1
            if action in self.stats:
                self.stats[action]['c'] += 1
        self._refresh_stats_panel()

    # ----------------------- Game Flow ---------------------------------------

    # ----------------------- Drill Mode Helpers -------------------------------

    def _generate_drill_hand(self) -> None:
        """Generate a random (player, dealer) starting situation for drill mode,
        avoiding trivial player 21 hands."""
        # Choose which category to draw from
        categories = []
        if self.drill_include_hard.get():
            categories.append("hard")
        if self.drill_include_soft.get():
            categories.append("soft")
        if self.drill_include_pairs.get():
            categories.append("pair")
        if not categories:
            categories = ["hard"]  # fallback

        # Dealer upcard + hole
        up_rank = random.choice(RANKS)
        up_suit = random.choice(SUITS)
        hole_rank = random.choice(RANKS)
        hole_suit = random.choice(SUITS)
        self.dealer = Hand([(up_rank, up_suit), (hole_rank, hole_suit)])

        # Re-roll player hand until it's NOT 21
        while True:
            category = random.choice(categories)

            if category == "pair":
                r = random.choice(RANKS)
                s1, s2 = random.sample(SUITS, 2)
                cards = [(r, s1), (r, s2)]

            elif category == "soft":
                # One ace + one non-ace card (soft total), but allow all except 21
                non_ace_ranks = [r for r in RANKS if r != "A"]
                r2 = random.choice(non_ace_ranks)
                s1, s2 = random.sample(SUITS, 2)
                cards = [("A", s1), (r2, s2)]
                random.shuffle(cards)

            else:  # "hard"
                non_ace_ranks = [r for r in RANKS if r != "A"]
                while True:
                    r1 = random.choice(non_ace_ranks)
                    r2 = random.choice(non_ace_ranks)
                    total = VALUES[r1] + VALUES[r2]
                    if 5 <= total <= 21:
                        break
                s1, s2 = random.sample(SUITS, 2)
                cards = [(r1, s1), (r2, s2)]

            player_hand = Hand(cards)

            # Skip trivial hands that already total 21 (e.g., A+10, 10+J, etc.)
            if player_hand.value() != 21:
                break

        self.player_hands = [PlayerHand(hand=player_hand, bet=self.min_bet)]
        self.active_hand_index = 0
        self.insurance_bet = 0
        self.dealer_blackjack = False
        self.round_complete = False
        self.in_round = True

        # Reset visuals
        self.outcome_var.set("")
        self._highlight_buttons(None)
        self.advice_text.set("")
        self._enable_actions(hit=True, stand=True, double=True, split=True)

        # Show dealer upcard, hide hole (realistic)
        self._draw_table(hide_dealer_hole=True)

        category_name = {
            "hard": "Hard total",
            "soft": "Soft total",
            "pair": "Pair",
        }[category]
        self._update_status(f"Drill: {category_name}. What's the best move?")


    def _handle_drill_answer(self, action: str) -> None:
        """Handle a user action in drill mode: grade it and show feedback."""
        if not self.in_round or not self.player_hands or not self.dealer.cards:
            return

        self.in_round = False
        self.deal_btn.config(state="normal")  # allow Next Question

        # Record & grade using existing stats machinery
        self._record_action(action)

        ph = self.player_hands[self.active_hand_index]
        dealer_up = self.dealer.cards[0][0]
        best, why = self._best_move(ph, dealer_up)

        if action == best:
            self.outcome_var.set("✅ Correct!")
            self.outcome_lbl.config(bg="#bbf7d0")
            self._update_status(f"Correct: {best}. {why}")
        else:
            self.outcome_var.set("❌ Incorrect")
            self.outcome_lbl.config(bg="#fecaca")
            self._update_status(f"Best move: {best}. {why}")

        # Visually highlight the best move
        self._highlight_buttons(best)
        # No bankroll / shoe changes in drill mode

    
    def on_set_decks(self) -> None:
        if getattr(self, "in_menu", False):
            return
        
        try:
            decks = int(self.decks_var.get())
        except Exception:
            messagebox.showerror("Invalid decks", "Please enter a valid integer (1-12).")
            return
        if not (1 <= decks <= 12):
            messagebox.showerror("Invalid decks", "Decks must be between 1 and 12.")
            return
        self.shoe.decks = decks
        self.shoe._reshuffle()
        self.running_count = 0
        self.discard_count = 0
        self.round_complete = False
        self._refresh_info_panel()
        self._update_status(f"Set shoe to {decks} deck(s); shuffled fresh shoe.")
        self.advice_text.set("")
        self._highlight_buttons(None)

    def on_shuffle(self) -> None:
        if getattr(self, "in_menu", False):
            return
        self.shoe._reshuffle()
        self.running_count = 0
        self.discard_count = 0
        self.round_complete = False
        self._refresh_info_panel()
        self._update_status("Shuffled a fresh shoe.")
        self._draw_table(hide_dealer_hole=False)
        self.advice_text.set("")
        self._highlight_buttons(None)

    def on_deal(self) -> None:
        if getattr(self, "in_menu", False):
            return
        
        if getattr(self, "mode", None) == "drill":
            # Prevent skipping without answering
            self.deal_btn.config(state="disabled")
            self._generate_drill_hand()
            return

        if self.in_round or self.animating:
            return
        # Clear any dangling insurance prompt just in case
        self._hide_insurance_prompt()

        # If previous round finished, discard now so cards remained visible until this point
        if self.round_complete:
            _ = self._collect_discards()
            self.dealer.clear()
            for ph in self.player_hands:
                ph.hand.clear()
            self.round_complete = False
            self._draw_table(hide_dealer_hole=False)

        bet = self.bet_var.get()
        try:
            bet = int(bet)
        except Exception:
            messagebox.showerror("Invalid Bet", "Please enter a valid integer bet.")
            return
        if bet < self.min_bet:
            messagebox.showerror("Invalid Bet", f"Minimum bet is {self.min_bet}.")
            return
        if bet > self.bankroll:
            messagebox.showerror("Invalid Bet", "You don't have enough bankroll for that bet.")
            return

        # Clear banners/hint
        self.outcome_var.set("")
        self.advice_text.set("")
        self._highlight_buttons(None)

        # Prepare round
        self.deal_btn.config(state="disabled")
        self.in_round = True
        self.animating = True
        self._disable_actions()
        self.dealer = Hand([])
        player = Hand([])
        self.player_hands = [PlayerHand(hand=player, bet=bet)]
        self.active_hand_index = 0
        self.insurance_bet = 0
        self.dealer_blackjack = False

        self.bankroll -= bet
        self._refresh_bankroll()

        # Animated initial deal: P, D, P, D (hole card hidden)
        steps = [
            ("Player gets first card", lambda: self._deal_to(player)),
            ("Dealer upcard", lambda: self._deal_to(self.dealer)),
            ("Player second card", lambda: self._deal_to(player)),
            ("Dealer hole card", lambda: self._deal_to(self.dealer)),
        ]

        def run_step(i: int) -> None:
            if i >= len(steps):
                self.animating = False
                self._post_initial_deal()
                return
            desc, action = steps[i]
            action()
            self._draw_table(hide_dealer_hole=True)
            self._update_status(desc)
            self.after(self._delay(), lambda: run_step(i + 1))

        self._draw_table(hide_dealer_hole=True)
        run_step(0)

    def _post_initial_deal(self) -> None:
        # Insurance if dealer shows Ace
        if self.dealer.cards and self.dealer.cards[0][0] == "A":
            self.canvas.update_idletasks()
            self._draw_table(hide_dealer_hole=True)
            self._offer_insurance()
            # _offer_insurance will bring up inline prompt and pause here
            return

        # Otherwise continue with normal peek & flow
        self._after_insurance_decision()

    def _offer_insurance(self) -> None:
        total_bets = sum(ph.bet for ph in self.player_hands)
        max_ins = total_bets // 2
        if max_ins == 0 or self.bankroll == 0:
            # If no insurance possible, just continue
            self._after_insurance_decision()
            return
        self._show_insurance_prompt(max_ins)

    def _update_actions_for_active_hand(self) -> None:
        ph = self.player_hands[self.active_hand_index]
        can_double = ph.can_double() and (self.bankroll >= ph.bet)
        can_split = (len(ph.hand.cards) == 2 and ph.hand.is_pair() and len(self.player_hands) < 2 and self.bankroll >= ph.bet)
        self._enable_actions(hit=True, stand=True, double=can_double, split=can_split)
        self._draw_table(hide_dealer_hole=True)
        self._update_status("Your move.")
        # Show hint BEFORE action
        self._update_hint()

    def on_hit(self) -> None:
        if getattr(self, "in_menu", False):
            return
        if getattr(self, "mode", None) == "drill":
            self._handle_drill_answer("HIT")
            return

        if not self.in_round or self.animating or self.insurance_prompt_visible:
            return
        ph = self.player_hands[self.active_hand_index]
        self._record_action('HIT')
        self._deal_to(ph.hand)
        self._draw_table(hide_dealer_hole=True)

        if ph.hand.is_bust():
            self._update_status("You bust!")
            self._next_hand_or_dealer()
        else:
            if ph.split_aces and len(ph.hand.cards) >= 2:
                self._update_status("Split Aces receive only one card.")
                self._next_hand_or_dealer()
            else:
                self._update_actions_for_active_hand()

    def on_stand(self) -> None:
        if getattr(self, "in_menu", False):
            return
        if getattr(self, "mode", None) == "drill":
            self._handle_drill_answer("STAND")
            return
        if not self.in_round or self.animating or self.insurance_prompt_visible:
            return
        self._record_action('STAND')
        self._next_hand_or_dealer()

    def on_double(self) -> None:
        if getattr(self, "in_menu", False):
            return
        if getattr(self, "mode", None) == "drill":
            self._handle_drill_answer("DOUBLE")
            return
        if not self.in_round or self.animating or self.insurance_prompt_visible:
            return
        ph = self.player_hands[self.active_hand_index]
        if not ph.can_double() or self.bankroll < ph.bet:
            return
        self._record_action('DOUBLE')
        self.bankroll -= ph.bet
        self._refresh_bankroll()
        ph.doubled = True
        self._deal_to(ph.hand)
        self._draw_table(hide_dealer_hole=True)
        if ph.hand.is_bust():
            self._update_status("You bust after doubling.")
        self._next_hand_or_dealer()

    def on_split(self) -> None:
        if getattr(self, "in_menu", False):
            return
        if getattr(self, "mode", None) == "drill":
            self._handle_drill_answer("SPLIT")
            return
        if not self.in_round or self.animating or self.insurance_prompt_visible:
            return
        ph = self.player_hands[self.active_hand_index]
        if not (len(ph.hand.cards) == 2 and ph.hand.is_pair() and len(self.player_hands) < 2 and self.bankroll >= ph.bet):
            return
        self._record_action('SPLIT')
        self.bankroll -= ph.bet
        self._refresh_bankroll()
        c1, c2 = ph.hand.cards
        new1 = Hand([c1])
        new2 = Hand([c2])
        self._deal_to(new1)
        self._deal_to(new2)
        split_aces_flag = (c1[0] == "A" and c2[0] == "A")
        self.player_hands[self.active_hand_index] = PlayerHand(new1, ph.bet, split_aces=split_aces_flag)
        self.player_hands.insert(self.active_hand_index + 1, PlayerHand(new2, ph.bet, split_aces=split_aces_flag))
        self._draw_table(hide_dealer_hole=True)
        self._update_status("Hand split.")
        self._update_actions_for_active_hand()

    # ----------------------- Dealer & Settlement -----------------------------

    def _next_hand_or_dealer(self) -> None:
        self.active_hand_index += 1
        if self.active_hand_index < len(self.player_hands):
            ph = self.player_hands[self.active_hand_index]
            if ph.split_aces and len(ph.hand.cards) >= 2:
                self._update_status("Split Aces receive one card only. Moving on.")
                self._next_hand_or_dealer()
                return
            self._update_actions_for_active_hand()
            return

        if not all(ph.hand.is_bust() for ph in self.player_hands):
            self._disable_actions()
            self._dealer_play()
        self._finish_round(dealer_blackjack=False)

    def _dealer_play(self) -> None:
        self._draw_table(hide_dealer_hole=False)
        self.update_idletasks()
        self.after(self._delay())

        while True:
            val = self.dealer.value()
            soft = self.dealer.is_soft()
            if val < 17:
                self._deal_to(self.dealer)
            elif val == 17 and (not self.stand_on_soft_17) and soft:
                self._deal_to(self.dealer)
            else:
                break
            self._draw_table(hide_dealer_hole=False)
            self.after(self._delay())
            self.update_idletasks()

    def _collect_discards(self) -> int:
        moved = 0
        moved += len(self.dealer.cards)
        for ph in self.player_hands:
            moved += len(ph.hand.cards)
        self.discard_count += moved
        self._refresh_info_panel()
        return moved

    def _finish_round(self, dealer_blackjack: bool) -> None:
        self._disable_actions()
        self.in_round = False

        # Insurance resolution
        if self.insurance_bet:
            if dealer_blackjack:
                payout = self.insurance_bet * 2
                self.bankroll += self.insurance_bet + payout
                self._update_status(f"Insurance wins {payout}.")
            else:
                self._update_status(f"Insurance loses {self.insurance_bet}.")

        dealer_val = self.dealer.value()
        dealer_bust = self.dealer.is_bust()

        total_net = 0
        outcome_msgs = []

        for idx, ph in enumerate(self.player_hands, start=1):
            player_val = ph.hand.value()
            base = ph.bet * (2 if ph.doubled else 1)
            delta = 0
            outcome = ""

            if dealer_blackjack:
                if ph.hand.is_blackjack():
                    outcome = "Push vs dealer blackjack."
                    delta = base
                else:
                    outcome = "Lose (dealer blackjack)."
                    delta = 0
            else:
                if ph.hand.is_blackjack():
                    win = int(ph.bet * 1.5)
                    outcome = f"Blackjack! Win {win}."
                    delta = ph.bet + win
                elif ph.hand.is_bust():
                    outcome = "Bust. Lose."
                    delta = 0
                elif dealer_bust:
                    outcome = f"Dealer busts. Win {base}."
                    delta = base * 2
                else:
                    if player_val > dealer_val:
                        outcome = f"Win {base}."
                        delta = base * 2
                    elif player_val < dealer_val:
                        outcome = "Lose."
                        delta = 0
                    else:
                        outcome = "Push."
                        delta = base

            self.bankroll += delta
            total_net += (delta - base)
            outcome_msgs.append(f"Hand {idx}: {player_val} vs Dealer {dealer_val} -> {outcome}  (net {'+' if delta - base >= 0 else ''}{delta - base})")

        if total_net > 0:
            self.outcome_var.set(f"✅ You WIN this round: +{total_net}")
            self.outcome_lbl.config(bg="#bbf7d0")
        elif total_net < 0:
            self.outcome_var.set(f"❌ You LOSE this round: {total_net}")
            self.outcome_lbl.config(bg="#fecaca")
        else:
            self.outcome_var.set("➖ PUSH this round")
            self.outcome_lbl.config(bg="#fde68a")

        for msg in outcome_msgs:
            self._toast(msg)

        self._refresh_bankroll()
        self._draw_table(hide_dealer_hole=False)

        # Keep cards until next deal; enable Deal
        self.round_complete = True
        self.deal_btn.config(state="normal")

        self.pl_points.append(self.bankroll)
        self._draw_pl_chart()

        if self.bankroll < self.min_bet:
            messagebox.showinfo("Game Over", f"You're below the minimum bet ({self.min_bet}). Cashing out: {self.bankroll}")
        else:
            self._update_status("Round complete. Press Deal for the next hand.")
        # Remove hint highlight after round
        self._highlight_buttons(None)

    def _toast(self, text: str) -> None:
        self.msg_var.set(text)
        self.after(3500, lambda: self.msg_var.set(""))

