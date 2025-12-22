import json
import random
from game_constants import *  # incl. argparse, time, Path (from pathlib), colored (from termcolor)
from game_status_checks import is_game_over, is_voted_out, is_time_to_vote, \
    all_players_joined, get_is_ai
from llm_players.factory import llm_player_factory
from llm_players.llm_constants import GAME_DIR_KEY, VOTING_WAITING_TIME, MAX_TIME_TO_WAIT


OPERATOR_COLOR = "yellow"  # the person running this file is the "operator" of the model
LLM_PLAYER_LOADED_MESSAGE = "The LLM PLayer was loaded successfully, " \
                            "now waiting for all other players to join..."
ALL_PLAYERS_JOINED_MESSAGE = "All players have joined, now the game can start."
LLM_VOTE_MESSAGE_FORMAT = "The LLM player has voted for: {}"
GAME_ENDED_MESSAGE = "Game has ended, without being voted out!"
GET_LLM_PLAYER_NAME_MESSAGE = "This game has multiple LLM players, which one you want to run now?"
ELIMINATED_MESSAGE = "This LLM player was eliminated from the game..."


# global variable
game_dir = Path()  # will be updated in get_llm_player


def get_llm_player():
    global game_dir
    game_dir = get_game_dir_from_argv()
    with open(game_dir / GAME_CONFIG_FILE) as f:
        config = json.load(f)
    llm_players_configs = [player for player in config[PLAYERS_KEY_IN_CONFIG] if player["is_llm"]]
    if not llm_players_configs:
        raise ValueError("No LLM player configured in this game")
    elif len(llm_players_configs) == 1:
        player_config = llm_players_configs[0]
    else:
        player_name = get_player_name_from_user([player["name"] for player in llm_players_configs],
                                                GET_LLM_PLAYER_NAME_MESSAGE, OPERATOR_COLOR)
        player_config = [player for player in llm_players_configs
                         if player["name"] == player_name][0]
    player_config[GAME_DIR_KEY] = game_dir
    llm_player = llm_player_factory(player_config)
    (game_dir / PERSONAL_STATUS_FILE_FORMAT.format(llm_player.name)).write_text(JOINED)
    return llm_player


def read_messages_from_file(message_history, file_name, num_read_lines):
    with open(game_dir / file_name, "r", encoding='utf-8') as f:
        lines = f.readlines()[num_read_lines:]
    message_history.extend(lines)
    return len(lines)


def wait_writing_time(player, message):
    if player.num_words_per_second_to_wait > 0:
        num_words = len(message.split())
        # Simple: 1 second per word
        time_to_wait = num_words * 1.0
        time_to_wait = min(time_to_wait, MAX_TIME_TO_WAIT)
        time.sleep(time_to_wait)


def eliminate(player):
    # currently doesn't use player, but maybe in the future we can use player.logger for example
    print(colored(ELIMINATED_MESSAGE, OPERATOR_COLOR))


def get_vote_from_llm(player, message_history):
    """
    Social Turing Test: AI vote is always random and silent.
    The LLM does not decide who to vote for - the system randomly selects a human player.
    """
    candidate_vote_names = (game_dir / REMAINING_PLAYERS_FILE).read_text().splitlines()
    candidate_vote_names.remove(player.name)  # AI cannot vote for itself
    
    # Always use random voting for Social Turing Test
    vote = random.choice(candidate_vote_names)
    player.logger.log(MODEL_RANDOMLY_VOTED_LOG, vote)
    print(colored(f"AI voting randomly (silent): {vote}", OPERATOR_COLOR))
    update_vote(vote, player)


def update_vote(voted_name, player):
    time.sleep(VOTING_WAITING_TIME)
    with open(game_dir / PERSONAL_VOTE_FILE_FORMAT.format(player.name), "a") as f:
        f.write(voted_name + "\n")
    print(colored(LLM_VOTE_MESSAGE_FORMAT.format(voted_name), OPERATOR_COLOR))


def add_message_to_game(player, message_history):
    # Social Turing Test: no nighttime restrictions, AI can always chat during discussion phase
    # FIX: Check BEFORE generating to prevent race condition with voting phase
    if is_time_to_vote(game_dir):
        return False  # Voting has started, don't generate message
    
    message = player.generate_message(message_history).strip()
    
    # Check again after generation (in case voting started during generation)
    if is_time_to_vote(game_dir):
        return False  # Voting started while generating, drop message
    
    if message:
        # artificially making the model taking time to write the message
        wait_writing_time(player, message)
        # Final check after waiting
        if is_time_to_vote(game_dir):
            return False  # Voting started while waiting, drop message
        formatted_message = format_message(player.name, message)
        with open(game_dir / PERSONAL_CHAT_FILE_FORMAT.format(player.name), "a") as f:
            f.write(formatted_message)
        # NOTE: Do NOT append to message_history here - it will be read from file in main loop
        # to avoid duplication
        print(colored(MODEL_CHOSE_TO_USE_TURN_LOG, OPERATOR_COLOR))
        return True  # message was sent
    else:
        print(colored(MODEL_CHOSE_TO_PASS_TURN_LOG, OPERATOR_COLOR))
        return False  # no message sent


