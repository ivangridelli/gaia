from langchain.tools import tool
import httpx

@tool
def wikipedia(query: str) -> str:
    url = "https://en.wikipedia.org/w/api.php"
    try:
        response = httpx.get(
            url,
            params={"action": "query", "list": "search", "srsearch": query, "format": "json"},
            headers={"User-Agent": "Telegram-Gaia-Agent/1.0"}
        )
        searches = response.json()["query"]["search"]
        if not searches:
            return "No Wikipedia article found"
        page_id = str(searches[0]["pageid"])
        page = httpx.get(
            url,
            params={"action": "query", "prop": "extracts", "explaintext": True, "exintro": True, "pageids": page_id, "format": "json"},
            headers={"User-Agent": "Telegram-Gaia-Agent/1.0"}
        ).json()
        return page["query"]["pages"][page_id]["extract"]
    except Exception as e:
        return f"Error: {e}"
