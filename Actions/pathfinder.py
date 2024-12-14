import heapq

class Pathfinder:
    def __init__(self, world):
        """Initialize with reference to world for grid access."""
        self.world = world

    def find_path(self, start_grid, goal_grid):
        """
        Find a path from start to goal using A* pathfinding.
        Returns a list of pixel‐center Vector2 waypoints.

        NOTE: We allow the start_grid itself to be “walkable,” even if
        world.nav_grid[start_grid] == 1.  This way the Servo can depart
        from a “blocked” tile.  We do *require* that goal_grid be nav_grid==0.
        """

        # 1) Ensure start_grid is in bounds.  (Even if it’s blocked, we still allow it.)
        sx, sy = start_grid
        if not (0 <= sx < self.world.grid_width and 0 <= sy < self.world.grid_height):
            print(f"[Pathfinder] Start {start_grid} is out of bounds ({self.world.grid_width}×{self.world.grid_height})")
            return []

        # 2) Ensure goal_grid is in bounds AND walkable.
        gx, gy = goal_grid
        if not (0 <= gx < self.world.grid_width and 0 <= gy < self.world.grid_height):
            print(f"[Pathfinder] Goal {goal_grid} is out of bounds ({self.world.grid_width}×{self.world.grid_height})")
            return []

        # If the goal cell is blocked, there’s no valid path.
        if self.world.nav_grid[gx][gy] != 0:
            print(f"[Pathfinder] Goal {goal_grid} is blocked (nav_grid={self.world.nav_grid[gx][gy]})")
            return []

        # 3) A* algorithm.  We *skip* checking nav_grid for start_grid; we only
        #    check walkability when we expand neighbors.
        frontier = []
        heapq.heappush(frontier, (0, start_grid))
        came_from = {start_grid: None}
        cost_so_far = {start_grid: 0}

        while frontier:
            current = heapq.heappop(frontier)[1]
            if current == goal_grid:
                break

            for next_pos in self.get_neighbors(current):
                new_cost = cost_so_far[current] + 1
                if next_pos not in cost_so_far or new_cost < cost_so_far[next_pos]:
                    cost_so_far[next_pos] = new_cost
                    priority = new_cost + self.heuristic(next_pos, goal_grid)
                    heapq.heappush(frontier, (priority, next_pos))
                    came_from[next_pos] = current

        # If we never reached goal_grid in came_from, no path was found.
        if goal_grid not in came_from:
            print(f"[Pathfinder] No path found from {start_grid} to {goal_grid}")
            return []

        # 4) Reconstruct the cell‐path, then convert to pixel‐center Vector2 waypoints.
        path_cells = []
        cur = goal_grid
        while cur is not None:
            path_cells.append(cur)
            cur = came_from[cur]
        path_cells.reverse()

        waypoints = []
        for (cx, cy) in path_cells:
            waypoints.append(self.world.grid_to_pixel(cx, cy))

        print(f"[Pathfinder] Found path with {len(waypoints)} waypoints: {path_cells}")
        return waypoints

    def get_neighbors(self, pos):
        """Return the 4-connected neighbors that are walkable (nav_grid == 0)."""
        x, y = pos
        neighbors = []
        for dx, dy in [(0,1), (1,0), (0,-1), (-1,0)]:
            nx, ny = x + dx, y + dy
            # 1) Make sure (nx,ny) is in‐bounds
            if 0 <= nx < self.world.grid_width and 0 <= ny < self.world.grid_height:
                # 2) If that cell is blocked (==1), print a debug and skip it
                if self.world.nav_grid[nx][ny] == 1:
                    print(f"[DEBUG][Pathfinder] Skipping blocked neighbor {(nx, ny)}")
                    continue
                # 3) Otherwise (==0), it’s walkable → include it
                neighbors.append((nx, ny))

        return neighbors

    def heuristic(self, a, b):
        """Manhattan distance heuristic between two grid cells a, b."""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
