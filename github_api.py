import os
from github import Github, PullRequest, Issue
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

    def create_pull_request(self, base_branch: str, head_branch: str, title: str, body: str, issue: Issue) -> PullRequest.PullRequest | None:
        """Create a new pull request for the given issue."""
        try:
            pr = self.repo.create_pull(
                title=title,
                body=f"Fixes #{issue.number}\n\n{body}",
                head=head_branch,
                base=base_branch
            )
            self.logger.info(f"Pull request created: {pr.html_url}")
            # Link the issue to the PR
            try:
                # This creates the connection in the Development panel
                issue.edit(
                    state='open',  # Ensure we don't accidentally close the issue
                    labels=list(issue.labels),  # Preserve existing labels
                    assignee=issue.assignee.login if issue.assignee else None,  # Preserve assignee
                    linked_pull_requests=[pr]  # Link the PR
                )
                self.logger.info(f"Successfully linked issue #{issue.number} to PR #{pr.number}")
            except Exception as e:
                self.logger.error(f"Failed to link issue to PR in Development panel: {str(e)}")
                # Note: PR is still created even if linking fails

            return pr
        except Exception as e:
            self.logger.error(f"Failed to create pull request: {str(e)}")
