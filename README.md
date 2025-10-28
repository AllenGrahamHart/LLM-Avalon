# Avalon LLM Multi-Agent Game

A framework for having 5 LLMs play The Resistance: Avalon together.

## Architecture Overview

### Core Files

1. **game_engine.py** - Game state management
   - Role assignment (random)
   - Seating order (random)
   - Leader rotation
   - Log management
   - Win condition checking

2. **agent_interface.py** - LLM prompting system
   - Builds prompts for each agent with appropriate context
   - Parses responses (votes, quest cards, proposals)
   - Manages conversation and private thought logs
   - Provides role-specific information to each agent

3. **game_loop.py** - Main game orchestration
   - Runs discussion rounds (3 turns per phase)
   - Collects votes and decisions
   - Updates game logs
   - Handles quest execution

### Game Flow

Each quest round follows this structure:

```
1. Pre-proposal Discussion (3 rounds, all players speak)
   ↓
2. Each player writes private thoughts + votes
   ↓
3. Count votes → If rejected, rotate leader and repeat
   ↓
4. If approved: Post-approval discussion (3 rounds)
   ↓
5. Quest team members write private thoughts + play quest cards
   ↓
6. Reveal quest outcome
   ↓
7. Update logs and check win conditions
```

### Context Given to Each Agent

When prompting an agent, they receive:

1. **Official game rules** (from Official_Rules.md)
2. **Their role** (Merlin, Assassin, Loyal Servant, Minion)
3. **Their private knowledge** (who they know based on role)
4. **Public game log** (quest history, votes, outcomes)
5. **Their previous private thoughts** (memory of their reasoning)
6. **Current round's conversation** (what's been said so far)

This keeps token usage manageable while providing sufficient context.

### File Structure

```
├── Official_Rules.md                    # Game rules
├── game_engine.py                       # Core game logic
├── agent_interface.py                   # LLM prompting
├── game_loop.py                         # Main orchestration
├── requirements.txt                     # Python dependencies
├── .env.example                         # Example environment variables
│
└── outputs/                             # Game outputs (gitignored)
    └── game-YYYYMMDD-HHMMSS/           # Timestamped game directory
        ├── public_game_log.json         # Public information (visible to all)
        ├── full_game_log.json           # Complete information (includes roles)
        ├── conversation_log.txt         # Public discussion only
        ├── full_conversation_log.txt    # Public + private thoughts per message
        └── Player*_private_thoughts.txt # Private reasoning per player
```

Each game run creates a new timestamped directory in `outputs/` with all game logs.

## LLM Integration

The `LLMAgent` class in `game_loop.py` is integrated with **Anthropic's Claude API** using **Claude 3 Haiku** (the cheapest model for testing).

```python
class LLMAgent:
    def __init__(self, name: str, api_key: str = None):
        self.name = name
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-haiku-20240307"  # Cheapest model

    def get_response(self, prompt: str) -> str:
        message = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
```

To switch to a different model (e.g., Claude 3.5 Sonnet for better performance), change the `self.model` variable.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your Anthropic API key:
```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your actual API key
# ANTHROPIC_API_KEY=your-actual-api-key-here
```

The `.env` file is gitignored to keep your API key safe.

## Running the Game

```bash
python3 game_loop.py
```

The game uses **Claude 3 Haiku** (the cheapest Anthropic model) for testing.

### Cost Estimate

Claude 3 Haiku pricing:
- **$0.25** per million input tokens
- **$1.25** per million output tokens

A typical 5-player game with 3-5 quest rounds costs approximately **$0.10-0.30** depending on conversation length.

## Key Design Decisions

1. **Token Management**: Agents only receive recent conversation + their own past thoughts, not the full game history

2. **Information Hiding**: Public log vs Full log separation ensures proper game mechanics

3. **XML Tags**: Used for parsing structured decisions (`<VOTE>`, `<QUEST_CARD>`, etc.)

4. **Sequential Discussion**: Simple rotating speaker order (3 rounds) keeps conversations manageable

5. **Private Thoughts**: Agents reason about other players before making decisions, creating richer gameplay

## Current Status

**Fully Implemented:**
- ✅ LLM API integration with Claude 3 Haiku
- ✅ Core game engine with role assignment
- ✅ Discussion rounds with agent conversations
- ✅ Voting system
- ✅ Quest card playing
- ✅ Public and private game logs
- ✅ Player private thoughts and memory

**TODO:**
- [ ] Implement leader's team proposal via LLM (currently uses placeholder: first N players)
- [ ] Implement assassination phase (when good wins 3 quests, Assassin tries to identify Merlin)
- [ ] Add optional roles (Percival, Morgana, Mordred, Oberon)
- [ ] Add game replay/analysis tools
- [ ] Improve agent reasoning and strategy

## Example Output Files

After running a game, check the `outputs/game-<timestamp>/` directory to see:
- `public_game_log.json` - Game history visible to all players
- `full_game_log.json` - Complete game history including roles and quest cards
- `conversation_log.txt` - Public messages only (what players see)
- `full_conversation_log.txt` - Both private thoughts and public messages for each discussion turn
- `Player*_private_thoughts.txt` - Each player's reasoning process (voting, quest cards, discussions)
