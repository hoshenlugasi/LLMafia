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
        # Social Turing Test: soft speaking frequency boundaries
        if not message_history:
            return "Feel free to speak up naturally when you have something to say."
        
        all_players = (self.game_dir / REMAINING_PLAYERS_FILE).read_text().splitlines()
        players_counts = {player: 0 for player in all_players}
        
        for message in message_history[::-1]:
            # Skip vote messages and phase end messages
            if f"] {GAME_MANAGER_NAME}: " in message:
                if "voted for" in message:
                    continue
                if "has ended" in message:
                    break
            
            # Fix 4: Use regex parsing instead of substring matching
            matcher = re.match(MESSAGE_PARSING_PATTERN, message)
            if matcher:
                speaker = matcher.group(4)
                if speaker in players_counts:
                    players_counts[speaker] += 1
        
        all_player_messages = sum(players_counts.values())
        if not all_player_messages:
            return "Feel free to speak up naturally."
        
        my_ratio = players_counts[self.name] / all_player_messages
        expected_ratio = 1 / len(all_players)
        
        # Soft boundaries - not targeting exact 1/N ratio
        # Slightly tighter boundaries to reduce over-responsiveness
        if my_ratio < expected_ratio:  # Very quiet
            return "You've been quiet - feel free to participate more if you want."
        elif my_ratio > expected_ratio:  # Very active
            return "You've been pretty active - let others have space to talk too."
        else:  # Balanced
            return "Continue participating naturally as feels right."

    def create_scheduling_prompt(self, message_history):
        # Improved: targeted social "you" patterns to reduce false positives
        social_you_patterns = [
            "and you", "what about you", "how about you",
            "you too", "wbu", "you?", "u?"
        ]
        
        mentioned = False
        asked_question = False
        
        if message_history:
            # Track if AI was recently active AND check for legitimate follow-up
            recent_messages = message_history[-3:]  # Check last 3 messages for context
            
            ai_last_message_position = None
            for i in range(len(recent_messages) - 1, -1, -1):  # Start from most recent
                matcher = re.match(MESSAGE_PARSING_PATTERN, recent_messages[i])
                if matcher:
                    speaker = matcher.group(4)
                    if speaker == self.name:
                        ai_last_message_position = i
                        break
            
            for message in recent_messages:
                message_lower = message.lower()
                
                # Fix 2: Parse and filter by speaker
                matcher = re.match(MESSAGE_PARSING_PATTERN, message)
                if matcher:
                    speaker = matcher.group(4)
                    # Skip messages from Game Manager or self
                    if speaker in {GAME_MANAGER_NAME, self.name}:
                        continue
                
                # Direct mention by name
                if self.name.lower() in message_lower:
                    mentioned = True
                    # Check for question words if mentioned
                    question_words = ["where", "what", "who", "how", "why", "when", "which"]
                    for qword in question_words:
                        if qword in message_lower:
                            asked_question = True
                            break
                
                # Fix 1: Improved "you" question detection - only social patterns
                if "?" in message_lower:
                    is_direct_you_ping = (
                        any(p in message_lower for p in social_you_patterns)
                        or message_lower.strip().endswith("you?")
                        or message_lower.strip().endswith("u?")
                    )
                    if is_direct_you_ping:
                        asked_question = True
            
            # NEW: Stricter follow-up question detection
            # Only trigger if AI spoke in the last 1-2 messages AND there's a legitimate follow-up
            if ai_last_message_position is not None and recent_messages:
                # AI must be in the last 2 messages (not 3+ messages ago)
                if ai_last_message_position >= len(recent_messages) - 2:
                    last_message = recent_messages[-1]
                    last_message_lower = last_message.lower()
                    
                    # Parse speaker
                    matcher = re.match(MESSAGE_PARSING_PATTERN, last_message)
                    if matcher:
                        speaker = matcher.group(4)
                        # Only check if it's from another player (not GM or self)
                        if speaker not in {GAME_MANAGER_NAME, self.name}:
                            # Check if it's a direct continuation question
                            is_direct_question = (
                                "?" in last_message_lower and
                                any(last_message_lower.strip().startswith(qw) for qw in 
                                    ["where", "what", "when", "why", "who", "how", "which", "really"])
                            )
                            
                            # Very short follow-ups that are clearly continuing
                            is_short_followup = last_message_lower.strip() in [
                                "why", "why?", "really", "really?", "how come", "how come?",
                                "what", "what?", "where", "where?"
                            ]
                            
                            # Only treat as follow-up if it's clearly asking for more info
                            if is_direct_question or is_short_followup:
                                asked_question = True
                                self.logger.log("follow_up_detected", 
                                    f"Legitimate follow-up: position={ai_last_message_position}, "
                                    f"is_direct_question={is_direct_question}, is_short={is_short_followup}")
        
        task = f"Do you want to send a message now, or wait and see what others say? "
        
        # Soft nudges, not hard requirements
        if asked_question:
            task += f"Note: Someone may be asking you something. Consider responding if it feels natural. "
        elif mentioned:
            task += f"Note: Your name was mentioned recently. Consider responding if it feels natural. "
        else:
            # Only add frequency guidance when NOT directly engaged
            task += f"{self.talkative_scheduling_prompt_modifier(message_history).strip()} "
        
        task += f"Reply only with `{self.use_turn_token}` to send now, " \
                f"or `{self.pass_turn_token}` to wait."
        
        return turn_task_into_prompt(task, message_history)

    def create_generation_prompt(self, message_history):
        task = "Add a natural message to the chat based on the current conversation. " \
               "You may continue the topic or respond to a question if relevant."
        return turn_task_into_prompt(task, message_history)
