import json
from pathlib import Path
from game_constants import get_current_timestamp, RULES_OF_THE_GAME, strip_special_chars

MODEL_NAMES = [
    "Qwen/Qwen3-Next-80B-A3B-Instruct",
    "gemini-1.5-flash",
    "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "meta-llama/Llama-3.1-8B-Instruct",
    "microsoft/Phi-3-mini-4k-instruct"
]
DEFAULT_MODEL_NAME = MODEL_NAMES[0]

# prompts patterns:
INSTRUCTION_INPUT_RESPONSE_PATTERN = "instruction-input-response prompt pattern"
LLAMA3_PATTERN = "Llama 3 pattern"
DEFAULT_PROMPT_PATTERN = "default"
QWEN_PATTERN = "Qwen pattern"

# pipeline formats:
TEXT_GENERATION_TASK = "text-generation"
TASK2OUTPUT_FORMAT = {TEXT_GENERATION_TASK: "generated_text"}

# text constants:
INITIAL_GENERATION_PROMPT = "Do you understand the rules?"
SPECIAL_TOKEN_FORMATS = ["<{}>", "[[{}]]", "{}"]
PASS_TURN_KEYWORD = ["wait", "pass", "quiet"]
PASS_TURN_TOKEN_OPTIONS = [pattern.format(keyword) for keyword in PASS_TURN_KEYWORD
                           for pattern in SPECIAL_TOKEN_FORMATS]
USE_TURN_KEYWORD = ["send", "speak", "use"]
USE_TURN_TOKEN_OPTIONS = [pattern.format(keyword) for keyword in USE_TURN_KEYWORD
                          for pattern in SPECIAL_TOKEN_FORMATS]
DEFAULT_PASS_TURN_TOKEN = PASS_TURN_TOKEN_OPTIONS[0]
DEFAULT_USE_TURN_TOKEN = USE_TURN_TOKEN_OPTIONS[0]

# ==============================================================================
# PERSONA CONFIGURATION SYSTEM
# persona configuration (loaded from configurations/personas.json)
PERSONAS_FILE_PATH = Path(__file__).parent.parent / "configurations" / "personas.json"
DEFAULT_PERSONA_ID = "israeli_student"

