import logging
import re
import time
import sys
from datetime import datetime
import git_api
from aider_client import AiderClient, AiderClientConfig
from github_api import GithubClient
from issue_parser import IssueDescriptionParser
from config import REPO_NAME, USERNAME, MODEL, ANTHROPIC_API_KEY, PRIORITY_LABELS


class FixitAgent:
    def __init__(self):
        self.setup_logging()
        self.api_key = self._get_anthropic_api_key()
        self.github_client = GithubClient(REPO_NAME)
        self.git_client = git_api.GitManager(REPO_NAME)
        self.parser = IssueDescriptionParser(self.api_key)
        self.processed_issues = set()  # Track processed issue numbers


    def setup_logging(self) -> None:
        """Configure logging with simplified time format."""
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

    def _get_anthropic_api_key(self) -> str | None:
        """Retrieve and validate the Anthropic API key."""
        if not ANTHROPIC_API_KEY:
            self.logger.error("❌ ANTHROPIC_API_KEY environment variable is not set")
            return None
        return ANTHROPIC_API_KEY

    def _create_branch_name(self, issue) -> str:
        """Generate a sanitized branch name from issue title."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sanitized_title = re.sub(r'[^a-zA-Z0-9]', '_', issue.title.lower())
        return f"fixit/{sanitized_title}_{timestamp}"

    def _checkout_branch(self, branch_name: str) -> None:
        """Checkout main and create a new branch."""
        self.logger.info(f"🔄 Switching to main branch and creating: {branch_name}")
        self.git_client.checkout("main")
        self.git_client.create_and_checkout_branch(branch_name)

    def _parse_issue(self, issue) -> tuple[str|None, list[str]|None]:
        """Parse issue description to extract instructions and files."""
        try:
            parsed_issue = self.parser.parse_description(issue.body)
            instructions = parsed_issue.get("instructions")
            files = parsed_issue.get("files")

            self.logger.info("📝 Parsed Fixit task:"
                             f"\n\tInstructions: {instructions}"
                             f"\n\tFiles: {files}")

            return instructions, files
        except Exception as e:
            self.logger.error(f"❌ Error parsing Fixit task: {str(e)}")
            return None, None

    def _execute_instructions(self, coder: AiderClient, instructions: str) -> str:
        """Execute the provided instructions using the AI coder."""
        self.logger.info("🤖 Fixit Agent processing task")
        try:
            result = coder.run(instructions)
            self.logger.info("✅ Fixit Agent completed task successfully")
            return result
        except Exception as e:
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

        self.logger.info(f"🔍 Fixit Agent scanning for tasks in: {REPO_NAME}")

        priority_issues = self.github_client.get_prioritized_issues(
            username=USERNAME,
            priority_labels=PRIORITY_LABELS
        )

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
            branch_name = self._create_branch_name(issue)
            self._checkout_branch(branch_name)

            # Parse issue and execute instructions
            instructions, files = self._parse_issue(issue)
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
                body=f"🤖 Fixit Agent Solution for #{issue.number}\n\n"
                     f"cc @{issue.user.login}\n\n"
                     f"Changes made by Fixit:\n```\n{changes_made}\n```",
                title=f"Fixit: {issue.title}",
                issue=issue
            )
            self.logger.info(f"✨ Fixit Agent created pull request: {pr.html_url}")

            # Comment on the issue
            issue.create_comment(
                f"🤖 Fixit Agent has created a solution!\n"
                f"Review the changes here: {pr.html_url}"
            )
            self.logger.info("💬 Added Fixit completion comment to issue")
            self.processed_issues.add(issue_to_process.number)
            return True

        except Exception as e:
            self.logger.error(f"❌ Fixit Agent error: {str(e)}")
            return False


def main():
    """
    Main service function that continuously runs the Fixit Agent.

    This function sets up the FixitAgent instance, configures logging,
    and then enters a loop where it continuously processes prioritized
    issues from the GitHub repository. The loop can be interrupted
    using a keyboard interrupt (Ctrl+C).

    If any errors occur during the processing of an issue, the error
    is logged, and the loop continues to the next iteration.

    The function also includes a configurable polling interval, which
    determines how often the Fixit Agent checks for new issues to
    process.
    """
    agent = FixitAgent()
    polling_interval = 5  # seconds

    agent.logger.info("🚀 Starting Fixit Agent Service")
    agent.logger.info(f"⏰ Task scanning interval: {polling_interval} seconds")

    while True:
        try:
            agent.process_single_issue()
        except KeyboardInterrupt:
            agent.logger.info("👋 Fixit Agent shutdown requested. Exiting...")
            break
        except Exception as e:
            agent.logger.error(f"❌ Fixit Agent encountered an error: {str(e)}")

        time.sleep(polling_interval)


if __name__ == "__main__":
    main()
