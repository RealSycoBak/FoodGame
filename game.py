import pygame
import sys
import random
import os
import json
import logging
from enum import Enum, auto
import traceback
from analytics import Analytics
from resourcemanager import ResourceManager
from pausemanager import PauseManager
from gamedata import GameData

# Initialize logging
logging.basicConfig(
    filename='game.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Configuration management
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "sound_volume": 0.7,
    "music_volume": 0.5,
    "screen_width": 1200,
    "screen_height": 800,
    "fps": 60,
    "analytics_enabled": True
}

def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        return DEFAULT_CONFIG
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        return DEFAULT_CONFIG

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        logging.error(f"Error saving config: {e}")

class FoodType(Enum):
    APPLE = {"points": 1, "speed": 1.2, "weight": 0.5, "size": (60, 60), "color": (255, 0, 0)}
    BANANA = {"points": 2, "speed": 1.4, "weight": 0.3, "size": (70, 70), "color": (255, 255, 0)}
    SPECIAL = {"points": 5, "speed": 1.8, "weight": 0.2, "size": (80, 80), "color": (255, 215, 0)}

class GameState(Enum):
    LOBBY = auto()
    PLAYING = auto()
    PAUSED = auto()
    GAME_OVER = auto()
    HOW_TO_PLAY = auto()
    CREDITS = auto()
    SETTINGS = auto()

