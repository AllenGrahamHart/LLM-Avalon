"""Main game loop for Avalon."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from anthropic import Anthropic
from dotenv import load_dotenv
from game_engine import AvalonGame
from agent_interface import AgentInterface

# Load environment variables from .env file
load_dotenv()


class LLMAgent:
    """LLM agent using Anthropic's Claude API."""

    def __init__(self, name: str, api_key: str = None):
        self.name = name

        # Get API key from parameter or environment variable
        if api_key is None:
            api_key = os.environ.get("ANTHROPIC_API_KEY")

        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY must be provided or set in environment")

        self.client = Anthropic(api_key=api_key)
        # Using Claude 3 Haiku - the cheapest Anthropic model
        self.model = "claude-3-haiku-20240307"

    def get_response(self, prompt: str) -> str:
        """Get response from Claude API."""
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response = message.content[0].text
            return response

        except Exception as e:
            print(f"Error getting response from {self.name}: {e}")
            # Return a safe default
            return "I approve of this proposal. <VOTE>approve</VOTE>"


def run_discussion_round(
    game: AvalonGame,
    interface: AgentInterface,
    agents: Dict[str, LLMAgent],
    round_number: int,
    num_turns: int = 3
):
    """Run a discussion round with all players speaking in order."""

    # Write round header to conversation logs
    with open(os.path.join(game.output_dir, "conversation_log.txt"), "a") as f:
        f.write(f"\n<ROUND>{round_number}</ROUND>\n")

    with open(os.path.join(game.output_dir, "full_conversation_log.txt"), "a") as f:
        f.write(f"\n\n{'#'*60}\n")
        f.write(f"# ROUND {round_number}\n")
        f.write(f"{'#'*60}\n")

    speaker_order = game.get_speaker_order()

    # Each player speaks num_turns times
    for turn in range(num_turns):
        for speaker in speaker_order:
            # Get role info for this player
            role_info = game.get_player_role_info(speaker)

            # Build prompt
            prompt = interface.build_discussion_prompt(
                player=speaker,
                role=role_info["role"],
                initial_knowledge=role_info["knows_about"],
                round_number=round_number
            )

            # Get agent's response
            agent = agents[speaker]
            response = agent.get_response(prompt)

            # Parse public message from response
            public_message = interface.parse_discussion_message(response)

            # Save full response (including private thoughts) to player's private file
            interface.save_private_thoughts(speaker, round_number, response, phase="discussion")

            # Save only public message to conversation log
            interface.save_conversation_message(round_number, speaker, public_message)

            # Save both private thoughts and public message to full conversation log
            interface.save_full_conversation_message(round_number, speaker, response, public_message)

            print(f"{speaker}: {public_message}")


def collect_votes(
    game: AvalonGame,
    interface: AgentInterface,
    agents: Dict[str, LLMAgent],
    round_number: int,
    proposed_team: List[str]
) -> Dict[str, str]:
    """Collect private thoughts and votes from all players."""

    votes = {}

    print(f"\n{'='*60}")
    print("COLLECTING VOTES...")
    print(f"{'='*60}\n")

    for player in game.players:
        role_info = game.get_player_role_info(player)

        # Build private thoughts prompt
        prompt = interface.build_private_thoughts_prompt(
            player=player,
            role=role_info["role"],
            initial_knowledge=role_info["knows_about"],
            round_number=round_number,
            decision_type="vote"
        )

        # Get agent's private thoughts
        agent = agents[player]
        response = agent.get_response(prompt)

        # Parse vote
        vote = interface.parse_vote(response)
        votes[player] = vote

        # Save private thoughts
        interface.save_private_thoughts(player, round_number, response, phase="vote")

        print(f"{player} voted: {vote}")

    return votes


def collect_quest_cards(
    game: AvalonGame,
    interface: AgentInterface,
    agents: Dict[str, LLMAgent],
    round_number: int,
    team_members: List[str]
) -> Dict[str, str]:
    """Collect quest card decisions from team members."""

    quest_cards = {}

    print(f"\n{'='*60}")
    print("COLLECTING QUEST CARDS...")
    print(f"{'='*60}\n")

    for player in team_members:
        role_info = game.get_player_role_info(player)

        # Build quest decision prompt
        prompt = interface.build_private_thoughts_prompt(
            player=player,
            role=role_info["role"],
            initial_knowledge=role_info["knows_about"],
            round_number=round_number,
            decision_type="quest_card"
        )

        # Get agent's decision
        agent = agents[player]
        response = agent.get_response(prompt)

        # Parse quest card
        card = interface.parse_quest_card(response)

        # Enforce good players must play success
        if role_info["role"] not in ["Assassin", "Minion"]:
            card = "success"

        quest_cards[player] = card

        # Save private thoughts
        interface.save_private_thoughts(player, round_number, response, phase="quest")

        print(f"{player} played: {card}")

    return quest_cards


