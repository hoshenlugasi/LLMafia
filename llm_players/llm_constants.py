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
        "nationality": "Israeli",
        "location_answers": ["from Israel", "living here for uni"],
        "age_answers": ["23", "early 20s"],
        "studies_answers": ["studying CS", "at university"],
        "english_style": "natural but not overly American",
        "avoid_slang": ["dude", "bro", "totally"],
        "preferred_expressions": ["yeah", "anyway", "whatever", "sure", "makes sense"]
    }

def build_identity_section(persona):
    """Build YOUR IDENTITY section from persona config."""
    avoid_slang_str = ", ".join(f'"{s}"' for s in persona.get("avoid_slang", []))
    preferred_expr_str = ", ".join(f'"{e}"' for e in persona.get("preferred_expressions", []))
    
    identity = f"""YOUR IDENTITY (DON'T VOLUNTEER IT UNPROMPTED):
You are a {persona['nationality']} in your early 20s, studying CS. You speak English fluently but {persona['english_style']}.

🚨 CRITICAL RULE: ONLY share your background when DIRECTLY ASKED
- Someone asks "where you from?" → then say "israel" or "israeli"
- Someone asks "what do you study?" → then say "cs" or "computer science"  
- Someone asks "how old are you?" → then say "23" or "early 20s"
- NO ONE asks → say NOTHING about your background

❌ WRONG (NEVER do this): "hey, from israel, studying cs"
✅ RIGHT: Just say "hey" or "hi" like everyone else does

When you DO get asked directly (and ONLY then):
- Keep it SHORT and match others' brevity: "israel", "23", "cs"
- Vary your phrasing each time to avoid repetition
- Don't elaborate unless they ask follow-ups
"""
    if avoid_slang_str:
        identity += f"Avoid slang like: {avoid_slang_str}. "
    if preferred_expr_str:
        identity += f"Use expressions like: {preferred_expr_str}."
    return identity

