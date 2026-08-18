import json
import unittest
from unittest.mock import AsyncMock

import httpx

from panel_nodes import NodeError, PanelNodeClient, normalize_base_url


def response(data, status=200):
    request = httpx.Request("GET", "https://node.example/test")
    return httpx.Response(status, json=data, request=request)


class NormalizeUrlTests(unittest.TestCase):
    def test_normalizes_trailing_slash(self):
        self.assertEqual(normalize_base_url(" https://node.example/panel/ "), "https://node.example/panel")

    def test_rejects_non_http_and_credentials(self):
        with self.assertRaises(NodeError):
            normalize_base_url("file:///etc/passwd")
        with self.assertRaises(NodeError):
            normalize_base_url("https://admin:secret@node.example")


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self):
        client = getattr(self, "client", None)
        if client:
            await client.client.aclose()

    async def test_rvg_overview_is_normalized(self):
        self.client = PanelNodeClient({
            "panel_type": "rvg", "base_url": "https://node.example",
            "auth_type": "token", "token": "secret",
        })
        self.client._request = AsyncMock(return_value=response({
            "version": "9.6", "links_count": 4, "active_links": 3,
            "active_connections": 2, "total_bytes": 1024, "uptime": "00:01:00",
        }))
        data = await self.client.overview()
        self.assertEqual(data["users"], 4)
        self.assertEqual(data["active"], 3)
        self.assertEqual(data["traffic_bytes"], 1024)
        self.client._request.assert_awaited_once_with("GET", "/api/node/v1/overview")

    async def test_xui_inbounds_are_normalized(self):
        self.client = PanelNodeClient({
            "panel_type": "xui", "base_url": "https://node.example",
            "auth_type": "token", "token": "secret",
        })
        settings = json.dumps({"clients": [{"id": "a", "enable": True}, {"id": "b", "enable": False}]})
        self.client._request = AsyncMock(return_value=response({"success": True, "obj": [
            {"id": 7, "remark": "main", "enable": True, "up": 10, "down": 20, "settings": settings}
        ]}))
        data = await self.client.overview()
        self.assertEqual(data["users"], 2)
        self.assertEqual(data["active"], 1)
        self.assertEqual(data["traffic_bytes"], 30)
        self.assertEqual(data["inbounds"], 1)

    async def test_marzban_config_normalization(self):
        self.client = PanelNodeClient({
            "panel_type": "marzban", "base_url": "https://node.example",
            "auth_type": "token", "token": "secret",
        })
        self.client._request = AsyncMock(return_value=response({"users": [{
            "username": "ali", "status": "active", "used_traffic": 12,
            "data_limit": 100, "subscription_url": "https://node.example/sub/ali",
        }]}))
        configs = await self.client.list_configs()
        self.assertEqual(configs[0]["id"], "ali")
        self.assertTrue(configs[0]["active"])
        self.assertEqual(configs[0]["subscription_url"], "https://node.example/sub/ali")


if __name__ == "__main__":
    unittest.main()
