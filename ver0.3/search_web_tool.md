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

### Other similar services:

Switching search providers is a smart move—different APIs offer varying "flavors" of data. Some are better for raw links, while others (like Tavily) are specifically tuned to give AI agents clean, readable context.

Here are the top alternatives to SerpAPI, along with the configuration details you'll need to swap into your `search_web_tool.py`.

---

## 1. Tavily (The "AI-First" Choice)

Tavily is built specifically for LLMs. Instead of returning ads and SEO fluff, it returns clean text snippets and can even provide a summary.

* **API Key:** [Get it here]()
* **Base URL:** `https://api.tavily.com/search`
* **Configuration:**

```python
# In search_web_tool.py
payload = {
    "api_key": "YOUR_TAVILY_KEY",
    "query": query,
    "search_depth": "smart", # or "basic"
    "max_results": 5
}
response = requests.post("https://api.tavily.com/search", json=payload)

```

---

## 2. Google Custom Search (The "Official" Way)

If you want to go straight to the source without a middleman like SerpAPI, you can use Google's JSON API. It's a bit more "corporate" to set up.

* **API Key:** [Google Cloud Console]()
* **Search Engine ID (CX):** You must create a "Programmable Search Engine" at [cse.google.com]().
* **Base URL:** `https://www.googleapis.com/customsearch/v1`
* **Configuration:**

```python
# In search_web_tool.py
params = {
    "key": "YOUR_GOOGLE_API_KEY",
    "cx": "YOUR_SEARCH_ENGINE_ID",
    "q": query
}
response = requests.get("https://www.googleapis.com/customsearch/v1", params=params)
# Results are in response.json().get("items", [])

```

---

## 3. Bing Search (The "Azure" Powerhouse)

Microsoft’s API is incredibly fast and often provides better structured data for news and images than Google’s.

* **API Key:** [Azure Portal]() (Search for "Bing Search Services")
* **Base URL:** `https://api.bing.microsoft.com/v7.0/search`
* **Configuration:**

```python
# In search_web_tool.py
headers = {"Ocp-Apim-Subscription-Key": "YOUR_BING_KEY"}
params = {"q": query, "textDecorations": True, "textFormat": "HTML"}
response = requests.get("https://api.bing.microsoft.com/v7.0/search", headers=headers, params=params)

```

---

## 4. DuckDuckGo (The "Free & Private" Route)

DuckDuckGo doesn't have an official "API" for individual developers in the same way, but the Python community has built a fantastic wrapper that is **free** and requires **no API key**.

* **Library:** `pip install duckduckgo_search`
* **Configuration:**

```python
from duckduckgo_search import DDGS

def search_web(query):
    with DDGS() as ddgs:
        results = [r for r in ddgs.text(query, max_results=5)]
    return {"results": results}

```

---

## Comparison Table for AI Tooling

| Service | Best For | Cost | Effort to Set Up |
| --- | --- | --- | --- |
| **SerpAPI** | Google parity | Mid-range | Low |
| **Tavily** | **LLM Context** | Generous Free Tier | Very Low |
| **Google CSE** | Reliability | Free (up to 100/day) | High |
| **Bing** | News/Speed | Paid (Azure) | Medium |
| **DuckDuckGo** | Quick Prototyping | **$0 (Free)** | Lowest |

---

### Pro-Tip: The "Unified" Config Structure

To make your `search_web_tool.py` easier to manage, I recommend using a `.env` file for your keys and a simple dictionary to switch between providers.

> **Warning:** Be careful with the "Search Depth" or "Max Results" parameters. LLMs have a context window; if you return 50 search results, you might crash your local Llama model or make it very slow! Stick to 3–5 high-quality results.

## Full code for each service:

Since here is building a tool-calling agent, each of these scripts is designed to replace current `search_web_tool.py`. I have kept the `schema` consistent so `ai.py` loader won't need any changes.

---

### 1. Tavily (Best for AI Agents)

