import os
import time
from functools import cache
from pathlib import Path
from google import genai

from game_constants import get_current_timestamp
from llm_players.llm_constants import (TASK2OUTPUT_FORMAT, INITIAL_GENERATION_PROMPT, \
                                       INSTRUCTION_INPUT_RESPONSE_PATTERN, LLAMA3_PATTERN, DEFAULT_PROMPT_PATTERN,
                                       NUM_BEAMS_KEY, \
                                       MODEL_NAME_KEY, USE_PIPELINE_KEY, PIPELINE_TASK_KEY, MAX_NEW_TOKENS_KEY,
                                       GENERAL_SYSTEM_INFO, \
                                       REPETITION_PENALTY_KEY, USE_TOGETHER_KEY, TOGETHER_API_KEY_KEYWORD, \
                                       SECRETS_DICT_FILE_PATH, SLEEPING_TIME_FOR_API_GENERATION_ERROR, USE_GEMINI_KEY,
                                       GEMINI_API_KEY_KEYWORD, GEMINI_GENERATION_PARAMETERS,
                                       TOGETHER_GENERATION_PARAMETERS, HUGGINGFACE_GENERATION_PARAMETERS,
                                       TOGETHER_SCHEDULING_GENERATION_PARAMETERS,
                                       HUGGINGFACE_SCHEDULING_GENERATION_PARAMETERS,
                                       GEMINI_SCHEDULING_GENERATION_PARAMETERS, QWEN_PATTERN)

print("Trying to import torch...", get_current_timestamp())
import torch
print("Finished importing torch!", get_current_timestamp())
print("Trying to import from transformers...", get_current_timestamp())
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoModelForSeq2SeqLM, AutoConfig, \
    pipeline
print("Finished importing from transformers!", get_current_timestamp())

from together import Together
from together.error import TogetherException

CACHE_DIR = os.path.expanduser("~/.cache/huggingface/hub")


def is_local_path(model_name):
    return os.path.isdir(model_name)  # maybe should come up with better mechanism


@cache
def cached_model(model_name):
    if is_local_path(model_name):
        config = AutoConfig.from_pretrained(model_name)
        return AutoModelForSeq2SeqLM.from_pretrained(model_name, config=config)
    return AutoModelForCausalLM.from_pretrained(model_name, cache_dir=CACHE_DIR)


@cache
def cached_tokenizer(model_name):
    return AutoTokenizer.from_pretrained(model_name, cache_dir=CACHE_DIR)


@cache
def cached_pipeline(model_name, task):
    return pipeline(task, model_name, device_map="auto")


def get_api_key(key_type):
    key = os.environ.get(key_type)
    if key:
        return key
    secrets_file = Path(SECRETS_DICT_FILE_PATH)
    if secrets_file.exists():
        try:
            secrets = eval(secrets_file.read_text())
        except (ValueError, NameError):
            return None
        return secrets.get(key_type)
    else:
        print("\n\n\nMISSING SECRETS DICT FILE!!!!!\n\n\n")
    return None