class Game:
    def __init__(self):
        pygame.init()
        self.config = load_config()
        self.analytics = Analytics()
        self.pause_manager = PauseManager()
        
        # Initialize display
        self.width = self.config["screen_width"]
        self.height = self.config["screen_height"]
        
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Ultimate Food Catcher: Competitive Edition")
        
        # Initialize high score
        self.high_score = self.load_high_score()
        
        # Initialize game state
        self.current_state = GameState.LOBBY
        self.game_data = None
        self.character_rect = None
        
        # Initialize audio
        pygame.mixer.init()
        
        # Initialize resources
        self.resources = ResourceManager()
        self.load_game_resources()
        self.set_volumes()

        # Set up fonts
        self.title_font = pygame.font.Font(None, 72)
        self.menu_font = pygame.font.Font(None, 48)
        self.text_font = pygame.font.Font(None, 36)
        self.font = pygame.font.Font(None, 36)

    
    def set_volumes(self):
        pygame.mixer.music.set_volume(self.config["music_volume"])
        for sound in self.resources.sounds.values():
            if sound:
                sound.set_volume(self.config["sound_volume"])
    
    def load_game_resources(self):
        """Load game resources including images and sounds with proper error handling."""
        try:
            # Load and scale background image
            self.background = pygame.image.load('assets/images/Background.png')
            self.background = pygame.transform.scale(self.background, (self.width, self.height))
            
            # Load and scale character image
            self.character = pygame.image.load('assets/images/character.png')
            self.character = pygame.transform.scale(self.character, (90, 150))
            self.character_rect = self.character.get_rect(center=(self.width // 2, self.height - 170))
            
            # Load sound effects
            self.sounds = {
                'catch': self.resources.load_sound('catch'),
                'level_up': self.resources.load_sound('level_up')
            }
            
            # Load and start background music
            pygame.mixer.music.load('assets/sounds/bg.mp3')
            pygame.mixer.music.play(-1)
            
        except pygame.error as e:
            logging.warning(f"Could not load resources ({e}). Using fallback assets.")
            # Create fallback surfaces
            self.background = pygame.Surface((self.width, self.height))
            self.background.fill((50, 100, 150))
            
            self.character = pygame.Surface((90, 150))
            self.character.fill((200, 200, 200))
            self.character_rect = self.character.get_rect(center=(self.width // 2, self.height - 170))
            
            self.sounds = {'catch': None, 'level_up': None}

    def handle_mouse_click(self, mouse_pos):
        if self.current_state == GameState.LOBBY:
            play_rect, how_to_play_rect, credits_rect = self.get_lobby_buttons()
            
            if play_rect.collidepoint(mouse_pos):
                self.current_state = GameState.PLAYING
                self.game_data = GameData()
            elif how_to_play_rect.collidepoint(mouse_pos):
                self.current_state = GameState.HOW_TO_PLAY
            elif credits_rect.collidepoint(mouse_pos):
                self.current_state = GameState.CREDITS
        
        elif self.current_state == GameState.HOW_TO_PLAY:
            back_rect = pygame.Rect(self.width // 2 - 100, self.height - 80, 200, 50)
            if back_rect.collidepoint(mouse_pos):
                self.current_state = GameState.LOBBY
        
        elif self.current_state == GameState.CREDITS:
            back_rect = pygame.Rect(self.width // 2 - 100, self.height - 80, 200, 50)
            if back_rect.collidepoint(mouse_pos):
                self.current_state = GameState.LOBBY
        
        elif self.current_state == GameState.GAME_OVER:
            if self.game_data:
                button_rect = pygame.Rect(self.width//2 - 100, self.height//2 + 100, 200, 60)
                if button_rect.collidepoint(mouse_pos):
                    self.current_state = GameState.LOBBY
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit_game()
            
            if event.type == pygame.KEYDOWN:
                self.handle_keydown(event)
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.handle_mouse_click(event.pos)

    def handle_keydown(self, event):
        if event.key == pygame.K_ESCAPE:
            if self.current_state == GameState.PLAYING:
                self.pause_manager.toggle_pause()
                self.current_state = GameState.PAUSED
            elif self.current_state == GameState.PAUSED:
                self.pause_manager.toggle_pause()
                self.current_state = GameState.PLAYING
            elif self.current_state in [GameState.HOW_TO_PLAY, GameState.CREDITS]:
                self.current_state = GameState.LOBBY
    
    
    def render(self):
        self.screen.fill((0, 0, 0))
        
        if self.current_state in [GameState.PLAYING, GameState.PAUSED]:
            # Render the game state regardless of whether it's paused or not
            self.render_game()
            
            # If the game is paused, render the pause overlay
            if self.pause_manager.paused:
                self.render_pause_overlay()
        elif self.current_state == GameState.LOBBY:
            self.render_lobby()
        elif self.current_state == GameState.HOW_TO_PLAY:
            self.render_how_to_play()
        elif self.current_state == GameState.CREDITS:
            self.render_credits()
        elif self.current_state == GameState.GAME_OVER:
            self.render_game_over()
        
        pygame.display.flip()

    def render_pause_overlay(self):
        # Create a semi-transparent overlay
        overlay = pygame.Surface((self.width, self.height))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(128)  # 128 is half transparent
        self.screen.blit(overlay, (0, 0))
        
        # Render "PAUSED" text
        pause_text = self.title_font.render("PAUSED", True, (255, 255, 255))
        text_rect = pause_text.get_rect(center=(self.width // 2, self.height // 2))
        self.screen.blit(pause_text, text_rect)
        
        # Render instructions
        instruction_text = self.text_font.render("Press ESC to resume", True, (255, 255, 255))
        instruction_rect = instruction_text.get_rect(center=(self.width // 2, self.height // 2 + 60))
        self.screen.blit(instruction_text, instruction_rect)
    
    def quit_game(self):
        logging.info("Game closing - saving data")
        self.save_high_score()
        self.analytics.save_analytics()
        save_config(self.config)
        pygame.quit()
        sys.exit()
    
    def run(self):
        clock = pygame.time.Clock()
        
        while True:
            try:
                self.handle_events()
                self.update()
                self.render()
                clock.tick(self.config["fps"])
            except Exception as e:
                logging.error(f"Critical error: {traceback.format_exc()}")
                self.handle_crash()
    
    def handle_crash(self):
        logging.info("Attempting to recover from crash")
        try:
            self.current_state = GameState.LOBBY
            self.game_data = None
            self.pause_manager.paused = False
            pygame.mixer.music.play(-1)
        except Exception as e:
            logging.error(f"Recovery failed: {e}")
            self.quit_game()

    def load_high_score(self):
        try:
            if os.path.exists("high_score.txt"):
                with open("high_score.txt", 'r') as f:
                    return int(f.read().strip())
            return 0
        except (ValueError, IOError) as e:
            logging.error(f"Error loading high score: {e}")
            return 0

    def save_high_score(self):
        try:
            with open("high_score.txt", 'w') as f:
                f.write(str(self.high_score))
        except IOError as e:
            logging.error(f"Error saving high score: {e}")

    def spawn_food(self, game_data):
        weights = [
            FoodType.APPLE.value["weight"],
            FoodType.BANANA.value["weight"],
            FoodType.SPECIAL.value["weight"] if random.random() < game_data.special_spawn_chance else 0
        ]
        food_type = random.choices(list(FoodType), weights=weights)[0]
        
        try:
            food_img = pygame.image.load(f'assets/images/{food_type.name.lower()}.png')
            food_img = pygame.transform.scale(food_img, food_type.value["size"])
        except pygame.error:
            food_img = pygame.Surface(food_type.value["size"])
            food_img.fill(food_type.value["color"])
        
        player_x = self.character_rect.centerx
        spawn_window = 400
        
        if player_x < 300:
            spawn_x = random.randint(200, 600)
        elif player_x > self.width - 300:
            spawn_x = random.randint(self.width - 600, self.width - 200)
        else:
            min_spawn = max(100, player_x - spawn_window // 2)
            max_spawn = min(self.width - 100, player_x + spawn_window // 2)
            spawn_x = random.randint(min_spawn, max_spawn)
            
            if random.random() < 0.2:
                offset = random.choice([-200, 200])
                spawn_x = max(100, min(self.width - 100, spawn_x + offset))
        
        spawn_y = random.randint(-70, -40)
        food_rect = food_img.get_rect(topleft=(spawn_x, spawn_y))
        
        for existing_food in game_data.food_objects:
            if abs(existing_food['rect'].centerx - spawn_x) < 60:
                spawn_x += random.choice([-50, 50])
                spawn_x = max(100, min(self.width - 100, spawn_x))
                food_rect.x = spawn_x
        
        game_data.food_objects.append({
            'img': food_img,
            'rect': food_rect,
            'type': food_type,
            'speed': food_type.value["speed"] * game_data.difficulty_multiplier
        })

    def update(self):
            if self.current_state == GameState.PLAYING:
                if self.game_data and not self.pause_manager.paused:
                    self.update_game_state()
                    
                    # Update high score if current score is higher
                    if self.game_data.score > self.high_score:
                        self.high_score = self.game_data.score
                        self.save_high_score()

    def update_game_state(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_a] and self.character_rect.left > 0:
            self.character_rect.x -= self.game_data.character_speed
        if keys[pygame.K_d] and self.character_rect.right < self.width:
            self.character_rect.x += self.game_data.character_speed
        
        self.update_difficulty(self.game_data)
        self.game_data.spawn_timer += 1
        if self.game_data.spawn_timer >= self.game_data.current_spawn_rate:
            self.spawn_food(self.game_data)
            self.game_data.spawn_timer = 0
        
        # Update food positions and collisions
        for food in self.game_data.food_objects[:]:
            food['rect'].y += food['speed']
            
            if food['rect'].colliderect(self.character_rect):
                self.handle_collision(self.game_data, food)
            elif food['rect'].top > self.height:
                self.game_data.food_objects.remove(food)
                self.game_data.missed_food += 1
                self.game_data.combo = 0
                
                if self.game_data.missed_food >= self.game_data.max_missed_food:
                    self.game_data.game_over = True
                    self.current_state = GameState.GAME_OVER

    def update_difficulty(self, game_data):
        game_data.level_timer += 1
        if game_data.level_timer >= 500:
            game_data.level += 1
            game_data.level_timer = 0
            
            game_data.difficulty_multiplier = 1.0 + (game_data.level - 1) * 0.12
            game_data.current_spawn_rate = max(
                15,
                game_data.base_spawn_rate - (game_data.level - 1) * 4
            )
            game_data.special_spawn_chance = min(0.35, 0.15 + (game_data.level - 1) * 0.025)
            game_data.character_speed = min(16, 10 + (game_data.level - 1) * 0.6)
            
            game_data.achievement_messages.append({
                'text': f'Level Up! {game_data.level}',
                'timer': 120,
                'color': (255, 215, 0)
            })

    def handle_collision(self, game_data, food):
        food_type = food['type']
        base_points = food_type.value["points"]
        
        game_data.combo += 1
        game_data.max_combo = max(game_data.max_combo, game_data.combo)
        combo_multiplier = min(4, 1 + (game_data.combo * 0.15))
        
        points = int(base_points * combo_multiplier * game_data.score_multiplier)
        game_data.score += points
        game_data.total_catches += 1
        
        game_data.score_popups.append({
            'text': f'+{points}',
            'pos': (food['rect'].centerx, food['rect'].centery),
            'timer': 60,
            'color': food_type.value["color"]
        })
        
        if game_data.combo == 10:
            game_data.achievement_messages.append({
                'text': 'Super Combo!',
                'timer': 120,
                'color': (255, 165, 0)
            })
        
        if self.sounds['catch']:
            self.sounds['catch'].play()
        game_data.food_objects.remove(food)
        
        return points

    def draw_button(self, screen, text, rect, button_color=(0, 128, 0), border_color=(0, 255, 0)):
        font = self.menu_font
        pygame.draw.rect(screen, button_color, rect)
        pygame.draw.rect(screen, border_color, rect, 3)
        
        text_surface = font.render(text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=rect.center)
        screen.blit(text_surface, text_rect)
        
        return rect

    def draw_enhanced_hud(self, screen, game_data):
        pygame.draw.rect(screen, (0, 0, 0), (0, 0, self.width, 60))
        
        hud_texts = [
            f"Score: {game_data.score}",
            f"Level: {game_data.level}",
            f"Combo: {game_data.combo}x"
        ]
        
        for i, text in enumerate(hud_texts):
            rendered_text = self.font.render(text, True, (255, 255, 255))
            screen.blit(rendered_text, (10 + i * 200, 20))
        
        for popup in game_data.score_popups[:]:
            popup['timer'] -= 1
            alpha = min(255, popup['timer'] * 4)
            text = self.font.render(popup['text'], True, popup['color'])
            text.set_alpha(alpha)
            screen.blit(text, (popup['pos'][0] - text.get_width()//2, 
                            popup['pos'][1] - (60 - popup['timer'])))
            if popup['timer'] <= 0:
                game_data.score_popups.remove(popup)
        
        for msg in game_data.achievement_messages[:]:
            msg['timer'] -= 1
            if msg['timer'] > 0:
                text = self.font.render(msg['text'], True, msg['color'])
                screen.blit(text, (self.width//2 - text.get_width()//2, 100))
            else:
                game_data.achievement_messages.remove(msg)
        
        for i in range(game_data.max_missed_food):
            color = (255, 0, 0) if i < game_data.missed_food else (0, 255, 0)
            pygame.draw.circle(screen, color, (self.width - 30 - i * 40, 30), 15)

    def draw_lobby(self, screen):
        screen.blit(self.background, (0, 0))
        
        title = self.title_font.render("Ultimate Food Catcher", True, (255, 215, 0))
        title_rect = title.get_rect(center=(self.width // 2, self.height // 4))
        screen.blit(title, title_rect)
        
        button_width = 300
        button_height = 60
        button_x = self.width // 2 - button_width // 2
        
        play_rect = pygame.Rect(button_x, self.height // 2, button_width, button_height)
        how_to_play_rect = pygame.Rect(button_x, self.height // 2 + 100, button_width, button_height)
        credits_rect = pygame.Rect(button_x, self.height // 2 + 200, button_width, button_height)
        
        self.draw_button(screen, "Play Game", play_rect)
        self.draw_button(screen, "How to Play", how_to_play_rect)
        self.draw_button(screen, "Credits", credits_rect)
        
        return play_rect, how_to_play_rect, credits_rect

    def draw_section_title(self, screen, text, y_pos, color=(255, 215, 0)):
        """Helper function to draw consistent section titles"""
        title = self.title_font.render(text, True, color)
        title_shadow = self.title_font.render(text, True, (0, 0, 0))
        
        # Draw shadow
        screen.blit(title_shadow, (self.width // 2 - title.get_width() // 2 + 2, y_pos + 2))
        # Draw main text
        screen.blit(title, (self.width // 2 - title.get_width() // 2, y_pos))
        
        # Draw decorative lines
        line_width = 200
        line_y = y_pos + title.get_height() + 10
        pygame.draw.line(screen, color, 
                        (self.width // 2 - line_width, line_y),
                        (self.width // 2 + line_width, line_y), 3)

    def draw_how_to_play(self, screen):
        # Create a semi-transparent overlay
        overlay = pygame.Surface((self.width, self.height))
        overlay.fill((20, 30, 40))
        overlay.set_alpha(240)
        screen.blit(overlay, (0, 0))
        
        self.draw_section_title(screen, "How to Play", 30)
        
        # Create sections for better organization
        sections = {
            "Controls": [
                "Move left with A key",
                "Move right with D key"
            ],
            "Scoring": [
                "Apples: 1 point (Common)",
                "Bananas: 2 points (Uncommon)",
                "Special items: 5 points (Rare)"
            ],
            "Game Rules": [
                "Catch falling food items to score points",
                "Build combos by catching items without missing",
                "Missing 3 items ends the game",
                "Higher combos = Higher score multiplier!"
            ],
            "Tips": [
                "Watch for special golden items",
                "Stay near the center for better control",
                "The game gets faster as you level up!"
            ]
        }
        
        y = 150
        for section_title, instructions in sections.items():
            # Section header
            header = self.menu_font.render(section_title, True, (255, 165, 0))
            header_rect = header.get_rect(center=(self.width // 2, y))
            
            # Draw header background
            pygame.draw.rect(screen, (0, 0, 0, 128), 
                            (header_rect.left - 20, header_rect.top - 5,
                            header_rect.width + 40, header_rect.height + 10))
            screen.blit(header, header_rect)
            
            y += 60
            
            # Draw items in section
            for line in instructions:
                text = self.text_font.render(line, True, (220, 220, 220))
                text_rect = text.get_rect(center=(self.width // 2, y))
                
                # Draw text shadow
                text_shadow = self.text_font.render(line, True, (0, 0, 0))
                shadow_rect = text_rect.copy()
                shadow_rect.x += 2
                shadow_rect.y += 2
                screen.blit(text_shadow, shadow_rect)
                
                screen.blit(text, text_rect)
                y += 40
            
            y += 20  # Space between sections
        
        mouse_pos = pygame.mouse.get_pos()
        back_rect = pygame.Rect(self.width // 2 - 100, self.height - 80, 200, 50)
        
        button_color = (0, 150, 0) if back_rect.collidepoint(mouse_pos) else (0, 100, 0)
        pygame.draw.rect(screen, button_color, back_rect, border_radius=10)
        pygame.draw.rect(screen, (0, 255, 0), back_rect, 3, border_radius=10)
        
        back_text = self.menu_font.render("Back", True, (255, 255, 255))
        screen.blit(back_text, (back_rect.centerx - back_text.get_width() // 2,
                            back_rect.centery - back_text.get_height() // 2))
        
        return back_rect

    def draw_credits(self, screen):
        # Create a semi-transparent overlay
        overlay = pygame.Surface((self.width, self.height))
        overlay.fill((20, 30, 40))
        overlay.set_alpha(240)
        screen.blit(overlay, (0, 0))
        
        self.draw_section_title(screen, "Credits", 30)
        
        credits_sections = {
            "Development Team": [
                ("Game Design & Programming", "Alon Baker"),
                ("Graphics & Art", "Alon Baker"),
                ("UI/UX Design", "Alon Baker")
            ],
            "Audio": [
                ("Music", "From Google"),
                ("Sound Effects", "From Google")
            ],
            "Special Thanks": [
                ("Support", "My Family & Friends"),
                ("Technical Support", "The Python Community"),
                ("Game Engine", "Pygame Development Team")
            ]
        }
        
        y = 150
        for section_title, items in credits_sections.items():
            # Section header
            header = self.menu_font.render(section_title, True, (255, 165, 0))
            header_rect = header.get_rect(center=(self.width // 2, y))
            
            # Draw header background
            pygame.draw.rect(screen, (0, 0, 0, 128), 
                            (header_rect.left - 20, header_rect.top - 5,
                            header_rect.width + 40, header_rect.height + 10))
            screen.blit(header, header_rect)
            
            y += 60
            
            # Draw credits items
            for role, name in items:
                # Role text
                role_text = self.text_font.render(role + ":", True, (180, 180, 180))
                role_rect = role_text.get_rect(right=self.width // 2 - 10, centery=y)
                
                # Name text
                name_text = self.text_font.render(name, True, (255, 255, 255))
                name_rect = name_text.get_rect(left=self.width // 2 + 10, centery=y)
                
                # Draw text shadows
                shadow_offset = 2
                role_shadow = self.text_font.render(role + ":", True, (0, 0, 0))
                name_shadow = self.text_font.render(name, True, (0, 0, 0))
                
                screen.blit(role_shadow, (role_rect.x + shadow_offset, role_rect.y + shadow_offset))
                screen.blit(name_shadow, (name_rect.x + shadow_offset, name_rect.y + shadow_offset))
                
                screen.blit(role_text, role_rect)
                screen.blit(name_text, name_rect)
                
                y += 40
            
            y += 30  # Space between sections
        
        # Version info
        version_text = self.text_font.render("Version 1.0", True, (150, 150, 150))
        screen.blit(version_text, (20, self.height - 40))
        
        mouse_pos = pygame.mouse.get_pos()
        back_rect = pygame.Rect(self.width // 2 - 100, self.height - 80, 200, 50)
        
        button_color = (0, 150, 0) if back_rect.collidepoint(mouse_pos) else (0, 100, 0)
        pygame.draw.rect(screen, button_color, back_rect, border_radius=10)
        pygame.draw.rect(screen, (0, 255, 0), back_rect, 3, border_radius=10)
        
        back_text = self.menu_font.render("Back", True, (255, 255, 255))
        screen.blit(back_text, (back_rect.centerx - back_text.get_width() // 2,
                            back_rect.centery - back_text.get_height() // 2))
        
        return back_rect

    def show_game_over(self, game_data):
        # Create semi-transparent overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        # Game Over title with shadow
        title = self.title_font.render("Game Over!", True, (255, 215, 0))
        title_shadow = self.title_font.render("Game Over!", True, (0, 0, 0))
        title_pos = (self.width//2 - title.get_width()//2, self.height//4)
        self.screen.blit(title_shadow, (title_pos[0] + 2, title_pos[1] + 2))
        self.screen.blit(title, title_pos)
        
        # Update high score before displaying
        if game_data.score > self.high_score:
            self.high_score = game_data.score
            self.save_high_score()
            new_record_text = self.menu_font.render("New High Score!", True, (255, 215, 0))
            self.screen.blit(new_record_text, 
                           (self.width//2 - new_record_text.get_width()//2, 
                            self.height//4 + title.get_height() + 20))
        
        stats = [
            f"Final Score: {game_data.score}",
            f"High Score: {self.high_score}",
            f"Max Level: {game_data.level}",
            f"Best Combo: {game_data.max_combo}x",
            f"Total Catches: {game_data.total_catches}"
        ]
        
        y_offset = self.height//2 - 100
        for stat in stats:
            text = self.font.render(stat, True, (255, 255, 255))
            text_shadow = self.font.render(stat, True, (0, 0, 0))
            text_pos = (self.width//2 - text.get_width()//2, y_offset)
            self.screen.blit(text_shadow, (text_pos[0] + 2, text_pos[1] + 2))
            self.screen.blit(text, text_pos)
            y_offset += 40
        
        button_rect = pygame.Rect(self.width//2 - 100, self.height//2 + 100, 200, 60)
        
        # Button hover effect
        mouse_pos = pygame.mouse.get_pos()
        button_color = (0, 150, 0) if button_rect.collidepoint(mouse_pos) else (0, 100, 0)
        
        pygame.draw.rect(self.screen, button_color, button_rect, border_radius=10)
        pygame.draw.rect(self.screen, (0, 255, 0), button_rect, 3, border_radius=10)
        
        button_text = self.font.render("Play Again", True, (255, 255, 255))
        self.screen.blit(button_text, (button_rect.centerx - button_text.get_width()//2,
                                     button_rect.centery - button_text.get_height()//2))
        
        return button_rect
    
    def restart_game():
        return GameData() 
    
    def render_how_to_play(self):
        self.draw_how_to_play(self.screen)

    def render_credits(self):
        self.draw_credits(self.screen)

    def render_game_over(self):
        if self.game_data:
            self.show_game_over(self.game_data)
    
    def render_game(self):
        self.screen.blit(self.background, (0, 0))
        self.screen.blit(self.character, self.character_rect)
        
        if self.game_data:
            for food in self.game_data.food_objects:
                self.screen.blit(food['img'], food['rect'])
            self.draw_enhanced_hud(self.screen, self.game_data)
    
    def get_lobby_buttons(self):
        button_width = 300
        button_height = 60
        button_x = self.width // 2 - button_width // 2
        
        play_rect = pygame.Rect(button_x, self.height // 2, button_width, button_height)
        how_to_play_rect = pygame.Rect(button_x, self.height // 2 + 100, button_width, button_height)
        credits_rect = pygame.Rect(button_x, self.height // 2 + 200, button_width, button_height)
        
        return play_rect, how_to_play_rect, credits_rect

    def render_lobby(self):
        self.screen.blit(self.background, (0, 0))
        play_rect, how_to_play_rect, credits_rect = self.get_lobby_buttons()
        
        # Draw title
        title = self.title_font.render("Ultimate Food Catcher", True, (255, 215, 0))
        title_rect = title.get_rect(center=(self.width // 2, self.height // 4))
        self.screen.blit(title, title_rect)
        
        # Draw buttons
        self.draw_button(self.screen, "Play Game", play_rect)
        self.draw_button(self.screen, "How to Play", how_to_play_rect)
        self.draw_button(self.screen, "Credits", credits_rect)

if __name__ == '__main__':
    try:
        game = Game()
        game.run()
    except Exception as e:
        logging.critical(f"Fatal error: {traceback.format_exc()}")
        pygame.quit()
        sys.exit(1)