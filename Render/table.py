import pygame

from constants import TILE_SIZE

class Table:
    def __init__(self, center, capacity=1):
        """
        center: pygame.math.Vector2 for the table's center position
        capacity: number of customers that can sit at this table
        """
        self.center = pygame.math.Vector2(center)
        self.capacity = capacity
        self.occupied = False
        
        # Fixed table size
        self.width, self.height = TILE_SIZE, TILE_SIZE
        self.radius = TILE_SIZE / 2.0 # For obstacle avoidance
        
        # Calculate top-left corner from center
        self.top_left = self.center - pygame.math.Vector2(self.width/2, self.height/2)

    def draw(self, screen):
        # Create rectangle from top-left corner
        rect = pygame.Rect(self.top_left.x, self.top_left.y, self.width, self.height)
        
        # Fill with pastel pink color (darker if occupied)
        color = (255, 241, 252) if not self.occupied else (204, 192, 201) 
        pygame.draw.rect(screen, color, rect)
        
        # Draw dark pink border
        pygame.draw.rect(screen, (255, 209, 245), rect, 5)
