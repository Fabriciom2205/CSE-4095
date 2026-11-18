"""Google Cloud client for agent and embedding requests."""

import os
from google import genai


def create_client():
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project:
        raise ValueError("GOOGLE_CLOUD_PROJECT is not configured; set it in the repository .env file.")
    return genai.Client(
        enterprise=True,
        project=project,
        location=os.getenv("GOOGLE_CLOUD_LOCATION", "global"),
        http_options={"api_version": "v1"},
    )
