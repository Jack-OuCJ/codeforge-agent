from __future__ import annotations

import dashscope

from config.settings import settings


def configure_dashscope_client() -> None:
    if settings.DASHSCOPE_API_KEY:
        dashscope.api_key = settings.DASHSCOPE_API_KEY
    if settings.DASHSCOPE_BASE_HTTP_API_URL:
        dashscope.base_http_api_url = settings.DASHSCOPE_BASE_HTTP_API_URL
