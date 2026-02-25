from __future__ import annotations

import os

from oqtopus_client import OqtopusClient, OqtopusConfig


SECTION = os.getenv("OQTOPUS_CONFIG_SECTION", "oqtopus-dev")
CONFIG_PATH = os.getenv("OQTOPUS_CONFIG_PATH", "~/.config/oqtopus/config.ini")

client = OqtopusClient(OqtopusConfig.from_file(SECTION, path=CONFIG_PATH))
print("announcements_list:", client.get_announcements_list())
print("api_token:", client.get_api_token())
