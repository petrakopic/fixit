from pathlib import Path
from typing import List, Optional, Union
import logging

from aider.coders import Coder
from aider.io import InputOutput
from aider.models import Model

from config import MODEL


class AiderClientConfig:
    """Configuration class for Aider client"""

    def __init__(
          self,
          model_name: str = MODEL,
          conventions_path: Optional[str] = None,
          show_diffs: bool = True,
          auto_commits: bool = True,
    ):
        self.model_name = model_name
        self.conventions_path = conventions_path or self._find_conventions()
        self.show_diffs = show_diffs
        self.auto_commits = auto_commits

    @staticmethod
    def _find_conventions() -> Optional[str]:
        """Look for conventions.md in current directory"""
        default_path = Path.cwd() / "conventions.md"
        return str(default_path) if default_path.exists() else None

    def read_conventions(self) -> str:
        if not self.conventions_path:
            return ""
        try:
            with open(self.conventions_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            logging.warning(f"Conventions file not found: {self.conventions_path}")
            return ""
        except Exception as e:
            logging.error(f"Error reading conventions file: {str(e)}")
            return ""


class AiderClient:
    """Client for interacting with Aider"""

    def __init__(self, config: Optional[AiderClientConfig] = None):
        self.config = config or AiderClientConfig()
        self.model = Model(self.config.model_name)
        self.coder = None
        self.logger = logging.getLogger(__name__)

    def initialize(self, files: List[str]) -> None:
        """Initialize the Aider coder with files and configurations"""
        try:
            io = InputOutput(yes=True)
            conventions = self.config.read_conventions()

            if conventions:
                read_only_files = [self.config.conventions_path]
            else:
                read_only_files = None

            # Create coder instance with conventions as read-only file
            self.coder = Coder.create(
                main_model=self.model,
                fnames=files,
                read_only_fnames=read_only_files,
                show_diffs=self.config.show_diffs,
                auto_commits=self.config.auto_commits,
                io=io
            )

            # Add conventions if they exist
            if conventions:
                self.logger.info("Adding code conventions to chat context")
                # Add an explicit instruction to follow conventions
                self.coder.cur_messages.extend([
                    {
                        "role": "user",
                        "content": "Please review the conventions in .conventions.md and ensure all"
                                   " changes follow these guidelines."
                    },
                    {
                        "role": "assistant",
                        "content": "I've reviewed the conventions and will ensure all changes"
                                   " follow these guidelines."
                    }
                ])

        except Exception as e:
            self.logger.error(f"Failed to initialize Aider: {str(e)}")
            raise

    def run(self, instructions: Union[str, List[str]]) -> str:
        """Run one or more instructions through Aider"""
        if not self.coder:
            raise ValueError("Aider not initialized. Call initialize first.")

        if isinstance(instructions, list):
            instructions = ".".join(instructions)

        try:
            result = self.coder.run(instructions)
            return result or "Commands executed successfully"
        except Exception as e:
            self.logger.error(f"Failed to execute instructions: {str(e)}")
            raise

    def add_files(self, files: List[str]) -> None:
        """Add additional files to the chat context"""
        if not self.coder:
            raise ValueError("Aider not initialized. Call initialize first.")

        for file in files:
            try:
                self.coder.add_rel_fname(file)
                self.logger.info(f"Added file to context: {file}")
            except Exception as e:
                self.logger.error(f"Failed to add file {file}: {str(e)}")
                raise