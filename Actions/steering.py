import pygame
import math

# ───────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS FOR 2D GEOMETRY AND TRANSFORMATION
# ───────────────────────────────────────────────────────────────────
def line_intersection(p1, p2, p3, p4):
    """
    Checks if line segment 'p1p2' intersects with line segment 'p3p4'.
    Returns a dictionary with intersection status and point.
    """
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4

    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if den == 0:
        return {'intersects': False, 'point': None, 'dist': float('inf')}

    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / den

    if 0 < t < 1 and u > 0:
        intersect_point = pygame.math.Vector2(x1 + t * (x2 - x1), y1 + t * (y2 - y1))
        return {'intersects': True, 'point': intersect_point, 'dist': p1.distance_to(intersect_point)}
    else:
        return {'intersects': False, 'point': None, 'dist': float('inf')}

def point_to_local_space(point, heading, side, position):
    """Transforms a world-space point to a vehicle's local space."""
    # Create a transformation matrix
    tx = -position.dot(heading)
    ty = -position.dot(side)
    # Perform the transformation
    transformed_x = point.dot(heading) + tx
    transformed_y = point.dot(side) + ty
    return pygame.math.Vector2(transformed_x, transformed_y)

def vector_to_world_space(vec, heading, side):
    """Transforms a vector from local to world space."""
    # Create a transformation matrix
    mat = pygame.math.Vector2(heading.x, side.x), pygame.math.Vector2(heading.y, side.y)
    # Perform the transformation
    transformed_x = vec.x * mat[0][0] + vec.y * mat[0][1]
    transformed_y = vec.x * mat[1][0] + vec.y * mat[1][1]
    return pygame.math.Vector2(transformed_x, transformed_y)


class SteeringBehavior:
    @staticmethod
    def seek(position, target, max_speed, current_velocity):
        """
        Seek steering behavior - move directly towards target at max_speed.
        Returns a steering force vector.
        """
        desired_velocity = target - position
        if desired_velocity.length() > 0:
            desired_velocity.scale_to_length(max_speed)
        
        # Calculate steering force
        steering_force = desired_velocity - current_velocity
        return steering_force

    @staticmethod
    def arrive(position, target, max_speed, current_velocity, slow_radius=100.0):
        """
        Arrive steering behavior - slow down as we approach the target.
        Returns a steering force vector.
        """
        to_target = target - position
        dist = to_target.length()
        
        if dist < 0.1:
            return -current_velocity # Dampening force to stop
            
        # The speed should vary between 0 and max_speed depending on distance
        speed = max_speed
        if dist < slow_radius:
            speed = max_speed * (dist / slow_radius)
        
        # Calculate the desired velocity
        if dist > 0:
            desired_velocity = to_target.normalize() * speed
        else:
            desired_velocity = pygame.math.Vector2(0, 0)
            
        # Calculate steering force
        steering_force = desired_velocity - current_velocity
        return steering_force

    @staticmethod
    def avoid(position, obstacles, max_speed, look_ahead=50.0):
        """Generate force to avoid static obstacles. Each obstacle is (x,y,radius)."""
        # No force if no obstacles
        if not obstacles:
            return pygame.math.Vector2(0, 0)

        # Check each obstacle
        strongest_force = pygame.math.Vector2(0, 0)
        for ox, oy, radius in obstacles:
            # Vector from position to obstacle center
            to_obstacle = pygame.math.Vector2(ox, oy) - position
            dist = to_obstacle.length()
            
            # Only avoid if within look_ahead distance
            if dist < look_ahead + radius:
                # Force points away from obstacle
                force = -to_obstacle.normalize() * max_speed
                # Scale by closeness (closer = stronger)
                force *= (look_ahead + radius - dist) / (look_ahead + radius)
                # Keep strongest repulsion
                if force.length() > strongest_force.length():
                    strongest_force = force

        return strongest_force

    @staticmethod
    def wall_avoidance(agent, walls, feeler_length=50.0):
        """
        Uses 'feelers' to detect and avoid walls.
        """
        # Create three feelers: one straight ahead, one 45deg left, one 45deg right
        heading = agent.velocity.normalize() if agent.velocity.length() > 0 else pygame.math.Vector2(1, 0)
        
        feelers = [
            agent.position + feeler_length * heading,
            agent.position + feeler_length * heading.rotate(-45),
            agent.position + feeler_length * heading.rotate(45)
        ]
        
        dist_to_closest_ip = float('inf')
        closest_wall = None
        closest_point = None
        steering_force = pygame.math.Vector2(0, 0)

        for feeler in feelers:
            for wall_start, wall_end in walls:
                result = line_intersection(agent.position, feeler, wall_start, wall_end)
                if result['intersects'] and result['dist'] < dist_to_closest_ip:
                    dist_to_closest_ip = result['dist']
                    closest_wall = (wall_start, wall_end)
                    closest_point = result['point']

        if closest_wall:
            overshoot = feeler - closest_point
            wall_vector = closest_wall[1] - closest_wall[0]
            wall_normal = pygame.math.Vector2(-wall_vector.y, wall_vector.x).normalize()
            steering_force = wall_normal * overshoot.length()
        
        return steering_force

    @staticmethod
    def obstacle_avoidance(agent, detection_box_length=120.0):
        """
        Avoids other agents, tables, and customers using a detection box.
        """
        if not hasattr(agent, 'obstacles') or not agent.obstacles:
            return pygame.math.Vector2(0, 0)

        heading = agent.velocity.normalize() if agent.velocity.length() > 0 else pygame.math.Vector2(1, 0)
        side = heading.rotate(90)

        # Dynamic detection box length
        d_box_length = detection_box_length + (agent.velocity.length() / agent.max_speed) * detection_box_length

        closest_dist = float('inf')
        closest_obj = None

        for obj in agent.obstacles:
            # Get the object's position, whether it's called 'position' or 'center'
            obj_pos = getattr(obj, 'position', None) or getattr(obj, 'center', None)
            if not obj_pos:
                continue # Skip objects that don't have a position

            local_pos = point_to_local_space(obj_pos, heading, side, agent.position)

            # Check if object is in front and within the detection box
            if local_pos.x >= 0 and local_pos.x < d_box_length:
                expanded_radius = getattr(obj, 'radius', 20) + getattr(agent, 'radius', 20)
                if abs(local_pos.y) < expanded_radius:
                    # Perform line/circle intersection test
                    sqrt_part = math.sqrt(expanded_radius**2 - local_pos.y**2)
                    ip = local_pos.x - sqrt_part
                    if ip <= 0:
                        ip = local_pos.x + sqrt_part
                    
                    if ip < closest_dist:
                        closest_dist = ip
                        closest_obj = obj
                        
        steering_force = pygame.math.Vector2(0, 0)
        if closest_obj:
            closest_obj_pos = getattr(closest_obj, 'position', None) or getattr(closest_obj, 'center', None)
            local_pos_closest = point_to_local_space(closest_obj_pos, heading, side, agent.position)
            multiplier = 1.0 + (d_box_length - local_pos_closest.x) / d_box_length
            
            # Lateral force to push the agent away
            steering_force.y = (getattr(closest_obj, 'radius', 20) - local_pos_closest.y) * multiplier
            
            # Braking force
            breaking_weight = 0.2
            steering_force.x = (getattr(closest_obj, 'radius', 20) - local_pos_closest.x) * breaking_weight
        
        return vector_to_world_space(steering_force, heading, side)
