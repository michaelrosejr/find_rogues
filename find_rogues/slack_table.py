import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from tabulate import tabulate
import tempfile
import yaml

with open(".env.yaml", "r") as envf:
    central_info = yaml.safe_load(envf)


class SlackTableUploader:
    """A class to handle uploading ASCII tables to Slack channels."""

    def __init__(self, token):
        """
        Initialize the Slack client with the provided token.

        Args:
            token (str): Slack Bot User OAuth Token
        """
        self.client = WebClient(token=token)

    def create_ascii_table(self, data, headers=None, table_format="grid"):
        """
        Create an ASCII table from the provided data.

        Args:
            data (list): List of lists containing the table data
            headers (list, optional): List of column headers
            table_format (str, optional): Format for tabulate (default: "grid")

        Returns:
            str: Formatted ASCII table
        """
        return tabulate(data, headers=headers, tablefmt=table_format)

    def upload_table(
        self, table_content, channel, filename="table.txt", initial_comment=None
    ):
        """
        Upload an ASCII table to a Slack channel.

        Args:
            table_content (str): The formatted ASCII table content
            channel (str): The channel ID or name to upload to
            filename (str, optional): Name of the file in Slack
            initial_comment (str, optional): Comment to accompany the upload

        Returns:
            dict: Response from Slack API

        Raises:
            SlackApiError: If the upload fails
        """
        try:
            # Create a temporary file to store the table
            with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
                tmp.write(table_content)
                tmp.flush()

                # Upload the file to Slack
                response = self.client.files_upload_v2(
                    channel=channel,
                    file=tmp.name,
                    filename=filename,
                    initial_comment=initial_comment,
                )

            # Clean up temporary file
            os.unlink(tmp.name)

            return response
        except SlackApiError as e:
            error_message = f"Failed to upload table: {e.response['error']}"
            raise SlackApiError(error_message, e.response)


def main():
    """Example usage of the SlackTableUploader class."""
    # Example data
    account = "default"
    data = [
        ["John", 30, "New York"],
        ["Alice", 25, "Los Angeles"],
        ["Bob", 35, "Chicago"],
    ]
    headers = ["Name", "Age", "City"]

    # Initialize uploader with your Slack token
    token = central_info[account]["slack_bot_token"]
    if not token:
        raise ValueError("slack_bot_token environment variable not set")

    uploader = SlackTableUploader(token)

    # Create ASCII table
    table = uploader.create_ascii_table(data, headers)

    # Upload to Slack
    try:
        response = uploader.upload_table(
            table,
            channel="C04P5CJHREX",
            filename="rogue_data.txt",
            initial_comment="Rogue SSIDs:",
        )
        print("Table uploaded successfully!")
    except SlackApiError as e:
        print(f"Error uploading table: {e}")


if __name__ == "__main__":
    main()
