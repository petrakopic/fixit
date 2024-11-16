import os
from github import Github
import logging


class GithubClient:
    def __init__(self, repo_name: str):
        self._github = Github(self._get_github_token())
        self.repo_name = repo_name
        self.logger = logging.getLogger(__name__)
        self._repo = None

    @staticmethod
    def _get_github_token() -> str:
        """Retrieve GitHub token from environment variables."""
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise ValueError("GITHUB_TOKEN environment variable not set.")
        return token

    @property
    def repo(self):
        """Lazily initialize and return the repository object."""
        if self._repo is None:
            try:
                self._repo = self._github.get_repo(self.repo_name)
                self.logger.info(f"Successfully fetched repository: {self.repo_name}")
            except Exception as e:
                self.logger.error(f"Failed to fetch repository: {str(e)}")
                raise ValueError("Invalid repository configuration.")
        return self._repo

    def get_open_issues(self) -> list:
        """Fetch all open issues from the repository."""
        return list(self.repo.get_issues(state="open"))

    def get_open_pull_requests(self) -> list:
        """Fetch all open pull requests from the repository."""
        return list(self.repo.get_pulls(state="open"))

    def find_assigned_issue(self, target_username: str):
        """Find an open issue assigned to the specified username."""
        for issue in self.get_open_issues():
            if issue.assignee and issue.assignee.login == target_username:
                return issue
        return None

    def create_pull_request(self, base_branch: str, head_branch: str, title: str, body: str) -> bool:
        """Create a new pull request for the given issue.
        The PR description includes the issue number and a brief description of the changes.
        """
        try:
            pr = self.repo.create_pull(
                title=title,
                body=f"This pull request addresses issue #{issue.number}. {body}",
                head=head_branch,
                base=base_branch
            )
            self.logger.info(f"Pull request created: {pr.html_url}")
        except Exception as e:
            self.logger.error(f"Failed to create pull request: {str(e)}")
