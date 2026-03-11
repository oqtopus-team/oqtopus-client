"""Usage example for oqtopus-client."""

from __future__ import annotations

import os

from oqtopus_client import OqtopusClient, OqtopusConfig

SECTION = os.getenv("OQTOPUS_CONFIG_SECTION", "oqtopus-dev")
CONFIG_PATH = os.getenv("OQTOPUS_CONFIG_PATH", "~/.config/oqtopus/config.ini")

client = OqtopusClient(OqtopusConfig.from_file(SECTION, path=CONFIG_PATH))
announcements = client.get_announcements_list()
announcement_count = (
    0 if announcements.announcements is None else len(announcements.announcements)
)
print("announcement_count:", announcement_count)
if announcements.announcements:
    detail = client.get_announcement(announcements.announcements[0].id)
    print("get_announcement:", detail.id, detail.title)
