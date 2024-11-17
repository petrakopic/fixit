import logging
import os
import re

import git_api
from github_api import GithubClient
from issue_parser import IssueDescriptionParser
from aider.coders import Coder
from aider.models import Model

from config import REPO_NAME, USERNAME, MODEL, ANTHROPIC_API_KEY

logging.basicConfig(level=logging.INFO)


def configure_logging():
    logging.basicConfig(level=logging.INFO)


def get_anthropic_api_key():
    api_key = ANTHROPIC_API_KEY
    if not api_key:
        logging.error("ANTHROPIC_API_KEY environment variable is not set")
        return None
    return api_key


def get_first_open_issue(github_client, username):
    issue = github_client.find_assigned_issue(username)
    if not issue:
        logging.info("No open issues found for the target user.")
        return None
    return issue


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
    pr = github_client.create_pull_request("main", branch_name, body=f"This is the result of fixit for issue {issue.number}\n\ncc @{author}\n\n{changes_made}", title=f"Fixit for issue {issue.number}")
    logging.info("****** Creating pull request********")
    return pr


def comment_on_issue(github_client, issue, pr_url):
    issue.create_comment(f"A pull request has been created to address this issue: {pr_url}")
    logging.info("****** Commented on the issue ********")


def main():
    configure_logging()
    api_key = get_anthropic_api_key()
    if not api_key:
        return

    logging.info(f"Repo name: {REPO_NAME}")
    github_client = GithubClient(REPO_NAME)
    issue = get_first_open_issue(github_client, USERNAME)
    if not issue:
        return

    branch_name = create_branch_name(issue)
    logging.info(f"****** Branch name: {branch_name}")

    git_client = git_api.GitManager(REPO_NAME)
    checkout_branch(git_client, branch_name)

    parser = IssueDescriptionParser(api_key)
    instructions, files = parse_issue(parser, issue)
    if not instructions or not files:
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
