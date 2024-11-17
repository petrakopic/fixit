import os
from datetime import datetime
import logging
import re
import sys
import time

import click

from ai_agent import AiderClient, AiderClientConfig, AiderException
from services.git import GitManager, GitException
from services.github_client import GithubClient, GithubException
from services.parser import IssueDescriptionParser, ParserException
from config import (
    MODEL,
    POLLING_INTERVAL,
    PRIORITY_LABELS,
)


class FixitAgent:
    def __init__(self, repo_name: str, username: str):
        self.repo_name = repo_name
        self.username = username
        self.setup_logging()
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.github_client = GithubClient(repo_name=repo_name)
        self.git_client = GitManager()
        self.parser = IssueDescriptionParser(self.api_key)
        # Track processed issue numbers, so we don't process the same issue twice
        self.processed_issues = set()

    def setup_logging(self) -> None:
        logging_format = '%(asctime)s [%(levelname)s] Fixit Agent: %(message)s'
        date_format = '%H:%M:%S'

        logging.basicConfig(
            level=logging.INFO,
            format=logging_format,
            datefmt=date_format,
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('fixit_agent.log')
            ]
        )
        self.logger = logging.getLogger('FixitAgent')

    def _create_branch_name(self, issue) -> str:
        """Generate a sanitized branch name from issue title."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sanitized_title = re.sub(r'[^a-zA-Z0-9]', '_', issue.title.lower())
        return f"{sanitized_title}_{timestamp}"

    def _checkout_branch(self, branch_name: str) -> None:
        """Checkout main and create a new branch."""
        self.logger.info(f"🔄 Switching to main branch and creating: {branch_name}")
        try:
            self.git_client.checkout("main")
            self.git_client.create_and_checkout_branch(branch_name)
        except GitException as e:
            self.logger.error(f"❌ Error checking out branch: {str(e)}")
            raise

    def _parse_issue(self, issue) -> tuple[str|None, list[str]|None]:
        """Parse issue description to extract instructions and files."""
        try:
            parsed_issue = self.parser.parse_description(issue_description=issue.body)
            instructions = parsed_issue.get("instructions")
            files = parsed_issue.get("files")

            self.logger.info("📝 Parsed Fixit task:"
                             f"\n\tInstructions: {instructions}"
                             f"\n\tFiles: {files}")

            return instructions, files
        except ParserException as e:
            self.logger.error(f"❌ Error parsing Fixit task: {str(e)}")
            return None, None

    def _execute_instructions(self, coder: AiderClient, instructions: str) -> str:
        """Execute the provided instructions using the AI coder."""
        self.logger.info("🤖 Fixit Agent processing task")
        try:
            result = coder.run(instructions)
            self.logger.info("✅ Fixit Agent completed task successfully")
            return result
        except AiderException as e:
            self.logger.error(f"❌ Fixit Agent encountered an error: {str(e)}")
            raise

    def _should_process_issue(self, issue) -> bool:
        """Determine if an issue should be processed."""
        # Skip if we've already processed this issue
        if issue.number in self.processed_issues:
            self.logger.info(f"Skipping issue #{issue.number}: Already processed in this session")
            return False
        return True

    def process_single_issue(self) -> bool:
        """Process a single prioritized issue."""
        if not self.api_key:
            return False

        self.logger.info(f"🔍 Fixit Agent scanning for tasks in: {self.repo_name}")

        try:
            priority_issues = self.github_client.get_prioritized_issues(
                username=self.username,
                priority_labels=PRIORITY_LABELS
            )
        except GithubException as e:
            self.logger.error(f"❌ Error fetching prioritized issues: {str(e)}")
            return False

        if not priority_issues:
            self.logger.info("ℹ️ No Fixit tasks found")
            return False

        # Find the first unprocessed issue
        issue_to_process = None
        for issue in priority_issues:
            if self._should_process_issue(issue):
                issue_to_process = issue
                break

        if not issue_to_process:
            self.logger.info("ℹ️ No new tasks to process")
            return False

        self.logger.info(
            f"🎯 Fixit Agent processing task #{issue_to_process.number}: {issue_to_process.title}")

        try:
            # Create and checkout branch
            branch_name = self._create_branch_name(issue_to_process)
            self._checkout_branch(branch_name)

            # Parse issue and execute instructions
            instructions, files = self._parse_issue(issue_to_process)
            if not instructions:
                self.logger.warning("⚠️ Invalid Fixit task data. Skipping processing.")
                return False

            # Initialize AI client and process changes
            client = AiderClient(AiderClientConfig(model_name=MODEL))
            client.initialize(files)
            changes_made = self._execute_instructions(client, instructions)

            # Push changes and create PR
            self.logger.info(f"📤 Pushing Fixit changes to branch: {branch_name}")
            self.git_client.push(branch_name)

            pr = self.github_client.create_pull_request(
                base_branch="main",
                head_branch=branch_name,
                body=f"🤖 Fixit Agent Solution for #{issue_to_process.number}\n\n"
                     f"cc @{issue_to_process.user.login}\n\n",
                title=f"Fixit: {issue_to_process.title}",
                issue=issue_to_process
            )
            self.logger.info(f"✨ Fixit Agent created pull request: {pr.html_url}")

            # Comment on the issue
            issue_to_process.create_comment(
                f"🤖 Fixit Agent has created a solution!\n"
                f"Review the changes here: {pr.html_url}"
            )
            self.logger.info("💬 Added Fixit completion comment to issue")
            self.processed_issues.add(issue_to_process.number)
            return True

        except (AiderException, GitException, GithubException) as e:
            self.logger.error(f"❌ Fixit Agent error: {str(e)}")
            return False


def run_fixit_agent_service(repo_name: str, username: str) -> None:
    """
    Main service function that continuously runs the Fixit Agent.

    This function sets up the FixitAgent instance, configures logging,
    and then enters a loop where it continuously processes prioritized
    issues from the GitHub repository.

    If any errors occur during the processing of an issue, the error
    is logged, and the loop continues to the next iteration.

    The function also includes a configurable polling interval, which
    determines how often the Fixit Agent checks for new issues to
    process.
    """
    agent = FixitAgent(repo_name=repo_name, username=username)
    agent.logger.info("🚀 Starting Fixit Agent Service")

    while True:
        try:
            agent.process_single_issue()
        except KeyboardInterrupt:
            agent.logger.info("👋 Fixit Agent shutdown requested. Exiting...")
            break
        except Exception as e:
            agent.logger.error(f"❌ Fixit Agent encountered an error: {str(e)}")

        time.sleep(POLLING_INTERVAL)


@click.command()
@click.option('--repo_name', default = "petrakopic/fixit", help='GitHub repository name in the format "username/repo"')
@click.option('--username', default = "fixit-bot", help='GitHub username to be tagged on issues')
def main(repo_name: str, username:str):
    run_fixit_agent_service(repo_name=repo_name, username=username)


if __name__ == '__main__':
    main()
