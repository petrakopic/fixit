import logging
import os
import re

import git_api
from github_api import GithubClient
from issue_parser import IssueDescriptionParser
from aider.coders import Coder
from aider.models import Model

model = "claude-3-haiku-20240307"

logging.basicConfig(level=logging.INFO)

USERNAME = "petrakopic"
MODEL = "claude-3-haiku-20240307"
REPO_NAME = "petrakopic/fixit"


def main():
    # Configuration
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
    print(f"Repo name: {REPO_NAME}")
    # Initialize components
    github_client = GithubClient(REPO_NAME)

    # Get the first open issue assigned to the target user
    issue = github_client.find_assigned_issue(USERNAME)
    if not issue:
        logging.info("No open issues found for the target user.")
        return

    branch_name = re.sub(" ","_", issue.title.lower())
    print(f"****** Branch name: {branch_name}")

    git_client=git_api.GitManager(REPO_NAME)
    git_client.checkout("main")
    git_client.create_and_checkout_branch(branch_name)

    # Parse the issue
    parser = IssueDescriptionParser(os.environ["ANTHROPIC_API_KEY"])
    parsed_issue = parser.parse_description(issue.body)
    instructions = parsed_issue.get("instructions")
    files = parsed_issue.get("files")
    print(f"****** Instructions: {instructions}")
    print(f"****** Files: {files}")

    if not instructions or not files:
        logging.warning("Invalid issue data. Skipping processing.")
        return

    # Create a coder object
    model = Model(MODEL)

    # Create a coder object
    coder = Coder.create(main_model=model, fnames=files)

    # This will execute one instruction on those files and then return
    result=coder.run(f"{instructions[0]}")
    print(f"****** Result: {result}")

    git_client.push(branch_name)
    print("****** Pushed branch")
    # Create a pull request
    print("****** Creating pull request********")
    github_client.create_pull_request("main", branch_name, body=f"This is the result of fixit for issue {issue.number}", title=f"Fixit for issue {issue.number}")

if __name__ == "__main__":
    main()