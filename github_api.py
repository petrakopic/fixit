import os
from github import Github
import logging

REPO_NAME = "petrakopic/fixit"


class GithubClient:
    def __init__(self, repo_name: str):
        self.github = Github(os.environ.get("GITHUB_TOKEN"))
        self.repo_name = repo_name
        self.logger = logging.getLogger(__name__)
        self._repo = None

    @property
    def repo(self):
        """
        Property to lazily initialize and return the repository object.
        """
        if self._repo is None:
            try:
                self._repo = self.github.get_repo(self.repo_name)
                self.logger.info(f"Successfully fetched repository: {self.repo_name}")
            except Exception as e:
                self.logger.error(f"Failed to fetch repository: {str(e)}")
                raise ValueError("Invalid repository configuration.")
        return self._repo

    def get_open_issues(self):
        return self.repo.get_issues(state="open")

    def get_open_pull_requests(self):
        return self.repo.get_pulls(state="open")

    def find_assigned_issue(self, target_username):
        for issue in self.get_open_issues():
            if issue.assignee and issue.assignee.login == target_username:
                return issue
        return None

    def create_pull_request(self, base_branch, head_branch, title, body):
        try:
            pr = self.repo.create_pull(
                title=title,
                body=f"This pull request addresses the issue #{issue.number}. {body}",
                head=head_branch,
                base=base_branch
            )
            self.logger.info(f"Pull request created: {pr.html_url}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create pull request: {str(e)}")