Tavily is specifically designed to provide clean, LLM-ready content. It avoids ads and returns concise snippets.

**Setup:** Set `TAVILY_API_KEY` in your environment variables.

```python
import os
import requests

def search_web(query):
    """Search using Tavily (AI-optimized search)."""
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return {"error": "Missing TAVILY_API_KEY"}

    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "max_results": 5
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data.get("results", []):
            results.append({
                "title": item.get("title"),
                "link": item.get("url"),
                "snippet": item.get("content")
            })
        return {"results": results}
    except Exception as e:
        return {"error": str(e)}

schema = {
    "type": "function",
    "function": {
        "name": "search_web",
        "description": "Search the web for current information using Tavily.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query."}
            },
            "required": ["query"]
        }
    }
}

```

---

### 2. Google Custom Search (Official API)

This is the standard Google way. It requires a project in Google Cloud and a search engine ID.

**Setup:** Set `GOOGLE_API_KEY` and `GOOGLE_CSE_ID` in your environment variables.

```python
import os
import requests

def search_web(query):
    """Search using Google Custom Search API."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    cse_id = os.environ.get("GOOGLE_CSE_ID")
    
    if not api_key or not cse_id:
        return {"error": "Missing GOOGLE_API_KEY or GOOGLE_CSE_ID"}

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cse_id,
        "q": query,
        "num": 5
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data.get("items", []):
            results.append({
                "title": item.get("title"),
                "link": item.get("link"),
                "snippet": item.get("snippet")
            })
        return {"results": results}
    except Exception as e:
        return {"error": str(e)}

schema = {
    "type": "function",
    "function": {
        "name": "search_web",
        "description": "Search Google for information.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query."}
            },
            "required": ["query"]
        }
    }
}

```

---

### 3. Bing Search (Azure)

Microsoft's API is very robust and often faster for global news.

**Setup:** Set `BING_API_KEY` in your environment variables.

```python
import os
import requests

def search_web(query):
    """Search using Bing Search API."""
    api_key = os.environ.get("BING_API_KEY")
    if not api_key:
        return {"error": "Missing BING_API_KEY"}

    url = "https://api.bing.microsoft.com/v7.0/search"
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    params = {"q": query, "count": 5}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data.get("webPages", {}).get("value", []):
            results.append({
                "title": item.get("name"),
                "link": item.get("url"),
                "snippet": item.get("snippet")
            })
        return {"results": results}
    except Exception as e:
        return {"error": str(e)}

schema = {
    "type": "function",
    "function": {
        "name": "search_web",
        "description": "Search the web using Microsoft Bing.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query."}
            },
            "required": ["query"]
        }
    }
}

```

---

### 4. DuckDuckGo (Free / No Key)

This is the "easiest" one because it doesn't require any registration. It uses the `duckduckgo_search` library.

**Setup:** Run `pip install duckduckgo_search`.

```python
from duckduckgo_search import DDGS

def search_web(query):
    """Search the web for free using DuckDuckGo."""
    try:
        results = []
        with DDGS() as ddgs:
            # We convert the generator to a list and limit it
            ddgs_gen = ddgs.text(query, max_results=5)
            for r in ddgs_gen:
                results.append({
                    "title": r.get("title"),
                    "link": r.get("href"),
                    "snippet": r.get("body")
                })
        
        if not results:
            return {"message": "No results found."}
        return {"results": results}
    except Exception as e:
        return {"error": str(e)}

schema = {
    "type": "function",
    "function": {
        "name": "search_web",
        "description": "Search the web privately and for free using DuckDuckGo.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query."}
            },
            "required": ["query"]
        }
    }
}

```

---

### Which one should you choose?

* **For the best results with an LLM:** Go with **Tavily**. It filters out the "junk" that usually confuses local models.
* **For zero cost and no hassle:** Go with **DuckDuckGo**. It just works.
* **For industrial reliability:** Go with **Google** or **Bing**.

