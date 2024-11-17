import logging

class ParserException(Exception):
    pass

class IssueDescriptionParser:
    def __init__(self, api_key: str):
        """Initialize the parser with your Anthropic API key."""
        self.api_key = api_key
        self.logger = logging.getLogger(__name__)

    def parse_description(self, issue_description: str) -> dict:
        """
        Parse the issue description to extract instructions and files.

        Raises:
            ParserException: If there is an error parsing the issue description.
        """
        try:
            # Implement the parsing logic here
            instructions = "..."
            files = ["..."]

            self.logger.info("📝 Parsed Fixit task:"
                             f"\n\tInstructions: {instructions}"
                             f"\n\tFiles: {files}")

            return {"instructions": instructions, "files": files}
        except Exception as e:
            self.logger.error(f"❌ Error parsing Fixit task: {str(e)}")
            raise ParserException("Failed to parse issue description") from e
