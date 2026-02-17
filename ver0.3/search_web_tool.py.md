Code for `search_web_tool.py`:

This version uses **SerpAPI** (a popular Google Search API wrapper) to perform real searches. You will need to get a free API key from [serpapi.com]() and set it as an environment variable named `SERPAPI_KEY` before running your main script.

### `search_web_tool.py`

```python
import os
import requests

def search_web(query):
    """
    Search the web for information using SerpAPI.
    
    Requires 'SERPAPI_KEY' environment variable to be set.
    """
    api_key = os.environ.get("SERPAPI_KEY")
    
    if not api_key:
        return {
            "error": "Missing API Key. Please set the SERPAPI_KEY environment variable."
        }

    url = "https://serpapi.com/search"
    params = {
        "q": query,
        "api_key": api_key,
        "engine": "google"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Parse organic results
        results = []
        if "organic_results" in data:
            for item in data["organic_results"][:5]:  # Limit to top 5 results
                results.append({
                    "title": item.get("title"),
                    "link": item.get("link"),
                    "snippet": item.get("snippet")
                })
        
        # Check for knowledge graph (often contains quick answers)
        if "knowledge_graph" in data:
            kg = data["knowledge_graph"]
            results.insert(0, {
                "title": kg.get("title", "Knowledge Graph"),
                "snippet": kg.get("description", "No description available.")
            })

        if not results:
            return {"message": f"No results found for '{query}'"}

        return {"results": results}

    except requests.exceptions.RequestException as e:
        return {"error": f"Search request failed: {str(e)}"}


# Tool Schema
schema = {
    "type": "function",
    "function": {
        "name": "search_web",
        "description": "Search the web for current information, news, or facts.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query."
                }
            },
            "required": ["query"]
        }
    }
}

```

### How to use this:

1. **Install requests** if you haven't already:
```bash
pip install requests

```


2. **Set your API Key** in your terminal before running `main.py`:
* **Windows (Command Prompt):** `set SERPAPI_KEY=your_api_key_here`
* **Windows (PowerShell):** `$env:SERPAPI_KEY="your_api_key_here"`
* **Mac/Linux:** `export SERPAPI_KEY=your_api_key_here`
