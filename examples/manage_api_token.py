"""Usage example for oqtopus-client: inspect and revoke the API token.

Q-API-Tokens are now ISSUED from an interactive (OIDC) session via the web
console; a client authenticated with a Q-API-Token can no longer mint a new one
(the server returns HTTP 403), so ``create_api_token`` is deprecated and not
shown here. This example inspects the current token's status and revokes it.
"""

from __future__ import annotations

import os

from oqtopus_client import OqtopusClient, OqtopusConfig

SECTION = os.getenv("OQTOPUS_CONFIG_SECTION", "oqtopus-dev")
CONFIG_PATH = os.getenv("OQTOPUS_CONFIG_PATH", "~/.config/oqtopus/config.ini")

client = OqtopusClient(OqtopusConfig.from_file(SECTION, path=CONFIG_PATH))
print("api_token_status:", client.get_api_token_status())
# NOTE: this revokes the token this client is currently authenticating with.
client.delete_api_token()
print("delete_api_token: done")
