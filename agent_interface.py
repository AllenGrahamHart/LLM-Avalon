"""Interface for interacting with LLM agents playing Avalon."""

import json
import os
import re
from pathlib import Path
from typing import Dict, List


class AgentInterface:
    """Handles prompting and parsing responses from LLM agents."""

    def __init__(self, game_rules_path: str = "Official_Rules.md", output_dir: str = "."):
        """Initialize the agent interface."""
        self.game_rules_path = game_rules_path
        self.game_rules = self._load_game_rules()
        self.output_dir = output_dir

    def _load_game_rules(self) -> str:
        """Load the official game rules."""
        with open(self.game_rules_path, "r") as f:
            return f.read()

    def _load_public_log(self) -> Dict:
        """Load the current public game log."""
        with open(os.path.join(self.output_dir, "public_game_log.json"), "r") as f:
            return json.load(f)

    def _load_player_private_thoughts(self, player: str) -> str:
        """Load a player's private thoughts from previous rounds."""
        thought_file = os.path.join(self.output_dir, f"{player}_private_thoughts.txt")
        if Path(thought_file).exists():
            with open(thought_file, "r") as f:
                return f.read()
        return ""

    def _load_current_conversation(self, round_number: int) -> str:
        """Load the current round's conversation so far."""
        with open(os.path.join(self.output_dir, "conversation_log.txt"), "r") as f:
            content = f.read()

        # Extract just the current round's conversation
        round_marker = f"<ROUND>{round_number}</ROUND>"
        if round_marker in content:
            parts = content.split(round_marker)
            if len(parts) > 1:
                # Get everything after the round marker
                current_round = parts[-1]
                # Stop at the next round marker if it exists
                next_round_marker = f"<ROUND>{round_number + 1}</ROUND>"
                if next_round_marker in current_round:
                    current_round = current_round.split(next_round_marker)[0]
                return round_marker + current_round.strip()
        return ""

    def build_discussion_prompt(
        self,
        player: str,
        role: str,
        initial_knowledge: List[str],
        round_number: int,
        phase: str = "pre_proposal"
    ) -> str:
        """Build the prompt for a player during discussion phase."""

        public_log = self._load_public_log()
        private_thoughts = self._load_player_private_thoughts(player)
        current_conversation = self._load_current_conversation(round_number)

        prompt = f"""You are playing The Resistance: Avalon, a game of hidden loyalty and social deduction.

YOUR ROLE: {role}
YOUR IDENTITY: {player}

"""

        # Add role-specific knowledge
        if role == "Merlin":
            prompt += f"As Merlin, you know the evil players are: {', '.join(initial_knowledge)}\n"
            prompt += "IMPORTANT: You must hide your identity! If the Assassin identifies you at the end, evil wins.\n\n"
        elif role in ["Assassin", "Minion"]:
            if initial_knowledge:
                prompt += f"You know your evil allies are: {', '.join(initial_knowledge)}\n\n"
        elif role == "Loyal Servant":
            prompt += "You do not have any special knowledge. You must use logic and discussion to identify evil players.\n\n"

        prompt += f"""GAME RULES (for reference):
{self.game_rules}

---

CURRENT GAME STATE:
{json.dumps(public_log, indent=2)}

---

YOUR PRIVATE THOUGHTS FROM PREVIOUS ROUNDS:
{private_thoughts if private_thoughts else "(No previous thoughts yet)"}

---

CURRENT CONVERSATION (Round {round_number}):
{current_conversation if current_conversation else "(Conversation just starting)"}

---

It is now your turn to speak. Respond with what you want to say to the group.

Your message:"""

        return prompt

    def build_private_thoughts_prompt(
        self,
        player: str,
        role: str,
        initial_knowledge: List[str],
        round_number: int,
        decision_type: str = "vote"  # "vote" or "quest_card"
    ) -> str:
        """Build the prompt for private thoughts and decision-making."""

        public_log = self._load_public_log()
        private_thoughts = self._load_player_private_thoughts(player)
        current_conversation = self._load_current_conversation(round_number)

        prompt = f"""You are playing The Resistance: Avalon.

YOUR ROLE: {role}
YOUR IDENTITY: {player}

"""

        # Add role-specific knowledge
        if role == "Merlin":
            prompt += f"As Merlin, you know the evil players are: {', '.join(initial_knowledge)}\n\n"
        elif role in ["Assassin", "Minion"]:
            if initial_knowledge:
                prompt += f"You know your evil allies are: {', '.join(initial_knowledge)}\n\n"

        prompt += f"""CURRENT GAME STATE:
{json.dumps(public_log, indent=2)}

---

CONVERSATION THIS ROUND:
{current_conversation}

---

YOUR PRIVATE THOUGHTS FROM PREVIOUS ROUNDS:
{private_thoughts if private_thoughts else "(No previous thoughts yet)"}

---

"""

        if decision_type == "vote":
            prompt += """Now you must make a PRIVATE decision about how to vote on the proposed team.

Write your reasoning about:
1. Who are the minions and who is Merlin?
2. Will you vote to accept or reject the team proposed by the leader? Why

End your thoughts with your vote in XML tags:
<VOTE>approve</VOTE> or <VOTE>reject</VOTE>

Your private thoughts:"""

        elif decision_type == "quest_card":
            prompt += """You are on the quest team. Now you must PRIVATELY decide which quest card to play.

"""
            if role in ["Assassin", "Minion"]:
                prompt += """As an evil player, you can choose to:
- Play SUCCESS to maintain your cover
- Play FAIL to sabotage the quest. 

Consider:
- Will sabotaging now reveal your identity?
- Is it better to wait for a later quest?
- What will other players deduce from the outcome?
- Loyal servants of Author cannot sabotage quests
"""
            else:
                prompt += """As a good player, you MUST play SUCCESS.
"""

            prompt += """
Write your reasoning, then end with your decision in XML tags:
<QUEST_CARD>success</QUEST_CARD> or <QUEST_CARD>fail</QUEST_CARD>

Your private thoughts:"""

        return prompt

    def parse_vote(self, response: str) -> str:
        """Extract vote from agent response."""
        match = re.search(r'<VOTE>(approve|reject)</VOTE>', response, re.IGNORECASE)
        if match:
            return match.group(1).lower()
        # Default to reject if parsing fails
        return "reject"

    def parse_quest_card(self, response: str) -> str:
        """Extract quest card from agent response."""
        match = re.search(r'<QUEST_CARD>(success|fail)</QUEST_CARD>', response, re.IGNORECASE)
        if match:
            return match.group(1).lower()
        # Default to success if parsing fails
        return "success"

    def parse_proposed_team(self, response: str) -> List[str]:
        """Extract proposed team from leader's response."""
        match = re.search(r'<PROPOSED_TEAM>(.*?)</PROPOSED_TEAM>', response)
        if match:
            team_str = match.group(1)
            # Parse comma-separated player names
            return [p.strip() for p in team_str.split(',')]
        return []

    def save_conversation_message(self, round_number: int, speaker: str, message: str):
        """Save a message to the conversation log."""
        with open(os.path.join(self.output_dir, "conversation_log.txt"), "a") as f:
            f.write(f"\n{speaker}: {message}\n")

    def save_private_thoughts(self, player: str, round_number: int, thoughts: str, phase: str = "vote"):
        """Save a player's private thoughts."""
        with open(os.path.join(self.output_dir, f"{player}_private_thoughts.txt"), "a") as f:
            f.write(f"\n=== Round {round_number} - {phase.title()} Decision ===\n\n")
            f.write(thoughts)
            f.write("\n")
