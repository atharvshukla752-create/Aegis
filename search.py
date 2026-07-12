from ddgs import DDGS

def web_search(query, max_results=3):
    """Search the web and return results"""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return "No results found."

        output = f"Web search results for: '{query}'\n\n"
        for i, r in enumerate(results, 1):
            output += f"{i}. {r['title']}\n"
            output += f"   {r['body']}\n"
            output += f"   Source: {r['href']}\n\n"

        return output

    except Exception as e:
        return f"Search failed: {str(e)}"


def should_search(user_input):
    """Detect if the user wants a web search"""
    triggers = [
        "search", "look up", "find", "google", "what is",
        "who is", "latest", "news", "current", "today",
        "weather", "price", "when is", "where is"
    ]
    return any(trigger in user_input.lower() for trigger in triggers)