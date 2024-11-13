import os
import json
import logging
from datetime import datetime

# Analytics
class Analytics:
    def __init__(self):
        self.session_start = datetime.now()
        self.data = {
            "games_played": 0,
            "total_score": 0,
            "max_score": 0,
            "total_time": 0,
            "items_caught": 0
        }
        self.load_analytics()
    
    def load_analytics(self):
        try:
            if os.path.exists("analytics.json"):
                with open("analytics.json", 'r') as f:
                    self.data = json.load(f)
        except Exception as e:
            logging.error(f"Error loading analytics: {e}")
    
    def save_analytics(self):
        try:
            with open("analytics.json", 'w') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            logging.error(f"Error saving analytics: {e}")
    
    def update_session(self, game_data):
        self.data["games_played"] += 1
        self.data["total_score"] += game_data.score
        self.data["max_score"] = max(self.data["max_score"], game_data.score)
        self.data["items_caught"] += game_data.total_catches
        self.save_analytics()