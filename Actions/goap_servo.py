from Customers.customer_fsm import CustomerState
from constants import FOOD_WINDOW_CELL
import pygame

class ServoGOAPPlanner:
    """
    Goal-Oriented Action Planning (GOAP) for the restaurant simulation.
    """
    def __init__(self, world):
        """Initialize the GOAP planner."""
        self.world = world
        self.FOOD_WINDOW_POS = pygame.math.Vector2(520, 120)
        print(f"[GOAP] Food window at grid={FOOD_WINDOW_CELL}, pixel={tuple(self.FOOD_WINDOW_POS)}")
        
    def compute_plan(self, servo):
        """
        servo: the ServoAgent that is asking for a new plan.
        """
        # 1) If carrying a dish, go deliver it
        if servo.carrying is not None:
            cust = servo.carrying
            print(f"[GOAP] → DeliverDish for Customer#{cust.spawn_tick}")
            return ("DeliverDish", cust, cust.target_table)

        # 2) If any customer is ORDERED and order_ready, pick up from FOOD WINDOW
        ready_customers = [
            c for c in self.world.customers
            if c.fsm.current == CustomerState.ORDERED and c.order_ready and not c.order_claimed
        ]
        if ready_customers:
            # Sort by wait time to prioritize customers who have waited longer
            ready_customers.sort(key=lambda c: c.wait_time, reverse=True)
            target_cust = ready_customers[0]
            target_cust.order_claimed = True
            print(f"[GOAP] → PickUpDish for Customer#{target_cust.spawn_tick}")
            return ("PickUpDish", target_cust, self.world.food_window)

        # 3) If any tables are free and there are waiting customers, seat them
        waiting_customers = [
            c for c in self.world.customers
            if c.fsm.current in (CustomerState.WAITING, CustomerState.UNHAPPY, CustomerState.ANGRY)
            and not c.seat_assigned
        ]
        if waiting_customers:
            # Get list of free tables
            free_tables = [t for t in self.world.tables if not t.occupied]
            print(f"[GOAP] Found {len(waiting_customers)} WAITING/ANGRY customers")
            print(f"[GOAP] Free tables right now: {[tuple(t.center) for t in free_tables]}")
            
            if free_tables:
                # Sort customers by wait time to prioritize those who have waited longer
                waiting_customers.sort(key=lambda c: c.wait_time, reverse=True)
                target_cust = waiting_customers[0]
                target_table = free_tables[0]
                target_table.occupied = True
                target_cust.seat_assigned = True
                target_cust.target_table = target_table
                print(f"[GOAP] → SeatCustomer for Customer#{target_cust.spawn_tick}")
                return ("SeatCustomer", target_cust, target_table)
            else:
                print("[GOAP] → No action")
                return None

        # 4) No action needed
        return None