class LLMWrapper:

    def __init__(self, logger, **llm_config):
        self.logger = logger
        self.model_name = llm_config[MODEL_NAME_KEY]
        self.use_together = llm_config.get(USE_TOGETHER_KEY)
        self.use_pipeline = llm_config[USE_PIPELINE_KEY]
        self.use_gemini = llm_config.get(USE_GEMINI_KEY)
        self.pipeline_task = llm_config[PIPELINE_TASK_KEY]
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.prompt_template = self._get_prompt_template()

        if self.use_gemini:
            self.client = genai.Client(api_key=get_api_key(GEMINI_API_KEY_KEYWORD))
            self.pipeline = self.tokenizer = self.model = None
            generation_params = GEMINI_GENERATION_PARAMETERS
            scheduling_generation_params = GEMINI_SCHEDULING_GENERATION_PARAMETERS
        elif self.use_together:
            self.client = Together(api_key=get_api_key(TOGETHER_API_KEY_KEYWORD))
            self.pipeline = self.tokenizer = self.model = None
            generation_params = TOGETHER_GENERATION_PARAMETERS
            scheduling_generation_params = TOGETHER_SCHEDULING_GENERATION_PARAMETERS
        elif self.use_pipeline:
            self.pipeline = cached_pipeline(self.model_name, self.pipeline_task)
            self.client = self.tokenizer = self.model = None
            generation_params = HUGGINGFACE_GENERATION_PARAMETERS
            scheduling_generation_params = HUGGINGFACE_SCHEDULING_GENERATION_PARAMETERS
        else:
            self.pipeline = self.client = None
            self.tokenizer = cached_tokenizer(self.model_name)
            self.model = cached_model(self.model_name)
            self.model.to(self.device)
            self.model.eval()
            generation_params = HUGGINGFACE_GENERATION_PARAMETERS
            scheduling_generation_params = HUGGINGFACE_SCHEDULING_GENERATION_PARAMETERS

        self.generation_parameters = {key: value for key, value in llm_config.items()
                                      if key in generation_params}
        
        # For scheduling, use hardcoded defaults - don't let config override
        # This ensures scheduling always uses minimal tokens (just for <send>/<wait>)
        if self.use_gemini:
            self.scheduling_generation_parameters = GEMINI_SCHEDULING_GENERATION_PARAMETERS.copy()
        elif self.use_together:
            self.scheduling_generation_parameters = TOGETHER_SCHEDULING_GENERATION_PARAMETERS.copy()
        else:
            self.scheduling_generation_parameters = HUGGINGFACE_SCHEDULING_GENERATION_PARAMETERS.copy()

        if (NUM_BEAMS_KEY in self.generation_parameters
            and self.generation_parameters[NUM_BEAMS_KEY] < 2):
            del self.generation_parameters[NUM_BEAMS_KEY]

        # initial generation just to save time of first generation in real time
        self.generate(INITIAL_GENERATION_PROMPT, False, system_info=GENERAL_SYSTEM_INFO)

    def _get_prompt_template(self):
        model_name = self.model_name.lower()
        if "phi-3" in model_name:
            return INSTRUCTION_INPUT_RESPONSE_PATTERN
        elif "llama-3" in model_name:
            return LLAMA3_PATTERN
        # elif "____" in model_name: return "____"
        elif "qwen" in model_name:
            return QWEN_PATTERN
        else:
            return DEFAULT_PROMPT_PATTERN

    def pipeline_preprocessing(self, input_text, system_info):
        if self.prompt_template in (INSTRUCTION_INPUT_RESPONSE_PATTERN, LLAMA3_PATTERN, QWEN_PATTERN):
            system_message = [{"role": "system", "content": system_info}] if system_info else []
            return system_message + [{"role": "user", "content": input_text}]
        else:
            raise NotImplementedError("Used model doesn't support pipeline, "
                                      "try `use_pipeline=False` in config")

    def direct_preprocessing(self, input_text, system_info) -> str:
        if self.prompt_template == INSTRUCTION_INPUT_RESPONSE_PATTERN:
            instruction = system_info.strip() + " " + input_text if system_info else input_text
            return f"### Instruction:\n{instruction}\n### Response: "
        # elif self.prompt_template is of Phi-3 style:
            # return f"<|user|>{input_text}<|end|>\n<|assistant|>"
        elif self.prompt_template == LLAMA3_PATTERN:
            if system_info:
                system_prompt = f"<|start_header_id|>system<|end_header_id|>{system_info}<|eot_id|>"
            else:
                system_prompt = ""
            return f"<|begin_of_text|>{system_prompt}" \
                   f"<|start_header_id|>user<|end_header_id|>{input_text}<|eot_id|>" \
                   f"<|start_header_id|>assistant<|end_header_id|>"
        else:
            raise NotImplementedError("Missing prompt template for used model")

    def direct_postprocessing(self, decoded_output):
        if self.prompt_template == INSTRUCTION_INPUT_RESPONSE_PATTERN:
            output = decoded_output.split("### Response:")[1].strip().split("</s>")[0]

            return output.strip()
        elif self.prompt_template == LLAMA3_PATTERN:
            assistant_prefix = "<|start_header_id|>assistant<|end_header_id|>"
            if assistant_prefix in decoded_output:
                decoded_output = decoded_output.split(assistant_prefix)[1].strip()
            decoded_output = decoded_output.split("<|eot_id|>")[0].split("<|end_of_text|>")[0].strip()
            if decoded_output and decoded_output[0] == ":":
                decoded_output = decoded_output[1:]
            if "<|eom_id|>" in decoded_output:
                decoded_output = decoded_output.split("<|eom_id|>")[0].strip()
            return decoded_output
        else:
            raise NotImplementedError("Missing output template for used model")

    def generate(self, input_text, is_scheduler=False, system_info=""):
        if is_scheduler:
            generation_parameters = self.scheduling_generation_parameters
        else:
            generation_parameters = self.generation_parameters
        with torch.inference_mode():
            if self.use_gemini:
                self.logger.log("messages in generate with self.use_gemini", system_info + "\n\n" + input_text)
                final_output = self.generate_with_gemini(input_text, system_info, generation_parameters)
                self.logger.log("final_output in generate with self.use_gemini", final_output)
            elif self.use_together:
                messages = self.pipeline_preprocessing(input_text, system_info)
                self.logger.log("messages in generate with self.use_together", messages)
                final_output = self.generate_with_together_safely(messages, generation_parameters)  # max_new_tokens -> max_tokens
                self.logger.log("final_output in generate with self.use_together", final_output)
            elif self.use_pipeline:
                messages = self.pipeline_preprocessing(input_text, system_info)
                self.logger.log("messages in generate with self.use_pipeline", messages)
                outputs = self.pipeline(messages, **generation_parameters)
                self.logger.log("outputs in generate with self.use_pipeline", outputs)
                final_output = outputs[0][TASK2OUTPUT_FORMAT[self.pipeline_task]][-1]
            else:
                prompt = self.direct_preprocessing(input_text, system_info)
                self.logger.log("prompt in generate directly", prompt)
                inputs = self.tokenizer(prompt, return_tensors="pt")
                inputs = {key: value.to(self.device) for key, value in inputs.items()}
                outputs = self.model.generate(**inputs, **generation_parameters)
                decoded_output = self.tokenizer.decode(outputs[0])
                self.logger.log("decoded_output in generate directly", decoded_output)
                final_output = self.direct_postprocessing(decoded_output)
        return final_output.replace("\n", "   ").strip()

    def generate_with_together_safely(self, messages, generation_parameters):
        output = None
        while not output:
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    **generation_parameters
                )
                output = response.choices[0].message.content
            except TogetherException as e:
                print(f"TogetherException\n{e}")
                self.logger.log("error generating with TogetherAI", str(e))
                time.sleep(SLEEPING_TIME_FOR_API_GENERATION_ERROR)
        return output

    def generate_with_gemini(self, input_text, system_info, generation_parameters):
        if system_info:
            full_prompt = system_info + "\n\n" + input_text
        else:
            full_prompt = input_text

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=full_prompt,
        )

        return response.text if hasattr(response, "text") else str(response)
