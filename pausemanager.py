import pygame
#Game State Management
class PauseManager:
    def __init__(self):
        self.paused = False
        self.pause_start = None
        self.total_pause_time = 0
    
    def toggle_pause(self):
        self.paused = not self.paused
        if self.paused:
            self.pause_start = pygame.time.get_ticks()
        else:
            self.total_pause_time += pygame.time.get_ticks() - self.pause_start