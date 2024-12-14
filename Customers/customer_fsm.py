from constants import UNHAPPY_TICKS, ANGRY_TICKS, LEAVE_TICKS, CustomerState

class CustomerFSM:
    def __init__(self):
        self.current = CustomerState.WAITING

    def step(self, customer):
        """
        Called every simulation tick to update the customer's state.
        """
        # 1) If WAITING → UNHAPPY after 10 ticks
        if self.current == CustomerState.WAITING and customer.wait_time >= 10:
            print(f"Customer#{customer.spawn_tick}: UNHAPPY  (wait_time={customer.wait_time}, sat={customer.satisfaction})")
            self.current = CustomerState.UNHAPPY
            customer.satisfaction = max(0, customer.satisfaction - 20)  # Reduce satisfaction but don't go below 0
            return

        # 2) If UNHAPPY → ANGRY after 20 ticks
        if self.current == CustomerState.UNHAPPY and customer.wait_time >= 20:
            print(f"Customer#{customer.spawn_tick}: ANGRY    (wait_time={customer.wait_time}, sat={customer.satisfaction})")
            self.current = CustomerState.ANGRY
            customer.satisfaction = max(0, customer.satisfaction - 20)  # Further reduce satisfaction
            return

        # 3) If ANGRY → LEAVING after 30 ticks
        if self.current == CustomerState.ANGRY and customer.wait_time >= 30:
            print(f"Customer#{customer.spawn_tick}: LEAVING  (wait_time={customer.wait_time}, sat={customer.satisfaction})")
            self.current = CustomerState.LEAVING
            customer.satisfaction = 0  # Zero satisfaction for angry customers who leave
            customer.marked_for_removal = True
            # Free the table if they had one assigned
            if customer.target_table:
                print(f"[Customer#{customer.spawn_tick}] LEAVING ANGRY → freeing table {tuple(customer.target_table.center)}")
                customer.target_table.occupied = False
                customer.target_table = None
            return

        # 4) If WAITING/UNHAPPY/ANGRY → SEATED when seat_assigned
        if self.current in (CustomerState.WAITING, CustomerState.UNHAPPY, CustomerState.ANGRY) and customer.seat_assigned:
            print(f"[FSM] Customer#{customer.spawn_tick} → WAITING/UNHAPPY/ANGRY → SEATED (seat_assigned)")
            self.current = CustomerState.SEATED
            customer.satisfaction = min(100, customer.satisfaction + 15)  # Bonus for being seated, cap at 100
            return

        # 5) If SEATED → ORDERED (auto-transition)
        if self.current == CustomerState.SEATED:
            print(f"[FSM] Customer#{customer.spawn_tick} SEATED→ORDERED (auto)")
            self.current = CustomerState.ORDERED
            customer.order_timer_started = True
            return

        # 6) If ORDERED → EATING when food delivered
        if self.current == CustomerState.ORDERED and customer.has_received_food:
            print(f"[FSM] Customer#{customer.spawn_tick} ORDERED→EATING (food delivered)")
            self.current = CustomerState.EATING
            customer.satisfaction = min(100, customer.satisfaction + 15)  # Bonus for getting food, cap at 100
            return

        # 7) If EATING → LEAVING when done
        if self.current == CustomerState.EATING and customer.eating_time >= customer.eating_duration:
            print(f"[Customer#{customer.spawn_tick}] FINISHED EATING → LEAVING")
            self.current = CustomerState.LEAVING
            customer.marked_for_removal = True
            customer.finished_eating = True
            # Add final satisfaction bonus for completing meal
            customer.satisfaction = min(100, customer.satisfaction + 10)
            # Free the table
            if customer.target_table:
                print(f"[Customer#{customer.spawn_tick}] LEAVING → freeing table {tuple(customer.target_table.center)}")
                customer.target_table.occupied = False
                customer.target_table = None
            return

    def transition_to(self, new_state):
        """Force‐set state (not normally needed)"""
        print(f"[FSM] Customer state force-changed: {self.current.name} → {new_state.name}")
        self.current = new_state 