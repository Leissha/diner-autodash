import pygame
from .customer_fsm import CustomerFSM, CustomerState
from constants import UNHAPPY_TICKS, ANGRY_TICKS, LEAVE_TICKS
from constants import SAT_DECREASE_UNHAPPY, SAT_ANGRY_VALUE, SAT_LEAVE_VALUE

class Customer:
    next_id = 1

    def __init__(self, world, spawn_tick, group_size=1):
        """Initialize a new customer."""
        self.world = world
        self.spawn_tick = spawn_tick
        self.position = pygame.math.Vector2(100, 480)  # Start in queue
        self.fsm = CustomerFSM()
        self.satisfaction = 50  # Start at 50% satisfaction
        self.wait_time = 0
        self.arrived = False
        self.seat_assigned = False
        self.eating_time = 0
        self.eating_duration = 10  # Takes 10 ticks to eat
        self.finished_eating = False
        self.marked_for_removal = False
        self.profit_calculated = False  # Track if profit has been calculated

        # Assign and increment ID
        self.id = Customer.next_id
        Customer.next_id += 1

        # ─── Dish preparation fields ────────────────────────────────
        self.dish_timer = 5        # "minutes" to prepare
        self.order_timer_started = False
        self.has_received_food = False
        self.order_ready = False
        self.order_claimed = False  # Track if a servo has claimed this order

        # track the table if/when seated
        self.target_table = None
        self.group_size = group_size

    def update(self):
        """Called every simulation tick."""
        # 1) Update wait time if not seated
        if not self.arrived:
            self.wait_time += 1

        # 2) Update FSM state
        self.fsm.step(self)

        # 3) Update position if seated at a table
        if self.target_table and not self.arrived:
            target_pos = pygame.math.Vector2(self.target_table.center)
            diff = target_pos - self.position
            if diff.length() > 1:
                # Move 20% of the remaining distance each tick
                self.position += diff * 0.8
            else:
                self.position = target_pos
                self.arrived = True

        # 4) If ORDERED, start dish timer
        if self.fsm.current == CustomerState.ORDERED:
            if not self.order_timer_started:
                self.order_timer_started = True
                print(f"[Customer#{self.spawn_tick}] SEATED→ORDERED  (starting order timer)")
            elif not self.order_ready:
                self.dish_timer -= 1
                print(f"[Customer#{self.spawn_tick}] Dish timer: {self.dish_timer}")
                if self.dish_timer <= 0:
                    self.order_ready = True
                    print(f"Customer#{self.spawn_tick}: order_ready = True")

        # 5) If EATING, update eating time
        if self.fsm.current == CustomerState.EATING:
            self.eating_time += 1
            print(f"[Customer#{self.spawn_tick}] Eating tick {self.eating_time}/{self.eating_duration}")

        # 6) Print debug info
        print(f"[Customer#{self.spawn_tick}] POS CHECK: pos={tuple(self.position)} | FSM={self.fsm.current} | arrived={self.arrived} | seat_assigned={self.seat_assigned} | wait={self.wait_time} | sat={self.satisfaction}")

        # 7) Calculate profit exactly once when customer is done
        if not self.profit_calculated and (self.marked_for_removal or self.fsm.current == CustomerState.LEAVING):
            if self.finished_eating:
                # Customer completed their meal successfully
                self.world.profit += 50  # Base profit for completed meal
                if self.satisfaction >= 30:  # If reasonably satisfied
                    self.world.profit += 10  # Bonus for good satisfaction
            else:
                # Customer left without eating or unhappy
                self.world.profit -= 30  # Penalty for unhappy customer
            
            self.profit_calculated = True
            print(f"[Customer#{self.spawn_tick}] Profit calculated: finished_eating={self.finished_eating}, satisfaction={self.satisfaction}")

    def draw(self, screen):
        # Only draw once spawn_tick has passed
        if self.world.tick_count < self.spawn_tick:
            return

        # ─────────────── Choose color by satisfaction ───────────────
        # (1) If satisfaction <= 0 → RED (very upset or leaving)
        if self.satisfaction <= 0:
            color = (255, 0, 0)      # red

        # (2) Else if satisfaction <= 15 → ORANGE (angry)
        elif self.satisfaction <= 15:
            color = (255, 165, 0)    # orange

        # (3) Else if satisfaction <= 30 → YELLOW (unhappy)
        elif self.satisfaction <= 30:
            color = (255, 255, 0)    # yellow

        # (4) Else → GREEN (happy/neutral)
        else:
            color = (0, 255, 0)      # green
        # ───────────────────────────────────────────────────────────────

        px, py = int(self.position.x), int(self.position.y)
        size = 12

        # Draw the triangle
        pts = [
            (px, py + size),           # bottom vertex
            (px - size, py - size),    # top-left
            (px + size, py - size)     # top-right
        ]
        pygame.draw.polygon(screen, color, pts)

        # Draw the "ID / Sat / State" on two lines under the triangle
        font_obj = pygame.font.SysFont(None, 18)
        text_color = (0, 0, 0)

        status_text = f"Cus: {self.id}\nSat: {self.satisfaction}  {self.fsm.current.name}"
        lines = status_text.split("\n")
        line_height = font_obj.get_linesize()

        for i, line in enumerate(lines):
            line_surf = font_obj.render(line, True, text_color)
            x = px - (line_surf.get_width() // 2)
            y = py + size + 4 + (i * line_height)
            screen.blit(line_surf, (x, y))
