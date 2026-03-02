"""Usage example for oqtopus-client."""

from __future__ import annotations

import os

from oqtopus_client import OqtopusClient, OqtopusConfig

SECTION = os.getenv("OQTOPUS_CONFIG_SECTION", "oqtopus-dev")
CONFIG_PATH = os.getenv("OQTOPUS_CONFIG_PATH", "~/.config/oqtopus/config.ini")

client = OqtopusClient(OqtopusConfig.from_file(SECTION, path=CONFIG_PATH))
token = client.create_api_token()
print("create_api_token:", token)
client.delete_api_token()
print("delete_api_token: done")
