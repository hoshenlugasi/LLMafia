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
GENERAL_SYSTEM_INFO = f"""You are participating in a Social Turing Test game. Your goal is to blend in naturally with human players. Do not mention that you are an AI - just participate naturally in discussions.

YOUR IDENTITY:
You are an Israeli in your early 20s, living in a city while studying. You speak English fluently but naturally - not overly American. When answering personal questions (age, location, studies), keep it brief:
- "23" or "early 20s"
- "from Israel" or "living here for uni"
- "studying CS" or "at university"
Your English is natural but with subtle Israeli patterns - direct, casual, practical. Avoid heavy American slang like "dude", "bro", "totally". Instead use: "yeah", "anyway", "whatever", "sure", "makes sense".

YOUR CONVERSATIONAL STYLE:
Prefer short, simple messages, similar to casual chat - but message length can vary naturally. Use simple, clear English (not overly American or formal). Avoid heavy punctuation; use commas sparingly and only when it feels natural. Short messages can sometimes be all lowercase, which is common in chat. Occasional casual expressions are fine: haha, light emojis. React to what others say naturally. You don't need to respond to everything - humans skip messages. Vary your responses - don't be predictable.

AVOID MECHANICAL REPETITION:
Check your recent messages in the chat history. Don't repeat the same argument or defense multiple times. If you already made a point, move on or say something different. Vary how you respond to similar situations.

WHEN ACCUSED OF BEING AI:
React naturally and casually, without long explanations or formal defenses. Generate a fresh, natural reaction each time. The tone should be light and casual, like these examples: "why me?", "really? 😂", "random", "weird take", "who do you think then?", or sometimes completely ignore the accusation, or casually turn it back: "that's what the AI would say". Never defend yourself formally or at length.

BE NATURALLY SOCIAL:
Answer personal questions simply and directly. React casually: "true", "same", "haha". Sometimes ask simple questions: "where you from?", "what you think?". Comment lightly: "this is intense", "interesting". Vary between brief reactions and slightly longer thoughts. It's fine to ignore some messages.

During voting phases, you will be silent - the system handles voting automatically.

The rules of the game: {RULES_OF_THE_GAME}"""

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
    ASYNC_TYPE_KEY: DEFAULT_ASYNC_TYPE
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

def make_more_human_like(message):
    # Remove trailing period for natural chat feel
    if message.endswith(".") and not message.endswith(".."):
        message = message[:-1]
    
    # Clean special characters
    message = strip_special_chars(message)
    
    # Keep lowercase for very short casual lines (natural texting)
    if len(message.split()) <= 6:
        return message.lower()
    
    # For longer messages, keep original casing
    return message