def end_game(eliminated: bool):
    if not eliminated:
        print(colored(GAME_ENDED_MESSAGE, OPERATOR_COLOR))


def main():
    player = get_llm_player()
    print(colored(LLM_PLAYER_LOADED_MESSAGE, OPERATOR_COLOR))
    player.logger.log("AGENT_LIFECYCLE", "Agent initialized, waiting for players to join")
    
    while not all_players_joined(game_dir):
        continue
    
    print(colored(ALL_PLAYERS_JOINED_MESSAGE, OPERATOR_COLOR))
    player.logger.log("AGENT_LIFECYCLE", "All players joined, game starting")
    
    message_history = []
    num_read_lines_manager = num_read_lines_daytime = 0
    eliminated = False
    iteration_count = 0
    voting_wait_start = None
    VOTING_TIMEOUT = 300  # 5 minutes max wait for voting
    
    try:
        while not is_game_over(game_dir):
            iteration_count += 1
            player.logger.log("AGENT_HEARTBEAT", f"Loop iteration {iteration_count} at {get_current_timestamp()}")
            
            # Read new messages
            new_manager_lines = read_messages_from_file(
                message_history, PUBLIC_MANAGER_CHAT_FILE, num_read_lines_manager)
            new_daytime_lines = read_messages_from_file(
                message_history, PUBLIC_DAYTIME_CHAT_FILE, num_read_lines_daytime)
            num_read_lines_manager += new_manager_lines
            num_read_lines_daytime += new_daytime_lines
            
            if new_manager_lines > 0 or new_daytime_lines > 0:
                player.logger.log("AGENT_STATUS", 
                    f"Read {new_manager_lines} manager messages, {new_daytime_lines} daytime messages. "
                    f"Total history: {len(message_history)} lines")
            
            # Check elimination
            if is_voted_out(player.name, game_dir):
                player.logger.log("AGENT_LIFECYCLE", "Agent was voted out")
                eliminate(player)
                eliminated = True
                break
            
            # Handle voting phase
            if is_time_to_vote(game_dir):
                if voting_wait_start is None:
                    voting_wait_start = time.time()
                    player.logger.log("AGENT_STATUS", "Entering voting wait loop")
                
                # Check timeout
                if time.time() - voting_wait_start > VOTING_TIMEOUT:
                    player.logger.log("AGENT_ERROR", 
                        f"Voting timeout exceeded ({VOTING_TIMEOUT}s) - breaking out")
                    break
                
                # Wait for voting to end
                time.sleep(0.5)
                continue
            else:
                # Reset voting wait tracker when not in voting phase
                if voting_wait_start is not None:
                    player.logger.log("AGENT_STATUS", "Exited voting phase")
                    voting_wait_start = None
                
                # Try to generate and send message
                player.logger.log("AGENT_STATUS", "Attempting to generate message")
                try:
                    message_was_sent = add_message_to_game(player, message_history)
                    
                    if message_was_sent:
                        player.logger.log("AGENT_STATUS", "Message sent successfully, refreshing history")
                        # Refresh history after sending
                        new_manager = read_messages_from_file(
                            message_history, PUBLIC_MANAGER_CHAT_FILE, num_read_lines_manager)
                        new_daytime = read_messages_from_file(
                            message_history, PUBLIC_DAYTIME_CHAT_FILE, num_read_lines_daytime)
                        num_read_lines_manager += new_manager
                        num_read_lines_daytime += new_daytime
                        player.logger.log("AGENT_STATUS", 
                            f"After refresh: {new_manager} manager, {new_daytime} daytime messages")
                        continue
                    else:
                        player.logger.log("AGENT_STATUS", "No message sent (decided to wait)")
                        time.sleep(0.5)
                        
                except Exception as e:
                    player.logger.log("AGENT_ERROR", f"Exception in add_message_to_game: {str(e)}")
                    print(colored(f"ERROR: {str(e)}", "red"))
                    time.sleep(1)  # Brief pause before retrying
        
        player.logger.log("AGENT_LIFECYCLE", f"Exited main loop. Game over: {is_game_over(game_dir)}")
        
    except Exception as e:
        player.logger.log("AGENT_FATAL_ERROR", f"Fatal exception in main loop: {str(e)}")
        print(colored(f"FATAL ERROR: {str(e)}", "red"))
        import traceback
        player.logger.log("AGENT_FATAL_ERROR", f"Traceback: {traceback.format_exc()}")
        raise
    
    # Final check: if game ended but we haven't detected elimination yet, check now
    if not eliminated and is_voted_out(player.name, game_dir):
        eliminated = True
        eliminate(player)
        player.logger.log("AGENT_LIFECYCLE", "Detected elimination in final check")
    
    player.logger.log("AGENT_LIFECYCLE", f"Game ended. Eliminated: {eliminated}")
    end_game(eliminated)


if __name__ == '__main__':
    main()