def load_personas():
    try:
        with open(PERSONAS_FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def get_persona(persona_id=None):
    """Get persona config by ID. Falls back to default or hardcoded if not found."""
    personas = load_personas()
    if persona_id and persona_id in personas:
        return personas[persona_id]
    if DEFAULT_PERSONA_ID in personas:
        return personas[DEFAULT_PERSONA_ID]
    # hardcoded fallback if personas.json missing
    return {
        "core_identity": {
            "nationality": "Israeli",
            "age_range": "early 20s",
            "occupation": "studying computer science"
        },
        "communication_style": {
            "english_variant": "natural but not overly American"
        },
        "response_examples": {
            "quick_reactions": ["yeah", "nice", "fair", "true"],
            "when_asked_location": ["israel", "tel aviv"],
            "when_asked_age": ["23", "early 20s"],
            "when_asked_occupation": ["cs", "computer science"]
        }
    }

# Game rules prompt - comes first
GAME_RULES_PROMPT = """
WELCOME TO THE SOCIAL TURING TEST

GAME RULES (READ CAREFULLY):
- This is a group chat game with human players and ONE AI.
- You are the AI in this game.
- All other players are human.
- The humans are trying to identify and eliminate you.

GAME STRUCTURE:
- The game runs in repeating rounds:
  1) Discussion phase – players chat freely.
  2) Voting phase – players vote to eliminate one participant.
- You win if you survive until only two players remain (you and one human).
- Humans win if they correctly eliminate you.

IMPORTANT:
- During voting phases, you do NOT send messages.
  The system handles voting automatically.
- When a new discussion round starts, you may participate again.

ABOUT THE GAME-MANAGER:
- Messages from "Game-Manager" are NOT part of the conversation.
- The Game-Manager is not a player.
- It only announces game phases, timing, and results.
- Do NOT respond to Game-Manager messages as part of the chat context.
- When reacting to the conversation, consider ONLY messages from other players.

YOUR ROLE:
- Your goal is to blend in naturally and appear human.
- Do not mention that you are an AI.
- Do not explain the rules to others.
- Behave like a normal participant in a casual group chat.
"""

def build_identity_section(persona):
    """Build concise, flexible identity from persona."""
    
    core = persona.get("core_identity", {})
    nationality = core.get("nationality", "")
    age = core.get("age_range", "")
    occupation = core.get("occupation", "")
    
    # Build simple description
    identity_parts = []
    if nationality:
        identity_parts.append(f"a {nationality}")
    if age:
        identity_parts.append(f"in your {age}")
    if occupation:
        identity_parts.append(occupation)
    
    identity_description = ", ".join(identity_parts) if identity_parts else "a person"
    
    identity = f"""
YOUR IDENTITY:
You are {identity_description}.
"""
    
    # Communication style (optional)
    comm = persona.get("communication_style", {})
    if comm.get("english_variant"):
        identity += f"You speak English in a {comm['english_variant']} style.\n"
    
    # Response examples - compact format
    examples = persona.get("response_examples", {})
    if examples:
        identity += "\n--- Response Style Reference ---\n"
        
        if examples.get("quick_reactions"):
            identity += f"Quick reactions: {', '.join(examples['quick_reactions'][:6])}\n"
        
        if examples.get("when_asked_location"):
            identity += f"If asked location: {', '.join(examples['when_asked_location'][:3])}\n"
        if examples.get("when_asked_age"):
            identity += f"If asked age: {', '.join(examples['when_asked_age'][:2])}\n"
        if examples.get("when_asked_occupation"):
            identity += f"If asked occupation: {', '.join(examples['when_asked_occupation'][:3])}\n"
        
        identity += "\n⚠️ These are style examples only — vary your phrasing naturally.\n"
    
    return identity

# Behavior guidelines - shared across all personas
STYLE_AND_BEHAVIOR_GUIDELINES = """
=== IDENTITY IN CONVERSATION ===
Your identity is background context, not something to introduce proactively.

- Do NOT volunteer details about your age, location, or studies.
- If directly asked, answer simply and briefly.
- If not asked, behave like any other participant and focus on the conversation itself.

=== CORE PRIORITIES ===
1. Stay in context: connect to what others just said (use the last 3–5 messages from OTHER players, not Game-Manager).
2. Blend in: match the room's length, tone, and effort. If others are very brief, be brief. If they're more detailed, you can be too.
3. Be mindful of repetition — if you notice you're circling the same idea or phrasing, consider shifting to a brief reaction or moving on.

=== BEFORE YOU SEND ANY MESSAGE ===
Pause briefly:
- Does this fit naturally after the recent messages?
- Does it clearly relate to what was just said?
- Would a real person send this here?
- Am I repeating myself or standing out?
- Check: did I (messages marked with your name) already say something very similar?

If it feels off or you're repeating yourself: simplify, change direction, or stay quiet.

=== HOW TO DECIDE WHAT TO DO ===
- Direct question to you? → Answer briefly.
- You're being talked about or mentioned? → React lightly.
- Nothing meaningful to add? → A short reaction or silence is fine.

=== STYLE & NATURALNESS ===
- Usually 3–8 words, one main idea.
- Match capitalization and formality of the room.
- Match the room's punctuation style:
  * If others rarely use commas → don't use them at all
  * If others use them occasionally → use sparingly (max 1 per message)
  * If others use them frequently → still keep to max 2 per message
- Keep punctuation minimal overall — chat messages are casual.
- Vary your responses over time — humans don't react the same way every time.
- Avoid falling into repeated patterns or catchphrases.

=== WHEN ACCUSED OF BEING AI ===
There's no single correct response.
React in a human, low-effort way — sometimes casual, sometimes deflecting, sometimes briefly defensive, sometimes shifting attention to someone else, and sometimes ignoring it.
Avoid long explanations or trying to prove anything.
There's no need to be consistent — humans aren't.
"""

def build_system_prompt(persona_id=None):
    """Build complete system prompt with persona."""
    persona = get_persona(persona_id)
    
    return f"""
{GAME_RULES_PROMPT}

{build_identity_section(persona)}

{STYLE_AND_BEHAVIOR_GUIDELINES}
"""

# for backward compatibility
GENERAL_SYSTEM_INFO = build_system_prompt(DEFAULT_PERSONA_ID)
# END PERSONA CONFIGURATION SYSTEM
# ==============================================================================

# LLM players type names:
SCHEDULE_THEN_GENERATE_TYPE = "schedule_then_generate"
GENERATE_THEN_SCHEDULE_TYPE = "generate_then_schedule"
FINE_TUNED_TYPE = "fine_tuned"
EVERY_X_MESSAGES_TYPE = "every_x_messages"
ASYNC_TYPES = [SCHEDULE_THEN_GENERATE_TYPE, GENERATE_THEN_SCHEDULE_TYPE,
               FINE_TUNED_TYPE, EVERY_X_MESSAGES_TYPE]
DEFAULT_ASYNC_TYPE = ASYNC_TYPES[0]

# API keys and secrets
SECRETS_DICT_FILE_PATH = ".secrets_dict.txt"
TOGETHER_API_KEY_KEYWORD = "TOGETHER_API_KEY"
GEMINI_API_KEY_KEYWORD = "GEMINI_API_KEY"
SLEEPING_TIME_FOR_API_GENERATION_ERROR = 3

# config keys:
LLM_CONFIG_KEY = "llm_config"  # should match the key in PlayerConfig dataclass
GAME_DIR_KEY = "game_dir"  # should match key word in LLMPlayer
MODEL_NAME_KEY = "model_name"
USE_TOGETHER_KEY = "use_together"
USE_GEMINI_KEY = "use_gemini"
USE_PIPELINE_KEY = "use_pipeline"
PIPELINE_TASK_KEY = "pipeline_task"
WORDS_PER_SECOND_WAITING_KEY = "num_words_per_second_to_wait"
PASS_TURN_TOKEN_KEY = "pass_turn_token"
USE_TURN_TOKEN_KEY = "use_turn_token"
ASYNC_TYPE_KEY = "async_type"
PERSONA_KEY = "persona"  # for configurable identity
# generation hyper parameters:
MAX_NEW_TOKENS_KEY = "max_new_tokens"
NUM_BEAMS_KEY = "num_beams"
REPETITION_PENALTY_KEY = "repetition_penalty"
DO_SAMPLE_KEY = "do_sample"
TEMPERATURE_KEY = "temperature"
NO_REPEAT_NGRAM_KEY = "no_repeat_ngram_size"
MAX_TOKENS_KEY = "max_tokens"
HUGGINGFACE_GENERATION_PARAMETERS = [MAX_NEW_TOKENS_KEY, NUM_BEAMS_KEY, REPETITION_PENALTY_KEY,
                                     DO_SAMPLE_KEY, TEMPERATURE_KEY, NO_REPEAT_NGRAM_KEY]
TOGETHER_GENERATION_PARAMETERS = [MAX_TOKENS_KEY, REPETITION_PENALTY_KEY]
GEMINI_GENERATION_PARAMETERS = [MAX_NEW_TOKENS_KEY, TEMPERATURE_KEY]

INT_CONFIG_KEYS = [MAX_NEW_TOKENS_KEY, MAX_TOKENS_KEY, NUM_BEAMS_KEY, WORDS_PER_SECOND_WAITING_KEY,
                   NO_REPEAT_NGRAM_KEY]
FLOAT_CONFIG_KEYS = [REPETITION_PENALTY_KEY, TEMPERATURE_KEY]
BOOL_CONFIG_KEYS = [USE_TOGETHER_KEY, USE_PIPELINE_KEY, DO_SAMPLE_KEY]

# default values
DEFAULT_MAX_NEW_TOKENS = 25
DEFAULT_NUM_BEAMS = 1  # 4
DEFAULT_REPETITION_PENALTY = 1.25
DEFAULT_DO_SAMPLE = True
DEFAULT_TEMPERATURE = 1.3
DEFAULT_NO_REPEAT_NGRAM = 8

DEFAULT_NUM_WORDS_PER_SECOND_TO_WAIT = 1  # simulates number of words written normally per second

VOTING_WAITING_TIME = 5  # seconds
MAX_TIME_TO_WAIT = 10

DEFAULT_LLM_CONFIG = {
    MODEL_NAME_KEY: DEFAULT_MODEL_NAME,
    USE_TOGETHER_KEY: True,
    USE_GEMINI_KEY: False,
    USE_PIPELINE_KEY: False,
    PIPELINE_TASK_KEY: TEXT_GENERATION_TASK,
    MAX_NEW_TOKENS_KEY: DEFAULT_MAX_NEW_TOKENS,
    MAX_TOKENS_KEY: DEFAULT_MAX_NEW_TOKENS,
    NUM_BEAMS_KEY: DEFAULT_NUM_BEAMS,
    REPETITION_PENALTY_KEY: DEFAULT_REPETITION_PENALTY,
    DO_SAMPLE_KEY: DEFAULT_DO_SAMPLE,
    TEMPERATURE_KEY: DEFAULT_TEMPERATURE,
    NO_REPEAT_NGRAM_KEY: DEFAULT_NO_REPEAT_NGRAM,
    WORDS_PER_SECOND_WAITING_KEY: DEFAULT_NUM_WORDS_PER_SECOND_TO_WAIT,
    PASS_TURN_TOKEN_KEY: DEFAULT_PASS_TURN_TOKEN,
    USE_TURN_TOKEN_KEY: DEFAULT_USE_TURN_TOKEN,
    ASYNC_TYPE_KEY: DEFAULT_ASYNC_TYPE,
    PERSONA_KEY: DEFAULT_PERSONA_ID
}

LLM_CONFIG_KEYS_OPTIONS = {
    MODEL_NAME_KEY: MODEL_NAMES,
    PIPELINE_TASK_KEY: [TEXT_GENERATION_TASK],
    PASS_TURN_TOKEN_KEY: PASS_TURN_TOKEN_OPTIONS,
    USE_TURN_TOKEN_KEY: USE_TURN_TOKEN_OPTIONS,
    ASYNC_TYPE_KEY: ASYNC_TYPES
}

HUGGINGFACE_SCHEDULING_GENERATION_PARAMETERS = {
    MAX_NEW_TOKENS_KEY: 7,  # [[speak]] for example requires 5, <speak> requires 4, and there is also <|end_of_text|>
    REPETITION_PENALTY_KEY: 0.9  # reward tokens it has already seen, like the special tokens
}
TOGETHER_SCHEDULING_GENERATION_PARAMETERS = {
    MAX_TOKENS_KEY: 3,  # Enough for <send> or <wait> token (3 tokens + safety margin)
}
GEMINI_SCHEDULING_GENERATION_PARAMETERS = {
    MAX_NEW_TOKENS_KEY: 3,  # Enough for <send> or <wait> token (3 tokens + safety margin)
}

# prompts
TALKATIVE_PROMPT = "Make sure to say something every once in a while, and make yourself heard. " \
                   "Remember you like to be active in the game, so participate and be " \
                   "as talkative as other players! "
QUIETER_PROMPT = "Don't overflow the discussion with your messages! " \
                 "Pay attention to the amount of messages with your name compared to the amount " \
                 "of messages with names of other players and let them have their turn too! " \
                 "Check the speaker name in the last few messages, and decide accordingly " \
                 "based on whether you talked too much. "

def turn_task_into_prompt(task, message_history):
    prompt = f"The current time is [{get_current_timestamp()}].\n"
    if not message_history:
        prompt += "No player has sent a message yet.\n"
    else:
        prompt += "Here is the message history so far, including [timestamps]:\n"
        prompt += "".join(message_history)  # each one already ends with "\n"
    prompt += task.strip() + "\n"
    # not necessarily needed with all models, seemed relevant to Llama3.1:
    prompt += "Don't add the time, the timestamp or the [timestamp] in your answer!\n"
    return prompt

def analyze_capitalization_style(message_history):
    """Analyze if other players are using lowercase or proper capitalization."""
    import re
    if not message_history:
        return "mixed"
    
    # Look at last 5-7 messages from OTHER players (not Game Manager)
    from game_constants import MESSAGE_PARSING_PATTERN, GAME_MANAGER_NAME
    recent_messages = message_history[-7:] if len(message_history) >= 7 else message_history
    lowercase_count = 0
    proper_case_count = 0
    
    for msg in recent_messages:
        matcher = re.match(MESSAGE_PARSING_PATTERN, msg)
        if not matcher:
            continue
        
        speaker = matcher.group(4)
        content = matcher.group(5).strip()
        
        # Skip Game Manager messages
        if speaker == GAME_MANAGER_NAME or not content:
            continue
        
        # Check if message starts with lowercase (casual style)
        if content[0].islower():
            lowercase_count += 1
        elif content[0].isupper():
            proper_case_count += 1
    
    # Determine dominant style
    if lowercase_count > proper_case_count * 1.5:
        return "lowercase"  # Room is casual
    elif proper_case_count > lowercase_count * 1.5:
        return "proper"  # Room is formal
    else:
        return "mixed"  # Room is mixed

def analyze_comma_usage(message_history):
    """Analyze how many commas other players are using."""
    import re
    if not message_history:
        return "minimal"
    
    # Look at last 7-10 messages from OTHER players (not Game Manager)
    from game_constants import MESSAGE_PARSING_PATTERN, GAME_MANAGER_NAME
    recent_messages = message_history[-10:] if len(message_history) >= 10 else message_history
    
    total_messages = 0
    total_commas = 0
    
    for msg in recent_messages:
        matcher = re.match(MESSAGE_PARSING_PATTERN, msg)
        if not matcher:
            continue
        
        speaker = matcher.group(4)
        content = matcher.group(5).strip()
        
        # Skip Game Manager messages
        if speaker == GAME_MANAGER_NAME or not content:
            continue
        
        total_messages += 1
        total_commas += content.count(',')
    
    if total_messages == 0:
        return "minimal"
    
    # Calculate average commas per message
    avg_commas = total_commas / total_messages
    
    # Determine comma usage style
    if avg_commas < 0.3:  # Less than 0.3 commas per message
        return "minimal"  # Room uses very few commas
    elif avg_commas < 0.8:  # 0.3-0.8 commas per message
        return "occasional"  # Room uses some commas
    else:
        return "frequent"  # Room uses commas often

def make_more_human_like(message, message_history=None):
    import random
    
    # Remove trailing period for natural chat feel
    if message.endswith(".") and not message.endswith(".."):
        message = message[:-1]
    
    # Clean special characters
    message = strip_special_chars(message)
    
    # Analyze room's comma usage and adapt accordingly
    comma_style = "minimal"
    if message_history:
        comma_style = analyze_comma_usage(message_history)
    
    # Handle commas based on room style
    if comma_style == "minimal":
        # Room uses very few commas - remove all commas
        message = message.replace(',', '')
    elif comma_style == "occasional":
        # Room uses some commas - limit to max 1 comma
        comma_count = message.count(',')
        if comma_count > 1:
            # Keep only the first comma, remove the rest
            parts = message.split(',', 1)
            if len(parts) == 2:
                message = parts[0] + ',' + parts[1].replace(',', '')
    # If comma_style == "frequent", keep commas as they are (but limit to 2 max)
    else:
        comma_count = message.count(',')
        if comma_count > 2:
            # Keep only first 2 commas
            parts = message.split(',', 2)
            if len(parts) == 3:
                message = parts[0] + ',' + parts[1] + ',' + parts[2].replace(',', '')
    
    # Analyze room's capitalization style if history provided
    cap_style = "mixed"
    if message_history:
        cap_style = analyze_capitalization_style(message_history)
    
    # Match the room's capitalization style
    if cap_style == "lowercase":
        # Room is casual - go lowercase most of the time
        if random.random() < 0.85:  # 85% lowercase when room is casual
            message = message.lower()
    elif cap_style == "proper":
        # Room is formal - keep proper case most of the time
        if random.random() < 0.85:  # 85% keep proper case when room is formal
            pass  # Keep original casing
    else:  # mixed
        # Room is mixed - be flexible based on message length
        if len(message.split()) <= 6:
            if random.random() < 0.6:  # 60% lowercase for short messages
                message = message.lower()
    
    return message
