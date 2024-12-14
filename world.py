import pygame
import random
from Actions.pathfinder import Pathfinder
from Render.table import Table
from Customers.customer import Customer
from Agents.servo_agent import ServoAgent
from Customers.customer_fsm import CustomerState
from Actions.goap_servo import ServoGOAPPlanner
from constants import CUSTOMER_RANDOM_SPAWN_RATE, HEIGHT, MAX_TICKS, NUM_SERVOS, SERVO_COLORS, SERVO_WAGE, SIM_SECONDS_PER_TICK, TILE_SIZE, WIDTH

class World:
    def __init__(self, num_servos=NUM_SERVOS, seed=None, render=True):
        # ─── Seed the RNG for reproducibility ────────────────────────────
        if seed is not None:
            random.seed(seed)
            
        print("[World] Initializing...")
        pygame.init()
        pygame.font.init()
        
        # Only create screen if rendering is enabled
        self.render = render
        if render:
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
            pygame.display.set_caption("DinnerAutoDashhhh (D-Stage)")
            # Initialize fonts
            self.font_status = pygame.font.SysFont(None, 24)
            self.font_kitchen = pygame.font.SysFont(None, 32)
            self.font_window = pygame.font.SysFont(None, 24)
            self.font_legend = pygame.font.SysFont(None, 16)
            self.font_sat = pygame.font.SysFont(None, 18)
        else:
            # Create a dummy surface for non-rendering mode
            self.screen = pygame.Surface((WIDTH, HEIGHT))

        # ─── GRID / PIXEL SETUP ──────────────────────────────────────────────
        self.width = WIDTH
        self.height = HEIGHT
        self.cell_size = TILE_SIZE  # Size of each grid cell in pixels
        self.grid_width = self.width // self.cell_size
        self.grid_height = self.height // self.cell_size
        
        # ─── SIMULATION STATE ───────────────────────────────────────────────
        self.tick_count = 0
        self.max_ticks = MAX_TICKS
        self.next_spawn_tick = CUSTOMER_RANDOM_SPAWN_RATE
        
        # Accumulator in "real seconds" so we know when 1 in-game minute has passed
        self._sim_time_acc = 0.0
        # How many real seconds = 1 in-game minute (simulation tick)
        self.SIM_SECONDS_PER_TICK = SIM_SECONDS_PER_TICK  # 1 in-game minute = 0.5 real seconds

        # ─── CREATE TABLES (grid coords) ───────────────────────────────────────
        print("[World] Creating tables...")
        self.tables = []
        table_positions = [
            (3, 3), (5, 3), (7, 3),  # Top row
            (3, 5), (5, 5), (7, 5)   # Bottom row
        ]
        for (gx, gy) in table_positions:
            pos = self.grid_to_pixel(gx, gy)
            t = Table(center=pos)
            t.occupied = False
            t.id = (gx, gy)
            self.tables.append(t)
        
        print(f"[World] Created tables at: {[tuple(t.center) for t in self.tables]}")

        # ─── INITIAL CUSTOMER ─────────────────────────────────────────────────
        print("[World] Creating initial customer...")
        self.customers = []
        self.spawn_customer()

        # ─── BUILD NAV GRID FOR A* & GOAP ─────────────────────────────────────
        print("[World] Creating navigation grid...")
        self.nav_grid = [[0 for _ in range(self.grid_height)] for _ in range(self.grid_width)]
        self.update_nav_grid()

        print("[World] Creating pathfinder...")
        self.pathfinder = Pathfinder(self)

        print("[World] Creating GOAP planner...")
        self.goap = ServoGOAPPlanner(self)
        
        # ─── PYGAME CLOCK ─────────────────────────────────────────────────────
        self.clock = pygame.time.Clock()

        # ─── ADD BUSINESS COST & SERVO ───────────────────────────────────────
        self.profit = 500
        self.num_servos = num_servos
        self.servos = []
        for i in range(num_servos):
            servo = ServoAgent(self, self.goap, self.pathfinder)
            # give it a color based on its index
            servo.color = SERVO_COLORS[i % len(SERVO_COLORS)]
            self.servos.append(servo)
                
        # ─── TRACK COMPLETED CUSTOMERS FOR ANALYSIS ─────────────────────────
        self.completed_customers: list[Customer] = []
        
        # Create food window
        from types import SimpleNamespace
        self.food_window = SimpleNamespace(center=pygame.math.Vector2(520, 120))
        
        # Define walls for avoidance behavior
        self.walls = self._create_walls()
        self.obstacles = self.tables # Start with tables as static obstacles

        print("[World] Initialization complete.")

    def get_obstacles(self, agent_to_exclude):
        """Returns a list of all dynamic and static obstacles, excluding the agent itself."""
        # Other servos
        other_agents = [agent for agent in self.servos if agent is not agent_to_exclude]
        # Seated customers (treat them as temporary obstacles)
        seated_customers = [cust for cust in self.customers if cust.fsm.current == CustomerState.SEATED]
        
        # Combine all obstacles
        return self.tables + other_agents + seated_customers

    def _create_walls(self):
        """Creates a list of wall line segments for wall avoidance."""
        walls = []
        # Top, Bottom, Left, Right
        walls.append((pygame.math.Vector2(0, 0), pygame.math.Vector2(self.width, 0)))
        walls.append((pygame.math.Vector2(0, self.height), pygame.math.Vector2(self.width, self.height)))
        walls.append((pygame.math.Vector2(0, 0), pygame.math.Vector2(0, self.height)))
        walls.append((pygame.math.Vector2(self.width, 0), pygame.math.Vector2(self.width, self.height)))
        return walls

    def grid_to_pixel(self, gx: int, gy: int):
        """Convert grid coordinates to pixel coordinates (center of cell)."""            
        # Clamp grid coordinates to valid range
        gx = max(0, min(gx, self.grid_width - 1))
        gy = max(0, min(gy, self.grid_height - 1))
        # Convert to pixel coordinates (center of cell)
        px = (gx + 0.5) * self.cell_size
        py = (gy + 0.5) * self.cell_size
        return pygame.math.Vector2(px, py)

    def pixel_to_grid(self, pixel_pos):
        """Convert pixel coordinates to grid coordinates."""
        if isinstance(pixel_pos, tuple):
            px, py = pixel_pos
        else:
            px, py = pixel_pos.x, pixel_pos.y
            
        # Convert to grid coordinates
        gx = int(px / self.cell_size)
        gy = int(py / self.cell_size)
        
        # Clamp to valid grid range
        gx = max(0, min(gx, self.grid_width - 1))
        gy = max(0, min(gy, self.grid_height - 1))
        
        return (gx, gy)

    def grid_position_for_table(self, table) -> tuple[int, int]:
        """Get the grid cell containing this table's center."""
        return self.pixel_to_grid(table.center)

    def update_nav_grid(self):
        """Mark edges/kitchen/food window/queue as walkable or blocked."""
        # 1) Reset grid (0 = walkable, 1 = blocked)
        for x in range(self.grid_width):
            for y in range(self.grid_height):
                self.nav_grid[x][y] = 0
                
        # 2) Edges (GUI window size) is blocked
        for x in range(self.grid_width):
            self.nav_grid[x][0] = 1  # Top edge
            self.nav_grid[x][self.grid_height-1] = 1  # Bottom edge
        for y in range(self.grid_height):
            self.nav_grid[0][y] = 1  # Left edge
            self.nav_grid[self.grid_width-1][y] = 1  # Right edge
            
        # 3) Kitchen area - row 0 to 1 (y=0 to y=1) is walkable
        for x in range(1, self.grid_width-1):
            self.nav_grid[x][0] = 0  
            self.nav_grid[x][1] = 0  
            
        # 4) Food window area - row 2 (y=2) is walkable
        for x in range(3, self.grid_width-1):  
            self.nav_grid[x][2] = 0  
            
        # 5) Customer queue is col 1 (x=1, just under food window) is walkable
        for y in range(2, self.grid_height-1):
            self.nav_grid[1][y] = 0 
            
        # 6) Tables: only mark the eight neighbors WALKABLE so the servo can approach.
        for table in self.tables:
            gx, gy = self.pixel_to_grid(table.center)
            # ───── Block the table's own grid cell ─────
            self.nav_grid[gx][gy] = 1
            print(f"[DEBUG] Blocking table cell at grid {(gx,gy)}")

            # Mark cells around table as walkable
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    nx, ny = gx + dx, gy + dy
                    if 0 <= nx < self.grid_width and 0 <= ny < self.grid_height:
                        if dx != 0 or dy != 0:  # If it's not the table's own cell, force it to be walkable
                            self.nav_grid[nx][ny] = 0
                        # If it's not the table's own center, force it to be walkable
                        if not (dx == 0 and dy == 0):
                            self.nav_grid[nx][ny] = 0

    # ─── SIMULATION TICK (advance "1 in-game minute") ─────────────────────────
    def _do_one_simulation_tick(self):
        """All the logic that used to live in your old updateAll(), *except* servo movement."""
        self.tick_count += 1

        # ─── (A) SPAWN NEW CUSTOMER ──────────────────────────────────────
        if self.tick_count == self.next_spawn_tick and self.tick_count <= self.max_ticks:
            self.spawn_customer()

        # ─── (B) UPDATE EACH CUSTOMER'S FSM & TIMERS ──────────────────────
        for cust in self.customers:
            cust.update()
                
        # (C) RUN GOAP → ASSIGN A PLAN TO EACH SERVO
        for idx, servo in enumerate(self.servos):
            # Update obstacle list for the servo
            servo.obstacles = self.get_obstacles(servo)
            if servo.executing:
                print(f"Servo#{idx} already busy")
                continue
            new_plan = self.goap.compute_plan(servo)
            print(f"Servo#{idx} plan → {new_plan}")
            
            if new_plan is None:
                continue

            # block double–pickups
            if not servo.actions_equal(new_plan, servo.current_action):
                servo.start_new_plan(new_plan)

        # ─── (D) MOVE SERVOS ALONG THEIR WAYPOINTS ────────────────────────────────────
        for servo in self.servos:
            servo.move(self.SIM_SECONDS_PER_TICK)

        # ─── (E) DEDUCT STAFF WAGE COST ────────────────────────────────────
        self.profit -= SERVO_WAGE / 60.0 * self.num_servos
        
        # ─── (F) Record and remove any customers who are marked_for_removal ──────────
        for cust in list(self.customers):
            if getattr(cust, "marked_for_removal", False):
                # if they ate, they still count as "served"
                self.completed_customers.append(cust)
                # remove from active list
                self.customers.remove(cust)

    def spawn_customer(self):
        """Create a new customer."""
        # Calculate queue position
        waiting_list = [
            c for c in self.customers
            if not c.arrived and not c.marked_for_removal
        ]
        queue_size = len(waiting_list)
        queue_y = 180 + queue_size * 60  # Space customers 60 pixels apart vertically
        
        # Create customer at queue position
        customer = Customer(
            world=self,
            spawn_tick=self.tick_count,
            group_size=1
        )
        customer.position = pygame.math.Vector2(100, queue_y)
        self.customers.append(customer)
        print(f"[World] Spawned Customer#{customer.spawn_tick} at queue y={queue_y}")
        
        # Set next spawn time
        self.next_spawn_tick = self.tick_count + CUSTOMER_RANDOM_SPAWN_RATE
        print(f"[World] Next spawn at tick {self.next_spawn_tick}")
        
        return customer

    def drawAll(self):
        """Draw all game objects to the screen."""
        if not self.render:
            return
            
        print(f"[World] Tick {self.tick_count:03d}: drawAll()")
        
        # 1) Fill background
        self.screen.fill((249, 247, 237))

        # 2) Draw status bar (dark gray)
        pygame.draw.rect(self.screen, (64, 64, 64), pygame.Rect(0, 0, WIDTH, 40))
        tick_text = self.font_status.render(f"Tick: {self.tick_count}/{self.max_ticks}", True, (255, 255, 255))
        self.screen.blit(tick_text, (20, 10))
        
        profit_text = self.font_status.render(f"Profit: ${int(self.profit)}", True, (255,255,255))
        self.screen.blit(profit_text, (200, 10))


        # 3) Draw KITCHEN bar (pale pink)
        pygame.draw.rect(self.screen, (255, 246, 250), pygame.Rect(0, 40, WIDTH, 40))
        kitchen_text = self.font_kitchen.render("KITCHEN", True, (0, 0, 0))
        self.screen.blit(kitchen_text, (WIDTH // 2 - kitchen_text.get_width() // 2, 60 - 16))

        # 4) Draw FOOD WINDOW (off-white)
        pygame.draw.rect(self.screen, (250, 240, 240), pygame.Rect(200, 80, WIDTH-200, 40))
        food_text = self.font_window.render("FOOD WINDOW", True, (0, 0, 0))
        self.screen.blit(food_text, (WIDTH // 2 - food_text.get_width() // 2, 100 - 12))

        # 5) Draw left queue panel (light yellow)
        pygame.draw.rect(self.screen, (255, 247, 231), pygame.Rect(0, 120, 200, HEIGHT-120))
        pygame.draw.rect(self.screen, (64, 64, 64), pygame.Rect(0, 120, 200, HEIGHT-120), 2)
        
        # Draw legend text at top of queue panel
        legend_lines = [
            "1 tick = 1 min",
            "Wait time:",
            "  10 mins: UNHAPPY (yellow)",
            "  20 mins: ANGRY (orange)",
            "  30 mins: LEAVING (red)",

        ]
        for i, line in enumerate(legend_lines):
            legend = self.font_legend.render(line, True, (0, 0, 0))
            self.screen.blit(legend, (10, 42 + i*15))

        #  6) Now draw each table on top of that overlay
        for table in self.tables:
            table.draw(self.screen)
            
        # 7) Draw ALL customers (both waiting and seated)
        waiting_count = 0
        for cust in self.customers:
            if cust.fsm.current in (CustomerState.WAITING,
                                    CustomerState.UNHAPPY,
                                    CustomerState.ANGRY):
                # Position in queue
                queue_x = 100
                queue_y = 180 + waiting_count * 60
                cust.position = pygame.math.Vector2(queue_x, queue_y)
                waiting_count += 1
            cust.draw(self.screen)

        # 8) Draw ALL servos LAST so they remain on top
        for idx, servo in enumerate(self.servos):
            servo.color = SERVO_COLORS[idx % len(SERVO_COLORS)]
            servo.draw(self.screen)
                
        pygame.display.flip()

    # ─── MAIN LOOP ──────────────────────────────────────────────────────────
    def run(self):
        running = True
        while running:
            # (1) Pygame events
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False

            # (2) Figure out how much real time has passed
            dt = self.clock.tick(10) / 1000.0
            #   dt is in seconds. If you run at ~60 FPS, dt ~ 0.0167.

            # (3) Accumulate until we hit 1 simulation tick
            self._sim_time_acc += dt
            while self._sim_time_acc >= self.SIM_SECONDS_PER_TICK:
                # Advance exactly one in-game minute:
                self._do_one_simulation_tick()
                self._sim_time_acc -= self.SIM_SECONDS_PER_TICK

            # (4) Move all servos smoothly (every frame):
            for servo in self.servos:
                servo.move(dt)

            # (5) Draw everything (this also shows newly updated customers/tables):
            if self.render:
                self.drawAll()

        pygame.quit()

    def update_queue_positions(self):
        """Update the positions of customers in the queue."""
        # Get list of customers in queue (not seated or leaving)
        waiting_list = [
            c for c in self.customers
            if not c.arrived and not c.marked_for_removal
        ]
        
        # Update each customer's position in queue
        for i, customer in enumerate(waiting_list):
            target_y = 180 + i * 60  # Space customers 60 pixels apart vertically
            # Smoothly move towards target position
            current_y = customer.position.y
            dy = target_y - current_y
            if abs(dy) > 1:
                customer.position.y += dy * 0.2  # Move 20% of the way there
            else:
                customer.position.y = target_y

    def update(self):
        """Called every simulation tick."""
        # Update all customers
        for customer in self.customers:
            customer.update()

        # Update queue positions
        self.update_queue_positions()

        # Remove customers marked for removal
        self.customers = [c for c in self.customers if not c.marked_for_removal]

        # Update servos
        for servo in self.servos:
            servo.update()

        # Spawn new customer if it's time
        if self.tick_count >= self.next_spawn_tick:
            self.spawn_customer()

        # Increment tick counter
        self.tick_count += 1










