import json
import os
import time
from typing import Annotated, Any, ClassVar, Literal

from crewai.tools import BaseTool, EnvVar
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic.types import StringConstraints
import requests

from crewai_tools.tools.brave_search_tool.base import _save_results_to_file
from crewai_tools.tools.brave_search_tool.schemas import WebSearchParams


load_dotenv()


FreshnessPreset = Literal["pd", "pw", "pm", "py"]
FreshnessRange = Annotated[
    str, StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}to\d{4}-\d{2}-\d{2}$")
]
Freshness = FreshnessPreset | FreshnessRange
SafeSearch = Literal["off", "moderate", "strict"]


# TODO: Extend support to additional endpoints (e.g., /images, /news, etc.)
class BraveSearchTool(BaseTool):
    """A tool that performs web searches using the Brave Search API."""

    name: str = "Brave Search"
    description: str = (
        "A tool that performs web searches using the Brave Search API. "
        "Results are returned as structured JSON data."
    )
    args_schema: type[BaseModel] = WebSearchParams
    search_url: str = "https://api.search.brave.com/res/v1/web/search"
    n_results: int = 10
    save_file: bool = False
    env_vars: list[EnvVar] = Field(
        default_factory=lambda: [
            EnvVar(
                name="BRAVE_API_KEY",
                description="API key for Brave Search",
                required=True,
            ),
        ]
    )
    # Rate limiting parameters
    _last_request_time: ClassVar[float] = 0
    _min_request_interval: ClassVar[float] = 1.0  # seconds

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if "BRAVE_API_KEY" not in os.environ:
            raise ValueError(
                "BRAVE_API_KEY environment variable is required for BraveSearchTool"
            )

    def _run(
        self,
        **kwargs: Any,
    ) -> Any:
        current_time = time.time()
        if (current_time - self._last_request_time) < self._min_request_interval:
            time.sleep(
                self._min_request_interval - (current_time - self._last_request_time)
            )
        BraveSearchTool._last_request_time = time.time()

        # Construct and send the request
        try:
            # Fallback to "query" or "search_query" for backwards compatibility
            query = kwargs.get("q") or kwargs.get("query") or kwargs.get("search_query")
            if not query:
                raise ValueError("Query is required")

            payload = {"q": query}

            if country := kwargs.get("country"):
                payload["country"] = country

            # Fallback to "search_language" for backwards compatibility
            if search_lang := kwargs.get("search_lang") or kwargs.get(
                "search_language"
            ):
                payload["search_lang"] = search_lang

            # Fallback to deprecated n_results parameter if no count is provided
            count = kwargs.get("count")
            if count is not None:
                payload["count"] = count
            else:
                payload["count"] = self.n_results

            # Offset may be 0, so avoid truthiness check
            offset = kwargs.get("offset")
            if offset is not None:
                payload["offset"] = offset

            if safesearch := kwargs.get("safesearch"):
                payload["safesearch"] = safesearch

            save_file = kwargs.get("save_file", self.save_file)
            if freshness := kwargs.get("freshness"):
                payload["freshness"] = freshness

            # Boolean parameters
            spellcheck = kwargs.get("spellcheck")
            if spellcheck is not None:
                payload["spellcheck"] = spellcheck

            text_decorations = kwargs.get("text_decorations")
            if text_decorations is not None:
                payload["text_decorations"] = text_decorations

            extra_snippets = kwargs.get("extra_snippets")
            if extra_snippets is not None:
                payload["extra_snippets"] = extra_snippets

            operators = kwargs.get("operators")
            if operators is not None:
                payload["operators"] = operators

            # Removed result_filter to allow other result types like "discussions", "faq", etc.

            # Setup Request Headers
            headers = {
                "X-Subscription-Token": os.environ["BRAVE_API_KEY"],
                "Accept": "application/json",
            }

            response = requests.get(
                self.search_url, headers=headers, params=payload, timeout=30
            )
            response.raise_for_status()  # Handle non-200 responses
            results = response.json()

            # Handle multiple result types
            all_results_items = []

            # Process web results
            if "web" in results:
                web_results = results["web"].get("results", [])
                for result in web_results:
                    url = result.get("url")
                    title = result.get("title")
                    if not url or not title:
                        continue
                    item = {"url": url, "title": title, "type": "web"}
                    if description := result.get("description"):
                        item["description"] = description
                    if snippets := result.get("extra_snippets"):
                        item["snippets"] = snippets
                    all_results_items.append(item)

            # Process discussions
            if "discussions" in results:
                discussion_results = results["discussions"].get("results", [])
                for result in discussion_results:
                    url = result.get("url")
                    title = result.get("title")
                    if not url or not title:
                        continue
                    item = {"url": url, "title": title, "type": "discussion"}
                    if description := result.get("description"):
                        item["description"] = description
                    all_results_items.append(item)

            # Process faq
            if "faq" in results:
                faq_results = results["faq"].get("results", [])
                for result in faq_results:
                    url = result.get("url")
                    title = result.get("title") or result.get("question")
                    if not url or not title:
                        continue
                    item = {"url": url, "title": title, "type": "faq"}
                    if answer := result.get("answer"):
                        item["description"] = answer
                    elif description := result.get("description"):
                        item["description"] = description
                    all_results_items.append(item)

            # Process news
            if "news" in results:
                news_results = results["news"].get("results", [])
                for result in news_results:
                    url = result.get("url")
                    title = result.get("title")
                    if not url or not title:
                        continue
                    item = {"url": url, "title": title, "type": "news"}
                    if description := result.get("description"):
                        item["description"] = description
                    all_results_items.append(item)

            # Process locations
            if "locations" in results:
                location_results = results["locations"].get("results", [])
                for result in location_results:
                    url = result.get("url")
                    title = result.get("title")
                    if not url or not title:
                        continue
                    item = {"url": url, "title": title, "type": "location"}
                    if description := result.get("description"):
                        item["description"] = description
                    all_results_items.append(item)

            # Process videos
            if "videos" in results:
                video_results = results["videos"].get("results", [])
                for result in video_results:
                    url = result.get("url")
                    title = result.get("title")
                    if not url or not title:
                        continue
                    item = {"url": url, "title": title, "type": "video"}
                    if description := result.get("description"):
                        item["description"] = description
                    all_results_items.append(item)

            # Process infobox
            if "infobox" in results:
                infobox_results = results["infobox"].get("results", [])
                for result in infobox_results:
                    url = result.get("url")
                    title = result.get("title")
                    if not url or not title:
                        continue
                    item = {"url": url, "title": title, "type": "infobox"}
                    if description := result.get("description"):
                        item["description"] = description
                    all_results_items.append(item)

            content = json.dumps(all_results_items)
        except requests.RequestException as e:
            return f"Error performing search: {e!s}"
        except KeyError as e:
            return f"Error parsing search results: {e!s}"
        if save_file:
            _save_results_to_file(content)
            return f"\nSearch results: {content}\n"
        return content
