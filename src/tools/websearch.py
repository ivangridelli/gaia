from langchain.tools import tool
import httpx


@tool
def web_search(query: str) -> str:
    """
    Perform a web search and return a summary of the first result.

    Args:
        query: Search query

    Returns:
        Summary of first result or fallback message
    """
    url = f"https://api.duckduckgo.com/?q={query}&format=json&no_redirect=1"
    try:
        r = httpx.get(url, timeout=5)
        data = r.json()
        abstract = data.get("AbstractText")
        if abstract:
            return abstract
        # If no abstract, try first URL
        related_topics = data.get("RelatedTopics")
        if related_topics and isinstance(related_topics, list):
            first = related_topics[0]
            return first.get("Text", "No summary found.")
        return "No good result found."
    except Exception as e:
        return f"Error searching web: {e}"
