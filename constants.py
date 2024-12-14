# constants.py
# ─────────────────────────────────────────────────────────────────────────────
# All game settings are here, so we can easily change them in one place :)

from enum import Enum
import random


class CustomerState(Enum):
    WAITING = 1
    UNHAPPY = 2    # after 10 ticks (10 minutes)
    ANGRY   = 3    # after 20 ticks (20 minutes)
    SEATED  = 4
    ORDERED = 5
    EATING  = 6
    LEAVING = 7
    
# ─── WORLD ───────────────────────────────────────────────────────────────
WIDTH = 800
HEIGHT = 600
MAX_TICKS = 250
SIM_SECONDS_PER_TICK = 0.2  # 1 in-game minute = 0.2 real seconds
CUSTOMER_RANDOM_SPAWN_RATE = 5 # or random.randint(2, 7) 

# ─── SERVO ───────────────────────────────────────────────────────────────
NUM_SERVOS = 3
SERVO_WAGE = 20
SERVO_COLORS = [
    (255, 255,   0),   # servo #1 = yellow
    (  0, 200, 255),   # servo #2 = cyan
    (118, 128, 191),   # servo #3 = violet,
    (255, 128, 128)    # servo #4 = light red
]

# ─── GRID / TIMING ────────────────────────────────────────────────────────────
TILE_SIZE      = 80      # pixels per grid‐cell (world.py uses this to convert grid ↔ pixel)
TICKS_PER_MIN  = 1       # 1 tick = 1 minute of simulated "in‐game" time

# ─── CUSTOMER WAIT TIME THRESHOLDS (in ticks) ───────────────────────────────
UNHAPPY_TICKS  = 10      # at 10 ticks waiting, customer goes from "Waiting" → "Angry/Unhappy"
ANGRY_TICKS    = 20      # at 20 ticks waiting (still no seat), customer remains ANGRY
LEAVE_TICKS    = 30      # at 30 ticks, customer's satisfaction → 0 and they LEAVE

# ─── SERVO MOVEMENT ──────────────────────────────────────────────────────────
# We want the servo to traverse exactly one TILE_SIZE (80 pixels) per tick,
# so that each cell–to–cell move takes "1 minute" (given our 1 tick=1 min).
SERVO_INITIAL_POSITION = (9, 6)
SERVO_SPEED_PIXELS_PER_TICK = 720

# ─── CUSTOMER SATISFACTION ADJUSTMENTS ───────────────────────────────────────
INITIAL_SATISFACTION = 50 # initial (for reference)
SAT_DECREASE_UNHAPPY = 35  # as soon as wait_time == UNHAPPY_TICKS
SAT_ANGRY_VALUE     = 15  # as soon as wait_time == ANGRY_TICKS
SAT_LEAVE_VALUE     = 0   # as soon as wait_time >= LEAVE_TICKS

# ─── FOOD WINDOW GRID LOCATION ──────────────────────────────────────────────
# (unchanged from original GOAPPlanner, but pulled here for easy tuning)
FOOD_WINDOW_CELL   = (6, 1) 

