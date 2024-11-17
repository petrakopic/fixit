import logging
import os
import subprocess

class GitException(Exception):
    pass

class GitManager:
    def __init__(self):
        """
        Initialize the GitManager with an optional repository path.
        Defaults to the current working directory if not provided.
        """
        self.repo_path = os.getcwd()
        self.logger = logging.getLogger(__name__)
        # Position to the main branch every time the GitManager is initialized.
        self.checkout("main")

    def _run(self, command):
        """
        Run a Git command.

        Args:
            command (list): Git command and arguments (e.g., ["git", "status"]).

        Returns:
            str: Output of the command.

        Raises:
            subprocess.CalledProcessError: If the command fails.
        """
        try:
            self.logger.info(f"Executing: {' '.join(command)} in {self.repo_path}")
            result = subprocess.run(
                command, cwd=self.repo_path, check=True, text=True, capture_output=True
            )
            self.logger.info(result.stdout)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Git command failed: {e.stderr}")
            raise GitException(f"Git command failed: {e.stderr}")

    def checkout(self, branch_name):
        return self._run(["git", "checkout", branch_name])

    def create_and_checkout_branch(self, branch_name):
        return self._run(["git", "checkout", "-b", branch_name])

    def push(self, branch_name=None):
        command = ["git", "push"]
        if branch_name:
            command += ["--set-upstream", "origin", branch_name]
        return self._run(command)

    def pull(self):
        return self._run(["git", "pull"])