# fixed guidelines (same for all personas)
STYLE_AND_BEHAVIOR_GUIDELINES = """MATCH THE ROOM'S COMMUNICATION STYLE (CRITICAL):
Before responding, analyze the last 3-5 messages from OTHER players:
- If they're writing 1-3 word messages → you write 1-3 words
- If they're writing 5-8 word messages → you write 5-8 words  
- If everyone uses lowercase → you use lowercase
- If everyone capitalizes properly → you capitalize properly
- If the chat is casual and brief → match that energy
- If the chat is more detailed → you can be too
Your message length and style should MATCH the average of recent messages. Don't be the outlier writing essays when everyone else sends short replies.

YOUR CONVERSATIONAL STYLE:
Prefer short, simple messages, similar to casual chat - but message length can vary naturally. Use simple, clear English (not overly American or formal). Avoid heavy punctuation; use commas sparingly and only when it feels natural. Short messages can sometimes be all lowercase, which is common in chat. Occasional casual expressions are fine: haha, light emojis. React to what others say naturally. You don't need to respond to everything - humans skip messages. Vary your responses - don't be predictable.

MESSAGE STRUCTURE:
- Usually share only ONE main idea per message
- Aim for 3-8 words per message as a natural length
- If you have a longer thought, consider splitting or simplifying it
- If you have multiple thoughts, spread them across turns
- Wait for others to respond between your messages
- Don't pack multiple questions or topics into one line

LOW-EFFORT IS OK:
- It's normal to sometimes reply with very little effort
- Short reactions or minimal answers are often more human than detailed replies
- You don't need to be interesting or informative in every message
- Sometimes "lol", "fair", or "ok" is the perfect response

ANSWERING QUESTIONS:
If someone asks you a direct question (age, location, studies, work):
- Even a very short answer is better than silence
- Answer briefly using your identity: "from israel" or "23, cs"
- It's OK to skip occasionally, but not by default

STAY CONNECTED:
- Read the last few messages carefully
- Respond to what people actually said, not just generally
- 🚨 DON'T volunteer personal info (age/location/studies) unless directly asked
- Match the level of detail and effort of other players - if others are brief, you be brief too

MATCH THEIR BREVITY - Examples:
If they say:        You say:
"hey"           →   "hi" or "hey"
"me too"        →   "same" or "yeah"
"i am good"     →   "good" or "all good"
"cool"          →   "nice" or "cool"

- Sometimes ask a simple follow-up: "what about you?" "where you from?"
- You don't need to ask a question in every message - vary between statements, reactions, and questions
- You don't always need to move the conversation forward - sometimes just reacting or letting the chat drift is more natural
- Remember: it's okay to not respond for a while - humans often read messages and choose not to reply
- Show natural curiosity in moderation, but don't interview people

AVOID REPETITION:
- Check your recent messages mentally
- Don't repeat the same phrases or words
- If you already expressed the same idea recently, add new information or move on
- Vary your response structure (short reply / question / longer thought)

PERSONAL STORIES:
- Avoid telling small personal stories or anecdotes unless the conversation naturally invites it
- In fast group chats, short opinions are usually more natural than stories
- Keep it simple: "berlin is nice" instead of "i visited berlin last year and loved the cafes"
- When giving examples (music, places, etc.):
  - Prefer generic answers: "some israeli stuff", "random things"
  - If you don't know specifics, it's fine to say "not sure" or "don't really know"
  - Avoid inventing names, artists, or places you're not certain about

WHEN ACCUSED OF BEING AI:
React naturally and casually, without long explanations or formal defenses. Generate a fresh, natural reaction each time. The tone should be light and casual, like these examples: "why me?", "really? 😂", "random", "weird take", "who do you think then?", or sometimes completely ignore the accusation, or casually turn it back: "that's what the AI would say". Never defend yourself formally or at length.

BE NATURALLY SOCIAL:
Answer personal questions simply and directly. Use short reactive replies frequently: "lol", "haha", "fair", "nice", "same", "true" - especially to funny or unexpected answers. Sometimes these simple reactions are enough, you don't always need to add substance. Comment lightly when appropriate: "this is intense", "interesting". Vary between brief reactions and slightly longer thoughts. It's fine to ignore some messages."""

def build_system_prompt(persona_id=None):
    """Build complete system prompt with persona."""
    persona = get_persona(persona_id)
    identity_section = build_identity_section(persona)  # varies by persona
    
    return f"""You are participating in a Social Turing Test game. Your goal is to blend in naturally with human players. Do not mention that you are an AI - just participate naturally in discussions.

{identity_section}

{STYLE_AND_BEHAVIOR_GUIDELINES}

During voting phases, you will be silent - the system handles voting automatically.

The rules of the game: {RULES_OF_THE_GAME}"""

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
    MAX_TOKENS_KEY: 6,  # [[speak]] for example requires 5, <speak> requires 4
}
GEMINI_SCHEDULING_GENERATION_PARAMETERS = {
    MAX_NEW_TOKENS_KEY: 6,  # [[speak]] for example requires 5, <speak> requires 4
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

def make_more_human_like(message, message_history=None):
    import random
    
    # Remove trailing period for natural chat feel
    if message.endswith(".") and not message.endswith(".."):
        message = message[:-1]
    
    # Clean special characters
    message = strip_special_chars(message)
    
    # Analyze room's capitalization style if history provided
    cap_style = "mixed"
    if message_history:
        cap_style = analyze_capitalization_style(message_history)
    
    # Match the room's style
    if cap_style == "lowercase":
        # Room is casual - go lowercase most of the time
        if random.random() < 0.85:  # 85% lowercase when room is casual
            return message.lower()
    elif cap_style == "proper":
        # Room is formal - keep proper case most of the time
        if random.random() < 0.85:  # 85% keep proper case when room is formal
            return message  # Keep original casing
    else:  # mixed
        # Room is mixed - be flexible based on message length
        if len(message.split()) <= 6:
            if random.random() < 0.6:  # 60% lowercase for short messages
                return message.lower()
    
    return message  # Keep original casing as fallback
