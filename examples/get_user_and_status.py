from __future__ import annotations

import os

from oqtopus_client import OqtopusClient, OqtopusConfig


SECTION = os.getenv("OQTOPUS_CONFIG_SECTION", "oqtopus-dev")
CONFIG_PATH = os.getenv("OQTOPUS_CONFIG_PATH", "~/.oqtopus")

with OqtopusClient(OqtopusConfig.from_file(SECTION, path=CONFIG_PATH)) as client:
    print("current_user:", client.get_current_user())
    print("announcements_list:", client.get_announcements_list())
    created = client.create_api_token()
    print("create_api_token:", created)
    print("api_token_status:", client.get_api_token_status())
