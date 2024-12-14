import pygame
class BaseAgent:
    def __init__(self, start_pos, max_speed=5.0):
        """
        start_pos: (x, y) initial position
        """
        self.position = pygame.math.Vector2(start_pos)
        self.velocity = pygame.math.Vector2(0, 0)
        self.max_speed = max_speed

    def update_position(self, force):
        """
        force: pygame.Vector2 – desired velocity vector
        We clamp the magnitude to max_speed and then update position
        """
        if force.length() > self.max_speed:
            force = force.normalize() * self.max_speed
        self.velocity = pygame.math.Vector2(force)
        self.position += self.velocity
