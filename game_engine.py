import json
import os
import random
from typing import List, Dict, Tuple
from pathlib import Path

class AvalonGame:
    def __init__(self, player_names: List[str] = None, output_dir: str = "."):
        """Initialize the Avalon game with 5 players."""
        if player_names is None:
            player_names = ["Player1", "Player2", "Player3", "Player4", "Player5"]

        self.player_count = 5
        self.players = player_names.copy()
        self.output_dir = output_dir

        # Randomly assign roles
        self.roles = self._assign_roles()

        # Randomly determine seating order
        self.seating_order = self.players.copy()
        random.shuffle(self.seating_order)

        # Randomly select initial leader
        self.leader_index = random.randint(0, len(self.seating_order) - 1)
        self.current_leader = self.seating_order[self.leader_index]

        # Quest requirements for 5 players
        self.quest_requirements = {
            1: 2,
            2: 3,
            3: 2,
            4: 3,
            5: 3
        }

        # Game state
        self.current_quest = 1
        self.quest_score = {"good": 0, "evil": 0}
        self.consecutive_rejections = 0
        self.rounds = []

        # Initialize logs
        self._initialize_logs()

    def _assign_roles(self) -> Dict[str, str]:
        """Assign roles to players: 3 good (including Merlin), 2 evil (including Assassin)."""
        roles = {}

        # Shuffle players
        shuffled_players = self.players.copy()
        random.shuffle(shuffled_players)

        # Assign roles
        roles[shuffled_players[0]] = "Merlin"
        roles[shuffled_players[1]] = "Loyal Servant"
        roles[shuffled_players[2]] = "Loyal Servant"
        roles[shuffled_players[3]] = "Assassin"
        roles[shuffled_players[4]] = "Minion"

        return roles

    def get_initial_knowledge(self) -> Dict[str, List[str]]:
        """Determine what each player knows at game start."""
        knowledge = {player: [] for player in self.players}

        # Find evil players
        evil_players = [p for p, r in self.roles.items() if r in ["Assassin", "Minion"]]

        # Evil players know each other
        for evil_player in evil_players:
            knowledge[evil_player] = [p for p in evil_players if p != evil_player]

        # Merlin knows all evil players
        merlin = [p for p, r in self.roles.items() if r == "Merlin"][0]
        knowledge[merlin] = evil_players.copy()

        return knowledge

    def _initialize_logs(self):
        """Initialize the game log files."""
        # Full game log
        initial_knowledge = self.get_initial_knowledge()

        full_log = {
            "game_id": "game_001",
            "player_count": self.player_count,
            "seating_order": self.seating_order,
            "role_assignments": self.roles,
            "initial_knowledge": initial_knowledge,
            "quest_requirements": self.quest_requirements,
            "quest_score": self.quest_score,
            "rounds": [],
            "assassination_phase": None,
            "game_result": None,
            "game_status": "in_progress"
        }

        with open(os.path.join(self.output_dir, "full_game_log.json"), "w") as f:
            json.dump(full_log, f, indent=2)

        # Public game log
        public_log = {
            "game_id": "game_001",
            "player_count": self.player_count,
            "players": self.seating_order,
            "quest_requirements": self.quest_requirements,
            "quest_score": self.quest_score,
            "rounds": [],
            "consecutive_rejections": 0,
            "game_status": "in_progress"
        }

        with open(os.path.join(self.output_dir, "public_game_log.json"), "w") as f:
            json.dump(public_log, f, indent=2)

        # Initialize conversation log
        with open(os.path.join(self.output_dir, "conversation_log.txt"), "w") as f:
            f.write("=== AVALON GAME START ===\n\n")
            f.write(f"Seating order: {', '.join(self.seating_order)}\n")
            f.write(f"Initial leader: {self.current_leader}\n\n")

        # Initialize full conversation log (includes private thoughts)
        with open(os.path.join(self.output_dir, "full_conversation_log.txt"), "w") as f:
            f.write("=== AVALON GAME START - FULL CONVERSATION LOG ===\n\n")
            f.write("This log includes both private thoughts and public messages from all players.\n")
            f.write("Use this for analysis and debugging.\n\n")
            f.write(f"Seating order: {', '.join(self.seating_order)}\n")
            f.write(f"Initial leader: {self.current_leader}\n\n")

        # Initialize private thought files for each player
        for player in self.players:
            with open(os.path.join(self.output_dir, f"{player}_private_thoughts.txt"), "w") as f:
                f.write(f"=== {player} Private Thoughts ===\n\n")

    def get_player_role_info(self, player: str) -> Dict:
        """Get role information for a specific player."""
        role = self.roles[player]
        knowledge = self.get_initial_knowledge()[player]

        return {
            "player": player,
            "role": role,
            "knows_about": knowledge
        }

    def rotate_leader(self):
        """Move leader token to next player in seating order."""
        self.leader_index = (self.leader_index + 1) % len(self.seating_order)
        self.current_leader = self.seating_order[self.leader_index]

    def get_speaker_order(self) -> List[str]:
        """Get speaking order starting from leader."""
        # Start from leader and go clockwise
        return self.seating_order[self.leader_index:] + self.seating_order[:self.leader_index]

    def update_public_log(self, round_data: Dict):
        """Update the public game log with new round data."""
        with open(os.path.join(self.output_dir, "public_game_log.json"), "r") as f:
            log = json.load(f)

        log["rounds"].append(round_data)
        log["quest_score"] = self.quest_score
        log["consecutive_rejections"] = self.consecutive_rejections

        with open(os.path.join(self.output_dir, "public_game_log.json"), "w") as f:
            json.dump(log, f, indent=2)

    def update_full_log(self, round_data: Dict):
        """Update the full game log with complete round data."""
        with open(os.path.join(self.output_dir, "full_game_log.json"), "r") as f:
            log = json.load(f)

        log["rounds"].append(round_data)
        log["quest_score"] = self.quest_score

        with open(os.path.join(self.output_dir, "full_game_log.json"), "w") as f:
            json.dump(log, f, indent=2)


def main():
    """Initialize and start the game."""
    print("=== Initializing Avalon Game ===")

    game = AvalonGame()

    print(f"\nSeating order: {game.seating_order}")
    print(f"Initial leader: {game.current_leader}")
    print(f"\nRole assignments (hidden from players):")
    for player, role in game.roles.items():
        print(f"  {player}: {role}")

    print(f"\nInitial knowledge:")
    knowledge = game.get_initial_knowledge()
    for player, knows in knowledge.items():
        if knows:
            print(f"  {player} knows: {knows}")

    print("\nGame logs initialized successfully!")
    print("Ready to start game loop...")


if __name__ == "__main__":
    main()
