from langchain.tools import tool
import httpx

@tool
def wikipedia(query: str) -> str:
    """
    Search Wikipedia for a given query and return the summary of the first matching article.

    Example usage:
    wikipedia("Python programming language") -> "Python is an interpreted, high-level..."

    If no article is found, returns "No Wikipedia article found".
    """
    url = "https://en.wikipedia.org/w/api.php"
    try:
        # Search for articles
        response = httpx.get(
            url,
            params={"action": "query", "list": "search", "srsearch": query, "format": "json"},
            headers={"User-Agent": "Telegram-Gaia-Agent/1.0"}
        )
        searches = response.json().get("query", {}).get("search", [])
        if not searches:
            return "No Wikipedia article found"

        # Get first article summary
        page_id = str(searches[0]["pageid"])
        page = httpx.get(
            url,
            params={
                "action": "query",
                "prop": "extracts",
                "explaintext": True,
                "exintro": True,
                "pageids": page_id,
                "format": "json"
            },
            headers={"User-Agent": "Telegram-Gaia-Agent/1.0"}
        ).json()

        return page["query"]["pages"][page_id]["extract"]
    except Exception as e:
        return f"Error: {e}"
