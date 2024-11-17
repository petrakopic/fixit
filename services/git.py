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
            GitException: If the command fails.
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
        try:
            return self._run(["git", "checkout", branch_name])
        except GitException as e:
            raise GitException(f"Failed to checkout branch: {branch_name}") from e

    def create_and_checkout_branch(self, branch_name):
        try:
            return self._run(["git", "checkout", "-b", branch_name])
        except GitException as e:
            raise GitException(f"Failed to create and checkout branch: {branch_name}") from e

    def push(self, branch_name=None):
        command = ["git", "push"]
        if branch_name:
            command += ["--set-upstream", "origin", branch_name]
        try:
            return self._run(command)
        except GitException as e:
            raise GitException(f"Failed to push changes to branch: {branch_name}") from e

    def pull(self):
        try:
            return self._run(["git", "pull"])
        except GitException as e:
            raise GitException("Failed to pull changes from remote repository") from e
