import logging
import os
from github import Github, PullRequest, Issue

class GithubError(Exception):
    """Exception raised for errors in the GithubClient"""
    pass


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
            raise GithubError("GITHUB_TOKEN environment variable not set.")
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
                raise GithubError("Invalid repository configuration.") from e
        return self._repo

    def get_open_issues(self) -> list[Issue]:
        """Fetch all open issues from the repository."""
        return list(self.repo.get_issues(state="open"))

    def get_open_pull_requests(self) -> list[PullRequest.PullRequest]:
        """Fetch all open pull requests from the repository."""
        return list(self.repo.get_pulls(state="open"))

    def get_prioritized_issues(
          self,
          username: str,
          priority_labels: set[str],
    ) -> list[Issue]:
        """
        Get open issues assigned to username with priority labels, sorted by creation date.
        """
        try:
            prioritized_issues = [
                issue for issue in self.get_open_issues()
                if issue.assignee
                   and issue.assignee.login == username
                   and any(label.name in priority_labels for label in issue.labels)
            ]

            # Sort by creation date (oldest first)
            prioritized_issues.sort(key=lambda x: x.created_at)

            self.logger.info(f"Found {len(prioritized_issues)} prioritized issues for {username}")
            return prioritized_issues
        except Exception as e:
            self.logger.error(f"Error fetching prioritized issues: {str(e)}")
            raise GithubError("Failed to fetch prioritized issues") from e

    def create_pull_request(
          self,
          base_branch: str,
          head_branch: str,
          title: str,
          body: str,
          issue: Issue
    ) -> PullRequest.PullRequest | None:
        """Create a new pull request and link it to the given issue."""
        try:
            pr = self.repo.create_pull(
                title=title,
                body=f"Fixes #{issue.number}\n\n{body}",
                head=head_branch,
                base=base_branch
            )
            self.logger.info(f"Pull request created: {pr.html_url}")

            try:
                issue.edit(
                    state='open',
                    labels=list(issue.labels),
                    assignee=issue.assignee.login if issue.assignee else None,
                    linked_pull_requests=[pr]
                )
                self.logger.info(f"Successfully linked issue #{issue.number} to PR #{pr.number}")
            except Exception as e:
                self.logger.error(f"Failed to link issue to PR in Development panel: {str(e)}")

            return pr
        except Exception as e:
            self.logger.error(f"Failed to create pull request: {str(e)}")
            raise GithubError("Failed to create pull request") from e
