import logging
import os
import re

import git_api
from github_api import GithubClient
from issue_parser import IssueDescriptionParser
from aider.coders import Coder
from aider.models import Model

from config import REPO_NAME, USERNAME, MODEL, ANTHROPIC_API_KEY, PRIORITY_LABELS

logging.basicConfig(level=logging.INFO)


def configure_logging():
    logging.basicConfig(level=logging.INFO)


def get_anthropic_api_key():
    api_key = ANTHROPIC_API_KEY
    if not api_key:
        logging.error("ANTHROPIC_API_KEY environment variable is not set")
        return None
    return api_key


def create_branch_name(issue):
    return re.sub(" ", "_", issue.title.lower())


def checkout_branch(git_client, branch_name):
    git_client.checkout("main")
    git_client.create_and_checkout_branch(branch_name)


def parse_issue(parser, issue):
    parsed_issue = parser.parse_description(issue.body)
    instructions = parsed_issue.get("instructions")
    files = parsed_issue.get("files")
    logging.info(f"****** Instructions: {instructions}")
    logging.info(f"****** Files: {files}")
    return instructions, files


def execute_instructions(coder, instructions):
    result = coder.run(".".join(instructions))
    logging.info(f"****** Result: {result}")
    changes_made = result
    return changes_made


def push_branch(git_client, branch_name):
    git_client.push(branch_name)
    logging.info("****** Pushed branch")


def create_pull_request(github_client, issue, branch_name, author, changes_made):
    pr = github_client.create_pull_request(base_branch="main", head_branch=branch_name, body=f"This is the result of fixit for issue {issue.number}\n\ncc @{author}\n\n{changes_made}", title=issue.title, issue=issue)
    logging.info("****** Creating pull request********")
    return pr


def comment_on_issue(github_client, issue, pr_url):
    issue.create_comment(f"A pull request has been created to address this issue: {pr_url}")
    logging.info("****** Commented on the issue ********")


def main():
    """
    The main function that orchestrates the entire process of fixing a prioritized issue.

    This function performs the following steps:
    1. Configures logging.
    2. Retrieves the Anthropic API key.
    3. Initializes the GitHub client with the repository name.
    4. Retrieves the prioritized issues from the GitHub repository.
    5. Selects the first prioritized issue.
    6. Creates a branch name based on the issue title.
    7. Checks out the new branch.
    8. Parses the issue description to extract instructions and files.
    9. Executes the instructions using the Coder and Model from the Aider library.
    10. Pushes the changes to the new branch.
    11. Creates a pull request for the new branch.
    12. Comments on the original issue with the pull request URL.
    13. Prints the changes made.

    Returns:
        None
    """
    configure_logging()
    api_key = get_anthropic_api_key()
    if not api_key:
        return

    logging.info(f"Repo name: {REPO_NAME}")
    github_client = GithubClient(REPO_NAME)

    priority_issues = github_client.get_prioritized_issues(username=USERNAME, priority_labels=PRIORITY_LABELS)

    if priority_issues:
        issue = priority_issues[0]
    else:
        return

    branch_name = create_branch_name(issue)
    logging.info(f"****** Branch name: {branch_name}")

    git_client = git_api.GitManager(REPO_NAME)
    checkout_branch(git_client, branch_name)

    parser = IssueDescriptionParser(api_key)
    instructions, files = parse_issue(parser, issue)
    if not instructions:
        logging.warning("Invalid issue data. Skipping processing.")
        return

    os.environ['AIDER_CONFIG'] = str("aider.conf.yml")
    model = Model(MODEL)
    coder = Coder.create(main_model=model, fnames=files)
    changes_made = execute_instructions(coder, instructions)

    push_branch(git_client, branch_name)
    pr = create_pull_request(github_client, issue, branch_name, issue.user.login, changes_made)
    comment_on_issue(github_client, issue, pr.html_url)

    print("\n\n")
    print(changes_made)

if __name__ == "__main__":
    main()
