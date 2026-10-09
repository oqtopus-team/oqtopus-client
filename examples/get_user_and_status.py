"""Usage example for oqtopus-client."""

from __future__ import annotations

import os

from oqtopus_client import OqtopusClient, OqtopusConfig

SECTION = os.getenv("OQTOPUS_CONFIG_SECTION", "oqtopus-dev")
CONFIG_PATH = os.getenv("OQTOPUS_CONFIG_PATH", "~/.config/oqtopus/config.ini")

client = OqtopusClient(OqtopusConfig.from_file(SECTION, path=CONFIG_PATH))
print("announcements_list:", client.get_announcements_list())
# NOTE: create_api_token is deprecated and rejected (403) for Q-API-Token
# callers; Q-API-Tokens are issued from an interactive (OIDC) session via the
# web console. This example only inspects the current token's status.
print("api_token_status:", client.get_api_token_status())
