import os
import unittest
from unittest import mock

import search
from search import get_api_key, validate_api_key


class FirecrawlProviderTests(unittest.TestCase):
    def test_get_api_key_reads_firecrawl_env(self):
        with mock.patch.dict(os.environ, {"FIRECRAWL_API_KEY": "fc-test-key"}, clear=False):
            self.assertEqual(get_api_key("firecrawl", {}), "fc-test-key")

    def test_validate_api_key_accepts_firecrawl(self):
        with mock.patch.dict(os.environ, {"FIRECRAWL_API_KEY": "fc-test-key-12345"}, clear=False):
            self.assertEqual(validate_api_key("firecrawl", {}), "fc-test-key-12345")

    def test_search_firecrawl_parses_web_results(self):
        fake_response = {
            "success": True,
            "data": {
                "web": [
                    {
                        "title": "Example result",
                        "url": "https://example.com/page",
                        "description": "Example snippet",
                        "position": 1,
                    }
                ]
            },
            "creditsUsed": 1,
        }
        with mock.patch("search.make_request", return_value=fake_response) as mock_request:
            result = search.search_firecrawl(
                query="example query",
                api_key="fc-test-key-12345",
                max_results=5,
                country="US",
                time_range="week",
            )

        self.assertEqual(result["provider"], "firecrawl")
        self.assertEqual(result["results"][0]["title"], "Example result")
        self.assertEqual(result["results"][0]["url"], "https://example.com/page")
        self.assertEqual(result["results"][0]["snippet"], "Example snippet")
        self.assertEqual(result["credits_used"], 1)

        _, headers, body = mock_request.call_args.args[:3]
        self.assertEqual(headers["Authorization"], "Bearer fc-test-key-12345")
        self.assertEqual(body["query"], "example query")
        self.assertEqual(body["limit"], 5)
        self.assertEqual(body["sources"], ["web"])
        self.assertEqual(body["country"], "US")
        self.assertEqual(body["tbs"], "qdr:w")


if __name__ == "__main__":
    unittest.main()
