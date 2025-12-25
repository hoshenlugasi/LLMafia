import re
from game_constants import REMAINING_PLAYERS_FILE, GAME_MANAGER_NAME, MESSAGE_PARSING_PATTERN
from llm_players.llm_constants import turn_task_into_prompt, SCHEDULE_THEN_GENERATE_TYPE, \
    make_more_human_like, TALKATIVE_PROMPT, QUIETER_PROMPT
from llm_players.llm_player import LLMPlayer
from llm_players.llm_wrapper import LLMWrapper


def no_one_has_talked_yet_in_current_phase(message_history):
    if not message_history:
        return True
    matcher = re.match(MESSAGE_PARSING_PATTERN, message_history[-1])
    if not matcher:
        return True
    name = matcher.group(4)  # depends on MESSAGE_PARSING_PATTERN
    return name == GAME_MANAGER_NAME


class ScheduleThenGeneratePlayer(LLMPlayer):

    TYPE_NAME = SCHEDULE_THEN_GENERATE_TYPE

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # scheduler_kwargs = kwargs.get("scheduler_kwargs", kwargs)
        # self.scheduler = LLMWrapper(**scheduler_kwargs)
        self.scheduler = self.llm  # using the same one for generation...
        self.message_in_progress = False  # Prevent duplicate messages during generation

    def should_generate_message(self, message_history):
        # Prevent duplicate messages: if already generating a message, return False
        if self.message_in_progress:
            self.logger.log("should_generate_message", "BLOCKED: message already in progress")
            return False
        
        if no_one_has_talked_yet_in_current_phase(message_history):
            return False
        prompt = self.create_scheduling_prompt(message_history)
        self.logger.log("prompt in should_generate_message", prompt)
        decision = self.scheduler.generate(
            prompt, True, self.get_system_info_message(only_special_tokens=True))
        self.logger.log("decision in should_generate_message", decision)
        return self.interpret_scheduling_decision(decision)

    def generate_message(self, message_history):
        if self.should_generate_message(message_history):
            # Lock to prevent duplicate message generation
            self.message_in_progress = True
            try:
                prompt = self.create_generation_prompt(message_history)
                self.logger.log("prompt in generate_message", prompt)
                message = self.llm.generate(
                    prompt, False, self.get_system_info_message(attention_to_not_repeat=True))
                # Silent backstop: trim if too long (10 words max)
                message = self.trim_message_if_too_long(message, max_words=10)
                # Pass message_history for smart capitalization matching
                message = make_more_human_like(message, message_history)
                return message
            finally:
                # Always unlock, even if an error occurs
                self.message_in_progress = False
                self.logger.log("generate_message", "UNLOCKED: message generation complete")
        else:
            return ""

    def talkative_scheduling_prompt_modifier(self, message_history):
        if not message_history:
            return TALKATIVE_PROMPT
        
        all_players = (self.game_dir / REMAINING_PLAYERS_FILE).read_text().splitlines()
        players_counts = {player: 0 for player in all_players}
        
        phases_ended_count = 0
        for message in message_history[::-1]:
            if f"] {GAME_MANAGER_NAME}: " in message:
                if "voted for" in message:
                    continue
                if "has ended" in message:
                    phases_ended_count += 1
                    if phases_ended_count >= 2:
                        break
                    continue
            
            matcher = re.match(MESSAGE_PARSING_PATTERN, message)
            if matcher:
                speaker = matcher.group(4)
                if speaker in players_counts:
                    players_counts[speaker] += 1
        
        all_player_messages = sum(players_counts.values())
        if not all_player_messages or players_counts[self.name] / all_player_messages < 1 / len(all_players):
            return TALKATIVE_PROMPT
        else:
            return QUIETER_PROMPT

    def create_scheduling_prompt(self, message_history):
        mentioned = False
        asked_question = False
        
        if message_history:
            # Track if AI was recently active in conversation (for follow-up detection)
            ai_was_recently_active = False
            for message in message_history[-3:]:  # Check last 3 messages
                matcher = re.match(MESSAGE_PARSING_PATTERN, message)
                if matcher:
                    speaker = matcher.group(4)
                    if speaker == self.name:
                        ai_was_recently_active = True
                        break
            
            # Check last 1-2 messages for direct mentions
            recent_messages = message_history[-2:]
            
            for message in recent_messages:
                message_lower = message.lower()
                
                # Parse and filter by speaker
                matcher = re.match(MESSAGE_PARSING_PATTERN, message)
                if matcher:
                    speaker = matcher.group(4)
                    # Skip messages from Game Manager or self
                    if speaker in {GAME_MANAGER_NAME, self.name}:
                        continue
                
                # Direct mention by name with question words
                if self.name.lower() in message_lower:
                    mentioned = True
                    # Check for question words if mentioned
                    question_words = ["where", "what", "who", "how", "why", "when", "which"]
                    for qword in question_words:
                        if qword in message_lower:
                            asked_question = True
                            break
            
            # Follow-up question detection: only when AI was recently active
            if ai_was_recently_active and recent_messages:
                last_message = recent_messages[-1]
                last_message_lower = last_message.lower()
                
                # Parse speaker
                matcher = re.match(MESSAGE_PARSING_PATTERN, last_message)
                if matcher:
                    speaker = matcher.group(4)
                    # Only check if it's from another player (not GM or self)
                    if speaker not in {GAME_MANAGER_NAME, self.name}:
                        # Check if it's a question (with or without "?")
                        is_question = (
                            "?" in last_message_lower or
                            any(last_message_lower.strip().startswith(qw) for qw in 
                                ["where", "what", "when", "why", "who", "how", "which"]) or
                            last_message_lower.strip() in ["really", "really?", "why", "how come"]
                        )
                        
                        # Check for follow-up patterns
                        is_follow_up = any(
                            last_message_lower.strip().startswith(p) for p in 
                            ["and ", "so ", "but ", "then ", "really", "why", "how come"]
                        )
                        
                        # If it's a question or follow-up after AI spoke, treat as directed to AI
                        if is_question or is_follow_up:
                            asked_question = True
                            self.logger.log("follow_up_detected", 
                                f"Detected follow-up: ai_active={ai_was_recently_active}, "
                                f"is_question={is_question}, is_follow_up={is_follow_up}")
        
        task = f"Do you want to send a message to the group chat now, or do you prefer to wait " \
               f"for now and see what messages others will send? " \
               f"Remember to choose to send a message only if your contribution to the " \
               f"discussion in the current time will be meaningful enough. " \

        if mentioned:
            task += f"Note: Your name was mentioned recently. Consider responding if it feels natural. "
        else:
            if asked_question:
                task += f"Note: Someone may be asking something. Consider responding if it feels natural. "
            task += f"{self.talkative_scheduling_prompt_modifier(message_history).strip()} "
        
        task += f"Reply only with `{self.use_turn_token}` if you want to send a message now, " \
               f"or only with `{self.pass_turn_token}` if you want to wait for now, " \
               f"based on your decision! "
        
        return turn_task_into_prompt(task, message_history)

    def create_generation_prompt(self, message_history):
        task = f"Add a very short message to the game's chat. " \
               f"Be specific and keep it relevant to the current situation, " \
               f"according to the last messages and the game's status. " \
               f"Your message should only be one short sentence! " \
               f"Don't add a message that you've already added (in the chat history)! " \
               f"It is very important that you don't repeat yourself! " \
               f"Match your style of message to the other player's message style, " \
               f"with more emphasis on more recent messages.\n"
        
        return turn_task_into_prompt(task, message_history)