def run_quest_round(game: AvalonGame, interface: AgentInterface, agents: Dict[str, LLMAgent]):
    """Run a complete quest round."""

    round_number = len(game.rounds) + 1

    print(f"\n{'#'*60}")
    print(f"# QUEST {game.current_quest} - ROUND {round_number}")
    print(f"# Leader: {game.current_leader}")
    print(f"# Team size required: {game.quest_requirements[game.current_quest]}")
    print(f"{'#'*60}\n")

    # Phase 1: Pre-proposal discussion
    print("=== PRE-PROPOSAL DISCUSSION ===\n")
    run_discussion_round(game, interface, agents, round_number, num_turns=3)

    # Phase 2: Leader proposes team
    print(f"\n=== TEAM PROPOSAL ===\n")
    print(f"Leader {game.current_leader} proposes team...")

    # TODO: In full implementation, get leader's proposal via LLM
    # For now, use a simple placeholder
    required_size = game.quest_requirements[game.current_quest]
    proposed_team = game.seating_order[:required_size]  # Placeholder

    print(f"Proposed team: {proposed_team}\n")

    # Phase 3: Voting
    votes = collect_votes(game, interface, agents, round_number, proposed_team)

    # Count votes
    approve_count = sum(1 for v in votes.values() if v == "approve")
    reject_count = sum(1 for v in votes.values() if v == "reject")

    vote_result = "approved" if approve_count > reject_count else "rejected"

    print(f"\nVote result: {approve_count} approve, {reject_count} reject → {vote_result.upper()}")

    # Create round data
    round_data = {
        "round_number": round_number,
        "quest_number": game.current_quest,
        "team_size_required": required_size,
        "leader": game.current_leader,
        "proposed_team": proposed_team,
        "votes": votes,
        "vote_result": vote_result,
        "consecutive_rejections": game.consecutive_rejections + 1 if vote_result == "rejected" else 0
    }

    if vote_result == "rejected":
        game.consecutive_rejections += 1

        # Check for auto-loss (5 rejections)
        if game.consecutive_rejections >= 5:
            print("\n5 consecutive rejections! Evil wins!")
            return "evil_wins"

        # Rotate leader and try again
        game.rotate_leader()
        round_data["quest_outcome"] = None
        game.rounds.append(round_data)
        game.update_public_log(round_data)

        return "rejected"

    # Reset consecutive rejections on approval
    game.consecutive_rejections = 0

    # Phase 4: Quest execution
    print(f"\n=== QUEST EXECUTION ===\n")

    quest_cards = collect_quest_cards(game, interface, agents, round_number, proposed_team)

    # Count results
    success_count = sum(1 for c in quest_cards.values() if c == "success")
    fail_count = sum(1 for c in quest_cards.values() if c == "fail")

    quest_result = "success" if fail_count == 0 else "fail"

    print(f"\nQuest result: {success_count} success, {fail_count} fail → {quest_result.upper()}")

    # Update quest score
    if quest_result == "success":
        game.quest_score["good"] += 1
    else:
        game.quest_score["evil"] += 1

    # Add quest outcome to round data
    round_data["quest_outcome"] = {
        "success_cards": success_count,
        "fail_cards": fail_count,
        "result": quest_result
    }

    # Save full round data (with quest cards played by each player)
    full_round_data = round_data.copy()
    full_round_data["quest_cards_played"] = quest_cards

    # Update logs
    game.rounds.append(round_data)
    game.update_public_log(round_data)
    game.update_full_log(full_round_data)

    # Move to next quest
    game.current_quest += 1
    game.rotate_leader()

    # Check win conditions
    if game.quest_score["good"] >= 3:
        return "good_wins_quests"
    elif game.quest_score["evil"] >= 3:
        return "evil_wins"

    return "continue"


def main():
    """Run a full game of Avalon."""

    print("="*60)
    print(" THE RESISTANCE: AVALON")
    print("="*60)

    # Create output directory for this game
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir = os.path.join("outputs", f"game-{timestamp}")
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    print(f"\nGame outputs will be saved to: {output_dir}")

    # Initialize game
    game = AvalonGame(output_dir=output_dir)
    interface = AgentInterface(output_dir=output_dir)

    # Create agents for each player
    agents = {player: LLMAgent(player) for player in game.players}

    print(f"\nSeating order: {', '.join(game.seating_order)}")
    print(f"Initial leader: {game.current_leader}")
    print(f"Quest score: Good {game.quest_score['good']} - {game.quest_score['evil']} Evil\n")

    # Main game loop
    game_result = None
    while game_result is None:
        result = run_quest_round(game, interface, agents)

        if result == "rejected":
            print("\nTeam rejected. Moving to next leader...\n")
            continue
        elif result == "continue":
            print(f"\nQuest score: Good {game.quest_score['good']} - {game.quest_score['evil']} Evil\n")
            continue
        else:
            game_result = result
            break

    # Handle end game
    print(f"\n{'='*60}")
    if game_result == "good_wins_quests":
        print("GOOD has won 3 quests!")
        print("\n=== ASSASSINATION PHASE ===")
        print("TODO: Implement assassination phase")
        # TODO: Assassin tries to identify Merlin
    elif game_result == "evil_wins":
        print("EVIL WINS!")

    print(f"{'='*60}\n")
    print("Game complete! Check game logs for full details.")


if __name__ == "__main__":
    main()
