import anthropic
import json


class IssueDescriptionParser:
    def __init__(self, api_key: str):
        """Initialize the parser with your Anthropic API key."""
        self.client = anthropic.Client(api_key=api_key)

    def parse_description(self, pr_description: str) -> dict:
        """
        Parse the PR description to extract the main message and files.

        Returns:
            Tuple containing (clear_message, list_of_files)
        """
        prompt = f"""Extract information from this PR description:
        1. List the instructions/changes exactly as they are mentioned in the PR description, without adding any new steps or modifying the intent. Keep the original phrasing where possible.
        2. List all files that are mentioned as being modified or created.

        Respond in this exact format (keep the quotes):
        {{
            "instructions": [
                "instruction 1",
                "instruction 2",
                ...
            ],
            "files": [
                "file/path1.ext",
                "file/path2.ext",
                ...
            ]
        }}

        PR Description:
        {pr_description}"""

        # Call Claude API
        message = self.client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        # Parse Claude's response as a Python dictionary
        try:
            response_dict = json.loads(message.content[0].text.strip())
        except json.JSONDecodeError:
            # Fallback if response isn't valid JSON
            response_dict = {
                "instructions": ["Error parsing response"],
                "files": []
            }

        return response_dict