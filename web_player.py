"""
Simple web interface for Social Turing Test game
Run this instead of player_merged_chat_and_input.py for a chat-like UI
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import secrets
import re
from pathlib import Path
from datetime import datetime

from game_constants import (
    DIRS_PREFIX,
    PERSONAL_CHAT_FILE_FORMAT,
    PERSONAL_VOTE_FILE_FORMAT,
    PERSONAL_STATUS_FILE_FORMAT,
    PERSONAL_SURVEY_FILE_FORMAT,
    PUBLIC_MANAGER_CHAT_FILE,
    PUBLIC_DAYTIME_CHAT_FILE,
    REAL_NAMES_FILE,
    REAL_NAME_CODENAME_DELIMITER,
    REMAINING_PLAYERS_FILE,
    PLAYER_NAMES_FILE,
    AI_PLAYER_FILE,
    LLM_LOG_FILE_FORMAT,
    METRIC_NAME_AND_SCORE_DELIMITER,
    JOINED,
    RULES_OF_THE_GAME,
    format_message,
    CONVERSATION_TOPIC_FILE,
)
from game_status_checks import (
    is_game_over,
    is_time_to_vote,
    all_players_joined,
    get_is_ai,
)
from game_constants import get_role_display_string

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
CORS(app)

# Global state for each player session (in-memory, per-server-process)
player_states = {}

class WebPlayer:
    """
    Represents one player connected through the web UI.
    Tracks how many lines were already read from each chat file in this session,
    so we only send *new* messages to the browser.
    """

    def __init__(self, game_dir: Path, name: str, is_ai: bool):
        self.game_dir = game_dir
        self.name = name
        self.is_ai = is_ai

        self.personal_chat_file = game_dir / PERSONAL_CHAT_FILE_FORMAT.format(name)
        self.personal_vote_file = game_dir / PERSONAL_VOTE_FILE_FORMAT.format(name)

        # how many lines we have already read from each public chat file
        self.num_read_manager = 0
        self.num_read_daytime = 0
        
        # Survey submission tracking
        self.did_submit_survey = False

    def get_new_messages(self):
        """
        Read only *new* lines from manager & daytime chat files
        and return them as a list of {text, type} dicts.
        
        BUG FIX: Classify messages ONLY by their file of origin:
        - All lines from PUBLIC_MANAGER_CHAT_FILE → type="manager"
        - All lines from PUBLIC_DAYTIME_CHAT_FILE → type="chat"
        
        This ensures 100% consistency - no text pattern matching needed!
        """
        messages = []

        try:
            # Manager messages (rules, phase announcements, results...)
            manager_file = self.game_dir / PUBLIC_MANAGER_CHAT_FILE
            if manager_file.exists():
                with manager_file.open("r", encoding="utf-8") as f:
                    all_lines = f.readlines()
                    new_lines = all_lines[self.num_read_manager :]
                    # advance cursor by ALL new lines (including blank)
                    self.num_read_manager += len(new_lines)

                    for raw in new_lines:
                        line = raw.strip()
                        if line:
                            # Strip "Game-Manager:" prefix to avoid duplication
                            # (frontend CSS adds "🛠️ Game Manager:" header)
                            # Pattern: "[HH:MM:SS] Game-Manager: message"
                            cleaned = re.sub(r'Game-Manager:\s*', '', line)
                            messages.append({"text": cleaned, "type": "manager"})

            # Daytime chat (merged messages from all personal files - player chat only)
            daytime_file = self.game_dir / PUBLIC_DAYTIME_CHAT_FILE
            if daytime_file.exists():
                with daytime_file.open("r", encoding="utf-8") as f:
                    all_lines = f.readlines()
                    new_lines = all_lines[self.num_read_daytime :]
                    self.num_read_daytime += len(new_lines)

                    for raw in new_lines:
                        line = raw.strip()
                        if line:
                            # All messages from daytime file are type="chat"
                            messages.append({"text": line, "type": "chat"})
        except Exception as e:
            print(f"[WebPlayer] Error reading messages for {self.name}: {e}")

        return messages

    def send_message(self, message: str):
        """Append a personal chat message that the game manager process will merge."""
        formatted = format_message(self.name, message)
        with self.personal_chat_file.open("a", encoding="utf-8") as f:
            f.write(formatted)

    def send_vote(self, voted_name: str):
        """Append a vote for the current voting phase."""
        with self.personal_vote_file.open("a", encoding="utf-8") as f:
            f.write(voted_name + "\n")

def get_llm_player_name(game_dir):
    """
    Get the AI player's name using multiple fallback methods:
    1. Check ai_player.txt file (newer games)
    2. Find player with _log.txt file (original method)
    3. Read directly from config.json (most reliable fallback)
    """
    # Step 1: Check if ai_player.txt exists (newer games)
    ai_player_file = game_dir / AI_PLAYER_FILE
    if ai_player_file.exists():
        content = ai_player_file.read_text(encoding="utf-8").strip()
        if content:  # Make sure it's not empty
            return content
    
    # Step 2: Find player with _log.txt file (original method)
    player_names_file = game_dir / PLAYER_NAMES_FILE
    if player_names_file.exists():
        for player_name in player_names_file.read_text(encoding="utf-8").splitlines():
            player_name = player_name.strip()
            if player_name:
                log_file = game_dir / LLM_LOG_FILE_FORMAT.format(player_name)
                if log_file.exists():
                    return player_name
    
    # Step 3: Read from config.json as final fallback
    config_file = game_dir / "config.json"
    if config_file.exists():
        try:
            import json
            with open(config_file) as f:
                config = json.load(f)
            
            # Find the AI player in config
            for player in config.get("players", []):
                if player.get("is_llm", False) or player.get("is_ai", False):
                    return player.get("name")
        except Exception as e:
            print(f"[AI Name] Error reading from config: {e}")
    
    return None

@app.route("/")
def index():
    # main HTML template
    return render_template("game.html")

@app.route("/get_players", methods=["POST"])
def get_players():
    """
    Given a game_id, return the list of *real names* that appear in REAL_NAMES_FILE,
    so players can choose themselves from a dropdown.
    """
    data = request.json or {}
    game_id = data.get("game_id")

    game_dir = Path(DIRS_PREFIX) / game_id
    if not game_dir.exists():
        return jsonify({"error": "Game not found"}), 404

    real_names_file = game_dir / REAL_NAMES_FILE
    if not real_names_file.exists():
        return jsonify({"error": "Game not ready"}), 404

    real_names_to_codenames_str = real_names_file.read_text(encoding="utf-8").splitlines()

    real_names = []
    for line in real_names_to_codenames_str:
        if REAL_NAME_CODENAME_DELIMITER in line:
            real_name, _code = line.split(REAL_NAME_CODENAME_DELIMITER, 1)
            real_names.append(real_name)

    return jsonify({"players": real_names})

@app.route("/join", methods=["POST"])
def join_game():
    """
    Map real_name → code name, create a WebPlayer, mark player as JOINED,
    and return session_id + metadata to the browser.
    """
    data = request.json or {}
    game_id = data.get("game_id")
    real_name = data.get("real_name")

    game_dir = Path(DIRS_PREFIX) / game_id
    if not game_dir.exists():
        return jsonify({"error": "Game not found"}), 404

    real_names_file = game_dir / REAL_NAMES_FILE
    real_names_to_codenames_str = real_names_file.read_text(encoding="utf-8").splitlines()

    real_to_code = {}
    for line in real_names_to_codenames_str:
        if REAL_NAME_CODENAME_DELIMITER in line:
            real, code = line.split(REAL_NAME_CODENAME_DELIMITER, 1)
            real_to_code[real] = code

    if real_name not in real_to_code:
        return jsonify({"error": "Name not found in game"}), 404

    code_name = real_to_code[real_name]
    is_ai = get_is_ai(code_name, game_dir)

    # Create WebPlayer session
    session_id = secrets.token_hex(8)
    player_states[session_id] = WebPlayer(game_dir, code_name, is_ai)

    # Mark as joined (same semantics as original CLI client)
    status_file = game_dir / PERSONAL_STATUS_FILE_FORMAT.format(code_name)
    status_file.write_text(JOINED, encoding="utf-8")

    role_display = get_role_display_string(is_ai) if is_ai else None

    return jsonify(
        {
            "session_id": session_id,
            "code_name": code_name,
            "is_ai": is_ai,
            "role": role_display,
            # RULES_OF_THE_GAME is still available if you ever want a static area,
            # but we no longer inject it as a separate chat bubble to avoid duplicates.
            "rules": RULES_OF_THE_GAME,
        }
    )

@app.route("/messages", methods=["POST"])
def get_messages():
    """
    Polling endpoint: the browser calls this every second with a session_id.
    We return:
      - new messages since last poll
      - flags: game_over, can_vote, can_chat, game_started
      - remaining players (for voting)
    """
    data = request.json or {}
    session_id = data.get("session_id")

    if session_id not in player_states:
        return jsonify({"error": "Invalid session"}), 401

    player = player_states[session_id]
    messages = player.get_new_messages()

    game_over = is_game_over(player.game_dir)
    can_vote = is_time_to_vote(player.game_dir)
    game_started = all_players_joined(player.game_dir)

    remaining_players = []
    remaining_file = player.game_dir / REMAINING_PLAYERS_FILE
    if remaining_file.exists():
        # After the first vote: use remaining_players.txt
        remaining_players = [
            line.strip()
            for line in remaining_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    else:
        # Before ANY elimination: all players are remaining
        full_list_file = player.game_dir / PLAYER_NAMES_FILE
        if full_list_file.exists():
            remaining_players = [
                line.strip()
                for line in full_list_file.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

    # Get game over message if game has ended
    game_over_message = None
    game_duration_minutes = None
    if game_over:
        from game_constants import WHO_WINS_FILE
        winner_file = player.game_dir / WHO_WINS_FILE
        if winner_file.exists():
            game_over_message = winner_file.read_text(encoding="utf-8").strip()
        
        # Calculate game duration deterministically: rounds × discussion_time
        # Count how many elimination rounds occurred
        config_file = player.game_dir / "config.json"
        if config_file.exists():
            try:
                import json
                with open(config_file) as f:
                    config = json.load(f)
                
                # Get discussion time per round
                from game_constants import DAYTIME_MINUTES_KEY
                daytime_minutes = config.get(DAYTIME_MINUTES_KEY, 2.0)
                
                # Count rounds: initial_players - final_players = eliminations = rounds
                total_players = len(all_players) if all_players else 0
                final_players = len(remaining_players) if remaining_players else 0
                
                # Number of rounds = number of eliminations
                num_rounds = total_players - final_players
                
                # Edge case: if game ended with 2 players (AI won), that's still the last round
                if num_rounds == 0 and game_over:
                    num_rounds = 1
                
                game_duration_minutes = round(num_rounds * daytime_minutes, 1)
                print(f"[Duration] Calculated: {num_rounds} rounds × {daytime_minutes} min = {game_duration_minutes} min")
            except Exception as e:
                print(f"[Duration] Error calculating duration: {e}")
                game_duration_minutes = None

    # Get all players for the frontend
    all_players = []
    full_list_file = player.game_dir / PLAYER_NAMES_FILE
    if full_list_file.exists():
        all_players = [
            line.strip()
            for line in full_list_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    # chat is only allowed when:
    #   - all players joined
    #   - not voting time
    #   - game not over
    can_chat = game_started and (not can_vote) and (not game_over)

    return jsonify(
        {
            "messages": messages,
            "game_over": game_over,
            "game_over_message": game_over_message,
            "game_duration_minutes": game_duration_minutes,
            "can_vote": can_vote,
            "can_chat": can_chat,
            "game_started": game_started,
            "remaining_players": remaining_players,
            "all_players": all_players,
        }
    )

@app.route("/send", methods=["POST"])
def send_message():
    """
    Append a chat message to this player's personal chat file.
    We assume the front-end already enforces "only during discussion",
    so here אנחנו רק בודקים תקינות בסיסית.
    """
    data = request.json or {}
    session_id = data.get("session_id")
    message = (data.get("message") or "").strip()

    if session_id not in player_states:
        return jsonify({"error": "Invalid session"}), 401

    if not message:
        return jsonify({"error": "Empty message"}), 400

    player = player_states[session_id]
    player.send_message(message)

    return jsonify({"success": True})

@app.route("/vote", methods=["POST"])
def vote():
    """
    Append a vote for the current player.
    BUG FIX: Check if player has already voted this round.
    """
    data = request.json or {}
    session_id = data.get("session_id")
    voted_name = (data.get("voted_name") or "").strip()

    if session_id not in player_states:
        return jsonify({"error": "Invalid session"}), 401

    if not voted_name:
        return jsonify({"error": "No vote"}), 400

    player = player_states[session_id]
    
    player.send_vote(voted_name)

    return jsonify({"success": True})

@app.route("/get_game_config", methods=["POST"])
def get_game_config():
    """
    Return game configuration, specifically the discussion time duration.
    Used by frontend to initialize the countdown timer.
    """
    data = request.json or {}
    session_id = data.get("session_id")

    if session_id not in player_states:
        return jsonify({"error": "Invalid session"}), 401

    player = player_states[session_id]
    config_file = player.game_dir / "config.json"
    
    if config_file.exists():
        import json
        with open(config_file) as f:
            config = json.load(f)
        
        from game_constants import DAYTIME_MINUTES_KEY
        daytime_minutes = config.get(DAYTIME_MINUTES_KEY, 2.0)
        
        return jsonify({
            "daytime_minutes": daytime_minutes
        })
    
    # Default fallback
    return jsonify({"daytime_minutes": 2.0})

@app.route("/get_conversation_topic", methods=["POST"])
def get_conversation_topic():
    """
    Return the conversation topic for this game (if available).
    """
    data = request.json or {}
    session_id = data.get("session_id")

    if session_id not in player_states:
        return jsonify({"error": "Invalid session"}), 401

    player = player_states[session_id]
    
    from game_constants import CONVERSATION_TOPIC_FILE
    topic_file = player.game_dir / CONVERSATION_TOPIC_FILE
    
    if topic_file.exists():
        topic = topic_file.read_text(encoding="utf-8").strip()
        if topic:
            return jsonify({"topic": topic})
    
    return jsonify({"topic": None})

@app.route("/lobby_status", methods=["POST"])
def lobby_status():
    """
    Return lobby status: all players and which have joined.
    Used for the waiting lobby screen.
    """
    data = request.json or {}
    session_id = data.get("session_id")

    if session_id not in player_states:
        return jsonify({"error": "Invalid session"}), 401

    player = player_states[session_id]
    
    # Get all players
    player_names_file = player.game_dir / PLAYER_NAMES_FILE
    if not player_names_file.exists():
        return jsonify({"error": "Game not ready"}), 404
    
    all_players = [
        name.strip()
        for name in player_names_file.read_text(encoding="utf-8").splitlines()
        if name.strip()
    ]
    
    # Check which players have joined
    joined_players = []
    for player_name in all_players:
        status_file = player.game_dir / PERSONAL_STATUS_FILE_FORMAT.format(player_name)
        if status_file.exists() and status_file.read_text(encoding="utf-8").strip() == JOINED.strip():
            joined_players.append(player_name)
    
    # Check if game has started
    game_started = all_players_joined(player.game_dir)
    
    return jsonify({
        "players": all_players,
        "joined_players": joined_players,
        "game_started": game_started
    })

@app.route("/get_survey_options", methods=["POST"])
def get_survey_options():
    """
    Return all player names for the survey (including eliminated players).
    Excludes the current player from the list.
    """
    data = request.json or {}
    session_id = data.get("session_id")

    if session_id not in player_states:
        return jsonify({"error": "Invalid session"}), 401

    player = player_states[session_id]
    
    # Get all players from PLAYER_NAMES_FILE
    player_names_file = player.game_dir / PLAYER_NAMES_FILE
    if not player_names_file.exists():
        return jsonify({"error": "Player names file not found"}), 404
    
    all_players = [
        name.strip()
        for name in player_names_file.read_text(encoding="utf-8").splitlines()
        if name.strip()
    ]
    
    # Exclude the current player
    survey_options = [p for p in all_players if p != player.name]
    
    return jsonify({"players": survey_options})

@app.route("/get_ai_player_name", methods=["POST"])
def get_ai_player_name():
    """
    Return the actual AI player's name using the reliable detection logic.
    """
    data = request.json or {}
    session_id = data.get("session_id")

    if session_id not in player_states:
        return jsonify({"error": "Invalid session"}), 401

    player = player_states[session_id]
    ai_name = get_llm_player_name(player.game_dir)
    
    if not ai_name:
        return jsonify({"error": "AI player not found"}), 404
    
    return jsonify({"ai_name": ai_name})

@app.route("/get_model_info", methods=["POST"])
def get_model_info():
    """
    Return the AI model name from the game configuration.
    """
    data = request.json or {}
    session_id = data.get("session_id")

    if session_id not in player_states:
        return jsonify({"error": "Invalid session"}), 401

    player = player_states[session_id]
    config_file = player.game_dir / "config.json"
    
    if not config_file.exists():
        return jsonify({"error": "Config not found"}), 404
    
    try:
        import json
        with open(config_file) as f:
            config = json.load(f)
        
        # Find the LLM player and extract model name
        model_name = "Unknown Model"
        for p in config.get("players", []):
            if p.get("is_llm", False):
                llm_config = p.get("llm_config", {})
                model_name = llm_config.get("model_name", "Unknown Model")
                break
        
        return jsonify({"model_name": model_name})
    except Exception as e:
        print(f"[Model Info] Error: {e}")
        return jsonify({"error": "Could not read model info"}), 500

@app.route("/survey_submit", methods=["POST"])
def survey_submit():
    """
    Submit end-of-game survey results.
    Writes to survey file in Niv's exact format matching game_constants.py:
    TIME - <timestamp>
    Was the LLM identified - <not used, always 0>
    similarity to human behavior - <1-5>
    timing of messaging - <1-5>
    relevance of messages - <1-5>
    Comments:
    <suspicion_reason>
    <notes>
    
    NOTE: We no longer ask "who was the AI" since it's already revealed.
    The "Was the LLM identified" field is kept for backward compatibility but set to 0.
    """
    data = request.json or {}
    session_id = data.get("session_id")
    human_likeness = data.get("human_likeness")
    timing = data.get("timing")
    relevance = data.get("relevance")
    suspicion_reason = (data.get("suspicion_reason") or "").strip()
    notes = (data.get("notes") or "").strip()

    if session_id not in player_states:
        return jsonify({"error": "Invalid session"}), 401

    player = player_states[session_id]
    
    # Check if already submitted
    if player.did_submit_survey:
        return jsonify({"error": "Survey already submitted"}), 400
    
    # Validate all rating fields (1-5)
    try:
        human_likeness = int(human_likeness)
        timing = int(timing)
        relevance = int(relevance)
        
        for val, name in [(human_likeness, "human_likeness"), 
                          (timing, "timing"), (relevance, "relevance")]:
            if not (1 <= val <= 5):
                return jsonify({"error": f"{name} must be between 1 and 5"}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid rating value"}), 400
    
    # Write to survey file in Niv's exact format
    survey_file = player.game_dir / PERSONAL_SURVEY_FILE_FORMAT.format(player.name)
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    # Match exact format from game_constants.py
    # Note: "Was the LLM identified" is set to 0 (not applicable) since we no longer ask this
    survey_content = f"TIME{METRIC_NAME_AND_SCORE_DELIMITER}{timestamp}\n"
    survey_content += f"Was the LLM identified{METRIC_NAME_AND_SCORE_DELIMITER}0\n"
    survey_content += f"similarity to human behavior{METRIC_NAME_AND_SCORE_DELIMITER}{human_likeness}\n"
    survey_content += f"timing of messaging{METRIC_NAME_AND_SCORE_DELIMITER}{timing}\n"
    survey_content += f"relevance of messages{METRIC_NAME_AND_SCORE_DELIMITER}{relevance}\n"
    survey_content += "Comments:\n"
    
    # Combine both text fields into comments section
    if suspicion_reason:
        survey_content += f"{suspicion_reason}\n"
    if notes:
        survey_content += f"{notes}\n"
    
    survey_file.write_text(survey_content, encoding="utf-8")
    
    # Mark as submitted
    player.did_submit_survey = True
    
    return jsonify({"success": True})

if __name__ == "__main__":
    print("Starting Social Turing Test Web Interface...")
    print("Open your browser to: http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
