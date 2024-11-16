import requests

def fetch_open_prs(owner, repo):
    """
    Fetch all open pull requests for a given repository.
    
    Args:
        owner (str): The GitHub username or organization name.
        repo (str): The name of the repository.
    
    Returns:
        list: A list of open pull request objects.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls?state=open"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def fetch_closed_prs(owner, repo):
    """
    Fetch all closed pull requests for a given repository.
    
    Args:
        owner (str): The GitHub username or organization name.
        repo (str): The name of the repository.
    
    Returns:
        list: A list of closed pull request objects.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls?state=closed"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()
