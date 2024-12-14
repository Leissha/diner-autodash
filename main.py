from world import World
import pygame
import sys
import traceback

if __name__ == "__main__":
    print("[Main] Starting DinnerAutoDashhhh...")
    try:
        print("[Main] Creating World instance...")
        game_world = World()
        print("[Main] Running game loop...")
        game_world.run()
    except Exception as e:
        print("\n=== EXCEPTION in main.py ===")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("\nFull traceback:")
        traceback.print_exc()
        pygame.quit()
        sys.exit(1)