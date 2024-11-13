import pygame

class GameData:
    def __init__(self):
        self.score = 0
        self.missed_food = 0
        self.max_missed_food = 3
        self.level = 1
        self.combo = 0
        self.max_combo = 0
        self.food_objects = []
        self.game_over = False
        self.character_speed = 10
        self.base_spawn_rate = 45
        self.current_spawn_rate = 45
        self.difficulty_multiplier = 1.0
        self.score_multiplier = 1.0
        self.spawn_timer = 0
        self.level_timer = 0
        self.special_spawn_chance = 0.15
        self.powerup_active = False
        self.powerup_timer = 0
        self.score_popups = []
        self.achievement_messages = []
        self.total_catches = 0
        self.perfect_catches = 0
        self.start_time = pygame.time.get_ticks()