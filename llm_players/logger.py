from pathlib import Path
from game_constants import LLM_LOG_FILE_FORMAT, get_current_timestamp

NEW_LOG_FORMAT = "# NEW LOG\n## TIME: {time}\n## OPERATION: {operation}\n## CONTENT: {content}\n\n"


class Logger:

    def __init__(self, name: str, game_dir: Path):
        self.log_file = game_dir / LLM_LOG_FILE_FORMAT.format(name)

    def log(self, operation, content):
        with open(self.log_file, "a", encoding='utf-8') as f:
            f.write(NEW_LOG_FORMAT.format(time=get_current_timestamp(),
                                          operation=operation, content=content))
