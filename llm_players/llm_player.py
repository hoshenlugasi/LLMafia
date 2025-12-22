import re
from abc import ABC, abstractmethod
from game_constants import get_role_string, GAME_START_TIME_FILE, PERSONAL_CHAT_FILE_FORMAT, \
    MESSAGE_PARSING_PATTERN, SCHEDULING_DECISION_LOG, MODEL_CHOSE_TO_USE_TURN_LOG, MODEL_CHOSE_TO_PASS_TURN_LOG
from llm_players.llm_constants import turn_task_into_prompt, GENERAL_SYSTEM_INFO, \
    PASS_TURN_TOKEN_KEY, USE_TURN_TOKEN_KEY, WORDS_PER_SECOND_WAITING_KEY, PASS_TURN_TOKEN_OPTIONS, \
    PERSONA_KEY, build_system_prompt
from llm_players.llm_wrapper import LLMWrapper
from llm_players.logger import Logger


class LLMPlayer(ABC):

    TYPE_NAME = None

    def __init__(self, name, is_ai, llm_config, game_dir, **kwargs):
        self.name = name
        self.is_ai = is_ai
        self.role = get_role_string(is_ai)
        self.game_dir = game_dir
        self.logger = Logger(name, game_dir)
        self.pass_turn_token = llm_config[PASS_TURN_TOKEN_KEY]
        self.use_turn_token = llm_config[USE_TURN_TOKEN_KEY]
        self.num_words_per_second_to_wait = llm_config[WORDS_PER_SECOND_WAITING_KEY]
        # Get persona from config, or use None for default
        self.persona_id = llm_config.get(PERSONA_KEY, None)
        # Build personalized system prompt
        self.system_prompt = build_system_prompt(self.persona_id)
        self.llm = LLMWrapper(self.logger, **llm_config)

    def get_system_info_message(self, attention_to_not_repeat=False, only_special_tokens=False):
        system_info = f"Your name is {self.name}. {self.system_prompt}\n"
        chat_room_open_time = (self.game_dir / GAME_START_TIME_FILE).read_text().strip()
        if chat_room_open_time:  # if the game has started, the file isn't empty
            system_info += f"The game's chat room was open at [{chat_room_open_time}].\n"
        
        # Add conversation topic context if available (soft, non-directive)
        from game_constants import CONVERSATION_TOPIC_FILE
        topic_file = self.game_dir / CONVERSATION_TOPIC_FILE
        if topic_file.exists():
            topic = topic_file.read_text().strip()
            if topic:
                system_info += f"\nThe current conversation topic is: {topic}. "
                system_info += "You don't need to stick to it strictly — people may drift naturally.\n"
        if attention_to_not_repeat:
            # Show only AI's own recent messages (not full chat history - that's in the prompt)
            previous_messages = (self.game_dir / PERSONAL_CHAT_FILE_FORMAT.format(self.name)
                                 ).read_text().splitlines()
            if previous_messages:
                system_info += f"\nFor reference, here are a few of your recent messages:\n"
                # Show only last 3 messages to keep it minimal
                for message in previous_messages[-3:]:
                    matcher = re.match(MESSAGE_PARSING_PATTERN, message)
                    if not matcher:
                        continue
                    message_content = matcher.group(5)  # depends on MESSAGE_PARSING_PATTERN
                    system_info += f"  • \"{message_content}\"\n"
                
                system_info += "\nWhen deciding what to say next, avoid repeating the same wording or reaction.\n"
        if only_special_tokens:
            system_info += f"You can ONLY respond with one of two possible outputs:\n" \
                           f"{self.pass_turn_token} - indicating your character in the game " \
                           f"should wait and not send a message in the current timing;\n" \
                           f"{self.use_turn_token} - indicating your character in the game should " \
                           f"send a message to the public chat now.\n\n" \
                           f"You must NEVER output any other text, explanations, or variations " \
                           f"of these tokens. Only these exact tokens are allowed: " \
                           f"{self.pass_turn_token} or {self.use_turn_token}.\n"
        return system_info

    @abstractmethod
    def should_generate_message(self, context):
        raise NotImplementedError()

    @abstractmethod
    def generate_message(self, message_history):
        raise NotImplementedError()
    
    def trim_message_if_too_long(self, message, max_words=10):
        """Silent backstop: trim message if it exceeds max_words"""
        words = message.split()
        if len(words) > max_words:
            return " ".join(words[:max_words])
        return message

    def interpret_scheduling_decision(self, decision):
        if not decision:
            generate = False
        elif self.pass_turn_token in decision:
            generate = False
        elif self.use_turn_token in decision:
            generate = True
        # for more robustness:
        elif any([option in decision for option in PASS_TURN_TOKEN_OPTIONS]):
            generate = False
        else:
            generate = True
        if generate:
            self.logger.log(SCHEDULING_DECISION_LOG, MODEL_CHOSE_TO_USE_TURN_LOG)
        else:
            self.logger.log(SCHEDULING_DECISION_LOG, MODEL_CHOSE_TO_PASS_TURN_LOG)
        return generate

    def get_vote(self, message_history, candidate_vote_names):
        task = f"From the following remaining players, which player you want to vote for " \
               f"to eliminate? Base your answer on the conversation as seen in the message " \
               f"history, and especially on what you ({self.name}) said. " \
               f"Reply with only one name from the list, and nothing but that name: "
        task += ", ".join(candidate_vote_names)
        prompt = turn_task_into_prompt(task, message_history)
        system_info = self.get_system_info_message()
        self.logger.log("prompt for get_vote", prompt)
        self.logger.log("system_info for get_vote", system_info)
        vote = self.llm.generate(prompt,False, system_info)
        self.logger.log("generated vote in get_vote", vote)
        return vote
