import pygame
import logging

# Resource Manager
class ResourceManager:
    def __init__(self):
        self.images = {}
        self.sounds = {}
        self.fonts = {}
        
    def load_image(self, name, size=None):
        try:
            if name not in self.images:
                path = f'assets/images/{name}.png'
                image = pygame.image.load(path)
                if size:
                    image = pygame.transform.scale(image, size)
                self.images[name] = image
            return self.images[name]
        except Exception as e:
            logging.error(f"Error loading image {name}: {e}")
            # Create fallback surface
            surface = pygame.Surface(size or (50, 50))
            surface.fill((200, 200, 200))
            return surface
    
    def load_sound(self, name):
        try:
            if name not in self.sounds:
                path = f'assets/sounds/{name}.mp3'
                self.sounds[name] = pygame.mixer.Sound(path)
            return self.sounds[name]
        except Exception as e:
            logging.error(f"Error loading sound {name}: {e}")
            return None
    
    def load_font(self, size):
        if size not in self.fonts:
            self.fonts[size] = pygame.font.Font(None, size)
        return self.fonts[size]
