class ParserError(Exception):
    """Exception raised for errors in the IssueDescriptionParser"""
    pass


class IssueDescriptionParser:
    def __init__(self, api_key: str):
        """Initialize the parser with your Anthropic API key."""
        self.api_key = api_key

    def parse_description(self, issue_description: str) -> dict:
        """
        Parse the issue description to extract instructions and files.

        Args:
            issue_description (str): The description of the GitHub issue.

        Returns:
            dict: A dictionary containing the extracted instructions and files.
                  The keys are "instructions" and "files".

        Raises:
            ParserError: If there is an error parsing the issue description.
        """
        try:
            # Implement the parsing logic here
            instructions = "..."
            files = ["..."]
            return {"instructions": instructions, "files": files}
        except Exception as e:
            raise ParserError(f"Error parsing issue description: {str(e)}") from e
