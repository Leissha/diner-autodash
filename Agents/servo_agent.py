import pygame
from Actions.steering import SteeringBehavior
from Customers.customer_fsm import CustomerState

from constants import SERVO_INITIAL_POSITION, SERVO_SPEED_PIXELS_PER_TICK, TILE_SIZE
from constants import FOOD_WINDOW_CELL

class ServoAgent:
    def __init__(self, world, planner, pathfinder):
        """
        Initialize the servo so that:
          1) We start on a valid grid cell  (e.g. (9,6))
          2) We only use world.grid_to_pixel(gx, gy) ↔ world.pixel_to_grid(vec2).
        """
        self.world = world
        self.planner = planner
        self.pathfinder = pathfinder
        self.color = (255, 255, 0)  # default to yellow
        
        # 1) Start position (pixel coords) near top-middle kitchen area
        self.position = self.world.grid_to_pixel(SERVO_INITIAL_POSITION[0], SERVO_INITIAL_POSITION[1])
        self.velocity = pygame.math.Vector2(0, 0)
        self.heading = pygame.math.Vector2(0, -1) # Start facing up
        self.side = self.heading.rotate(90)
        self.radius = 12 # For obstacle avoidance checks
        
        # 2) Maximum speed/force (in pixels per second)
        self.max_speed = SERVO_SPEED_PIXELS_PER_TICK  # px/sec
        self.max_force = SERVO_SPEED_PIXELS_PER_TICK * 1.5  # px/sec²
        
        # 3) Path‐following state
        self.waypoints = []   # list[Vector2] in pixel coords
        self.waypoint_index = 0
        self.waypoint_threshold = TILE_SIZE  
        
        # 4) Current GOAP action
        self.current_action = None #  e.g. ("SeatCustomer", cust, table) or ("PickUpDish", cust, table), etc.
        self.carrying = None  # Customer whose dish we're carrying
        self.executing = False  # prevents mid-action re-planning
        self.obstacles = [] # List of obstacles from the world
        
        print(f"[Servo] Created at pos={tuple(self.position)}")

    # ────────────────────────────────────────────────────────────────────
    def start_new_plan(self, plan):
        """
        Called once per simulation tick if GOAP's plan changes. 
        We convert A* grid cells → pixel waypoints so that move(dt) 
        can just interpolate every frame.
        """

        # If there is no plan, clear everything and return.
        if plan is None:
            self.current_action = None
            self.executing = False
            self.waypoints = []
            self.waypoint_index = 0
            return

        # If the plan is the same as before, do nothing.
        if plan == self.current_action:
            return

        # We are truly starting a brand‐new plan:
        self.current_action = plan
        self.velocity = pygame.math.Vector2(0, 0)

        action_type, cust, table = plan

        
        # ─── 1) Find the "delivery cell" (grid‐coords) adjacent to this table ───
        
        # First, figure out the table's grid coordinate:
        tgx, tgy = self.world.pixel_to_grid(table.center)

        # 1) Find a "delivery cell" next to the target table
        tgx, tgy = self.world.pixel_to_grid(table.center)
        delivery_cell = None
        for dx, dy in [(0, +1), (0, -1), (+1, 0), (-1, 0)]:
            nx, ny = tgx + dx, tgy + dy
            if (0 <= nx < self.world.grid_width 
                and 0 <= ny < self.world.grid_height 
                and self.world.nav_grid[nx][ny] == 0):
                delivery_cell = (nx, ny)
                break

        if delivery_cell is None:
            # (This should never happen if you've marked neighbor cells as walkable in update_nav_grid())
            print(f"[Servo][ERROR] Could NOT find a free delivery cell next to table at {tgx,tgy}")
            self.executing = False
            return

        # 2) Choose goal_cell based on action_type
        if action_type == "PickUpDish":
            # In this lab, "food window" is at a known cell:
            goal_cell = FOOD_WINDOW_CELL  
        else:   # "SeatCustomer" or "DeliverDish"
            goal_cell = delivery_cell
    
        print(f"[Servo][DEBUG] goal_cell = {goal_cell}, walkable? {self.world.nav_grid[goal_cell[0]][goal_cell[1]]}")

        # 3): compute current grid cell:
        start_cell = self.grid_position()
        print(f"[Servo] Generating waypoints for {action_type} from {start_cell} → {goal_cell}")

        # 4) Run A* on the nav_grid to get a list of pixel‐center Vector2 waypoints.
        self.waypoints = self.pathfinder.find_path(start_cell, goal_cell)
        print(f"[Servo][DEBUG] goal_cell = {goal_cell}, walkable? {self.world.nav_grid[goal_cell[0]][goal_cell[1]]}")

        # 5) If A* returned at least one waypoint, we are now "executing"
        if self.waypoints:
            self.executing = True
            self.waypoint_index = 0
            print(f"[Servo] New waypoints: {[tuple(w) for w in self.waypoints]}")
        else:
            print(f"[Servo][ERROR] A* could not find path from {start_cell} to {goal_cell}")
            self.executing = False
            
    def move(self, dt):
        """
        Called every render frame with dt = real seconds since last frame.
        We integrate velocity/position toward the current waypoint in pixel space.
        """
        # 1) If we have no plan, do nothing.
        if not self.executing or self.current_action is None:
            self.velocity *= 0.95 # Apply some friction to stop
            if self.velocity.length() < 0.1:
                self.velocity.update(0,0)
            self.position += self.velocity * dt
            return

        # --- COMBINE STEERING FORCES ---
        force = pygame.math.Vector2(0, 0)
        
        # 1. Path Following Force (Seek/Arrive)
        path_force = pygame.math.Vector2(0, 0)
        if self.waypoint_index < len(self.waypoints):
            target = self.waypoints[self.waypoint_index]
            dist = self.position.distance_to(target)

            if self.waypoint_index == len(self.waypoints) - 1 and dist < self.waypoint_threshold * 1.5:
                path_force = SteeringBehavior.arrive(
                    self.position, target, self.max_speed, self.velocity, slow_radius=self.waypoint_threshold
                )
            else:
                path_force = SteeringBehavior.seek(
                    self.position, target, self.max_speed, self.velocity
                )
        
        # 2. Wall Avoidance Force
        wall_force = SteeringBehavior.wall_avoidance(self, self.world.walls)

        # 3. Obstacle Avoidance Force
        obstacle_force = SteeringBehavior.obstacle_avoidance(self)
        
        # --- WEIGHTED SUM OF FORCES ---
        # Adjust weights to prioritize avoidance
        force += path_force * 1.0
        force += wall_force * 3.0
        force += obstacle_force * 5.0

        # --- APPLY FINAL FORCE ---
        # Cap the steering force
        if force.length() > self.max_force:
            force.scale_to_length(self.max_force)

        # Apply the force to the velocity
        self.velocity += force * dt
        
        # Cap the velocity to max_speed
        if self.velocity.length() > self.max_speed:
            self.velocity.scale_to_length(self.max_speed)
            
        # Update heading to match velocity
        if self.velocity.length_squared() > 0:
            self.heading = self.velocity.normalize()
            self.side = self.heading.rotate(90)

        # Update position based on the new velocity
        self.position += self.velocity * dt

        # --- WAYPOINT LOGIC ---
        if self.waypoint_index < len(self.waypoints):
            dist_to_wp = self.position.distance_to(self.waypoints[self.waypoint_index])
            if dist_to_wp < self.waypoint_threshold:
                self.waypoint_index += 1
                if self.waypoint_index >= len(self.waypoints):
                    self.execute_current_action()
        else:
            if self.executing:
                self.execute_current_action()

    def execute_current_action(self):
        """When the servo finally reaches the last waypoint, carry out the action itself."""
        if self.current_action is None:
            return

        action_type, cust, table = self.current_action

        if action_type == "SeatCustomer":
            cust.fsm.current = CustomerState.SEATED
            cust.target_table = table
            cust.seat_assigned = True
            cust.satisfaction = min(cust.satisfaction + 15, 100) # AWARD +15 for "just got seated" 
            cust.seat_tick = self.world.tick_count
            print(f"[Servo] Seating Customer#{cust.spawn_tick} → +15 sat → now {cust.satisfaction}")


        elif action_type == "PickUpDish":
            print(f"[Servo] Picking up dish for Customer#{cust.spawn_tick}")
            self.carrying = cust

        elif action_type == "DeliverDish":
            print(f"[Servo] Delivering dish to Customer#{cust.spawn_tick}")
            cust.fsm.current = CustomerState.EATING
            cust.order_delivered = True
            self.carrying = None
            
            # ─── AWARD +15 for "just began eating" ───
            cust.satisfaction = min(cust.satisfaction + 15, 100)
            print(f"[Servo] Customer#{cust.spawn_tick} now EATING → +15 sat → now {cust.satisfaction}")


        # Clear so we re-plan next simulation tick
        self.current_action = None
        self.waypoints = []
        self.waypoint_index = 0
        self.executing = False
        
    def actions_equal(self, a1, a2):
        """Compare if current GOAP action is the same as the next one so we don't re‐plan unnecessarily."""
        if a1 is None and a2 is None:
            return True
        if (a1 is None) or (a2 is None):
            return False
        # Compare tuple‐unpacked form: (action_name, Customer, Table)
        return (a1[0] == a2[0] and a1[1] is a2[1] and a1[2] is a2[2])
    
    def grid_position(self):
        """Get the current grid‐cell (gx, gy) that contains our pixel position."""
        return self.world.pixel_to_grid(self.position)

    def draw(self, screen: pygame.Surface):
        """
        Draw the servo as a solid yellow circle at self.position (Vector2),
        plus draw each waypoint as a small gray dot so we can see the path.
        """
        # 1) Draw the servo itself
        pygame.draw.circle(
            screen,
            self.color,                
            (int(self.position.x), int(self.position.y)),
            12
        )

        # 2) Draw each waypoint (for debugging) as a small gray circle
        for wp in self.waypoints:
            pygame.draw.circle(
                screen,
                (204, 192, 201), 
                (int(wp.x), int(wp.y)),
                4
            )
        
        # 3) Draw heading and feelers for debugging
        if self.velocity.length() > 0:
            # Heading line
            pygame.draw.line(screen, (0, 255, 0), self.position, self.position + self.heading * 25, 2)
            # Feeler lines
            feeler_len = 50.0
            pygame.draw.line(screen, (255, 0, 255), self.position, self.position + self.heading.rotate(-45) * feeler_len, 1)
            pygame.draw.line(screen, (255, 0, 255), self.position, self.position + self.heading.rotate(45) * feeler_len, 1)

    def compute_waypoints(self, action):
        """Compute waypoints for the given action."""
        if action is None:
            return []

        action_type, cust, table = action
        
        # Get current grid position
        start_grid = self.world.pixel_to_grid(self.position)
        
        if action_type == "PickUpDish":
            # Path to food window
            print(f"[Servo] Computing path from {start_grid} to {FOOD_WINDOW_CELL} for PickUpDish")
            path = self.pathfinder.find_path(start_grid, FOOD_WINDOW_CELL)
            if not path:
                print(f"[Servo] No path found from {start_grid} to {FOOD_WINDOW_CELL}")
            return path
            
        elif action_type == "DeliverDish":
            # Path from current position to table
            table_grid = self.world.pixel_to_grid(table.position)
            print(f"[Servo] Computing path from {start_grid} to {table_grid} for DeliverDish")
            path = self.pathfinder.find_path(start_grid, table_grid)
            if not path:
                print(f"[Servo] No path found from {start_grid} to {table_grid}")
            return path
            
        return []