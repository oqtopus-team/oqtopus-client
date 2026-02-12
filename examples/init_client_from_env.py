from __future__ import annotations

import os

from oqtopus_client import OqtopusClient, OqtopusConfig


SECTION = os.getenv("OQTOPUS_CONFIG_SECTION", "oqtopus-dev")
CONFIG_PATH = os.getenv("OQTOPUS_CONFIG_PATH", "~/.oqtopus")

config = OqtopusConfig.from_file(SECTION, path=CONFIG_PATH)
if not os.getenv("OQTOPUS_BASE_URL"):
    os.environ["OQTOPUS_BASE_URL"] = config.base_url
if config.api_token and not os.getenv("OQTOPUS_API_TOKEN"):
    os.environ["OQTOPUS_API_TOKEN"] = config.api_token
if config.api_token_file and not os.getenv("OQTOPUS_API_TOKEN_FILE"):
    os.environ["OQTOPUS_API_TOKEN_FILE"] = str(config.api_token_file)

env_config = OqtopusConfig.from_env()

with OqtopusClient(env_config) as client:
    print("client.base_url:", client.base_url)
    print("client.timeout:", client.timeout)
    print("client.retry_max_attempts:", client.retry_max_attempts)
    print("client.retry_backoff_seconds:", client.retry_backoff_seconds)
    print("client.retry_status_codes:", sorted(client.retry_status_codes))
    print("client.retry_methods:", sorted(client.retry_methods))

    if env_config.api_token:
        client.set_api_token(env_config.api_token)
        print("set_api_token: done")
