from termcolor import colored
from game_constants import get_game_dir_from_argv, METRICS_TO_SCORE, DEFAULT_SCORE_LOW_BOUND, \
    DEFAULT_SCORE_HIGH_BOUND, SURVEY_QUESTION_FORMAT, METRIC_NAME_AND_SCORE_DELIMITER, \
    PERSONAL_SURVEY_FILE_FORMAT, get_player_name_and_real_name_from_user, MANAGER_COLOR, \
    NUMERIC_SURVEY_QUESTION_FORMAT, NO_LLM_IN_GAME_MESSAGE, \
    ASK_USER_FOR_COMMENTS_MESSAGE, SURVEY_COMMENTS_TITLE, THANK_YOU_GOODBYE_MESSAGE, \
    PLAYER_NAMES_FILE, LLM_LOG_FILE_FORMAT

def get_llm_player_name(game_dir):
    for player_name in (game_dir / PLAYER_NAMES_FILE).read_text().splitlines():
        if (game_dir / LLM_LOG_FILE_FORMAT.format(player_name)).exists():
            return player_name
    return None

def ask_player_for_numeric_rank(llm_player_name, metric, low_bound=DEFAULT_SCORE_LOW_BOUND,
                                high_bound=DEFAULT_SCORE_HIGH_BOUND):
    print(colored(SURVEY_QUESTION_FORMAT.format(llm_player_name), MANAGER_COLOR),
          colored(metric + "?", MANAGER_COLOR, attrs=["bold"]))
    answer = ""
    while not (answer.isnumeric() and (low_bound <= int(answer) <= high_bound)):
        answer = input(colored(NUMERIC_SURVEY_QUESTION_FORMAT.format(low_bound, high_bound),
                               MANAGER_COLOR))
    return answer

def run_survey_about_llm_player(game_dir, name):
    print()
    llm_player_name = get_llm_player_name(game_dir)
    if llm_player_name:
        # Simply remind who the AI was (they already know from end of game)
        print(colored(f"\nReminder: The AI player was ", MANAGER_COLOR),
              colored(llm_player_name, MANAGER_COLOR, attrs=["bold"]))
        print(colored("Please rate the AI's performance:\n", MANAGER_COLOR))
        
        for metric in METRICS_TO_SCORE:
            answer = ask_player_for_numeric_rank(llm_player_name, metric)
            print()
            with open(game_dir / PERSONAL_SURVEY_FILE_FORMAT.format(name), "a") as f:
                f.write(metric + METRIC_NAME_AND_SCORE_DELIMITER + answer + "\n")
    else:
        print(colored(NO_LLM_IN_GAME_MESSAGE + "\n", MANAGER_COLOR))
    comments = input(colored(ASK_USER_FOR_COMMENTS_MESSAGE, MANAGER_COLOR)).strip()
    with open(game_dir / PERSONAL_SURVEY_FILE_FORMAT.format(name), "a") as f:
        f.write(SURVEY_COMMENTS_TITLE + "\n" + comments + "\n")
    print(colored("\n" + THANK_YOU_GOODBYE_MESSAGE, MANAGER_COLOR))

def main():
    game_dir = get_game_dir_from_argv()
    name, _ = get_player_name_and_real_name_from_user(game_dir)
    run_survey_about_llm_player(game_dir, name)

if __name__ == '__main__':
    main()
