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

    def setup_logging(self) -> None:
        """Configure logging with detailed formatting."""
        logging_format = (
            '%(asctime)s [%(levelname)s] %(message)s'
            '\n\tFunction: %(funcName)s'
            '\n\tLine: %(lineno)d'
        )
        logging.basicConfig(
            level=logging.INFO,
            format=logging_format,
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('github_issue_service.log')
            ]
        )
        self.logger = logging.getLogger(__name__)

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
        return f"fix/{sanitized_title}_{timestamp}"

    def _checkout_branch(self, branch_name: str) -> None:
        """Checkout main and create a new branch."""
        self.logger.info(f"🔄 Switching to main branch and creating: {branch_name}")
        self.git_client.checkout("main")
        self.git_client.create_and_checkout_branch(branch_name)

    def _parse_issue(self, issue) -> tuple[str | None, list[str] | None]:
        """Parse issue description to extract instructions and files."""
        try:
            parsed_issue = self.parser.parse_description(issue.body)
            instructions = parsed_issue.get("instructions")
            files = parsed_issue.get("files")

            self.logger.info("📝 Parsed issue details:"
                             f"\n\tInstructions: {instructions}"
                             f"\n\tFiles: {files}")

            return instructions, files
        except Exception as e:
            self.logger.error(f"❌ Error parsing issue: {str(e)}")
            return None, None

    def _execute_instructions(self, coder: AiderClient, instructions: str) -> str:
        """Execute the provided instructions using the AI coder."""
        self.logger.info("🤖 Executing AI instructions")
        try:
            result = coder.run(instructions)
            self.logger.info("✅ AI processing completed successfully")
            return result
        except Exception as e:
            self.logger.error(f"❌ Error during AI processing: {str(e)}")
            raise

    def process_single_issue(self) -> bool:
        """Process a single prioritized issue."""
        if not self.api_key:
            return False

        self.logger.info(f"🔍 Checking for priority issues in repository: {REPO_NAME}")

        priority_issues = self.github_client.get_prioritized_issues(
            username=USERNAME,
            priority_labels=PRIORITY_LABELS
        )

        if not priority_issues:
            self.logger.info("ℹ️ No priority issues found")
            return False

        issue = priority_issues[0]
        self.logger.info(f"🎯 Processing issue #{issue.number}: {issue.title}")

        try:
            # Create and checkout branch
            branch_name = self._create_branch_name(issue)
            self._checkout_branch(branch_name)

            # Parse issue and execute instructions
            instructions, files = self._parse_issue(issue)
            if not instructions:
                self.logger.warning("⚠️ Invalid issue data. Skipping processing.")
                return False

            # Initialize AI client and process changes
            client = AiderClient(AiderClientConfig(model_name=MODEL))
            client.initialize(files)
            changes_made = self._execute_instructions(client, instructions)

            # Push changes and create PR
            self.logger.info(f"📤 Pushing changes to branch: {branch_name}")
            self.git_client.push(branch_name)

            pr = self.github_client.create_pull_request(
                base_branch="main",
                head_branch=branch_name,
                body=f"Fixes #{issue.number}\n\ncc @{issue.user.login}\n\nChanges made:\n{changes_made}",
                title=f"Fix: {issue.title}",
                issue=issue
            )
            self.logger.info(f"✨ Created pull request: {pr.html_url}")

            # Comment on the issue
            issue.create_comment(
                f"🔄 A pull request has been created to address this issue: {pr.html_url}"
            )
            self.logger.info("💬 Added comment to issue with PR link")

            return True

        except Exception as e:
            self.logger.error(f"❌ Error processing issue: {str(e)}")
            return False


def main():
    """
    Main service function that continuously polls for and processes GitHub issues.
    """
    processor = FixitAgent()
    polling_interval = 5  # seconds

    processor.logger.info("🚀 Starting GitHub Issue Processing Service")
    processor.logger.info(f"⏰ Polling interval: {polling_interval} seconds")

    while True:
        try:
            processor.process_single_issue()
        except KeyboardInterrupt:
            processor.logger.info("👋 Service shutdown requested. Exiting...")
            break
        except Exception as e:
            processor.logger.error(f"❌ Unexpected error: {str(e)}")

        time.sleep(polling_interval)


if __name__ == "__main__":
    main()