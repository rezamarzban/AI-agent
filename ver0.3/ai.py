import requests
import json
import time
import os
import importlib
import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer

# ====================== TOOL LOADER ======================
def load_tools():
    tools = {}
    schemas = []
    # Ensure current directory is in path for imports if needed, though usually not required for current dir
    for filename in os.listdir('.'):
        if filename.endswith('_tool.py'):
            module_name = filename[:-3]
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, 'schema'):
                    sch = module.schema
                    tool_name = sch['function']['name']
                    if hasattr(module, tool_name):
                        tools[tool_name] = getattr(module, tool_name)
                        schemas.append(sch)
                        print(f"   Loaded tool: {tool_name}")
            except Exception as e:
                print(f"   Failed to load {filename}: {e}")
    return tools, schemas


# ====================== CONFIG ======================
LLAMA_SERVER_URL = "http://127.0.0.1:8080/v1/chat/completions"
MODEL = "llama-3.1-8b-instruct"
TIMEOUT = 600
MAX_RETRIES = 3
WEB_PORT = 8000

# Load tools automatically
TOOLS, TOOLS_SCHEMAS = load_tools()
print(f"✅ Loaded {len(TOOLS)} tools\n")

# Shared history for the session (simplistic approach for single-user local tool)
HISTORY = [
    {
        "role": "system",
        "content": "You are an expert helpful assistant.\n"
                   "IMPORTANT RULES FOR TOOL USE:\n"
                   "- When the user asks to search multiple items (e.g., 'search web for hydrogen, then for carbon, then for oxygen' or 'search for A, B, and C'),\n"
                   "  you MUST call the search_web tool MULTIPLE TIMES IN PARALLEL in a SINGLE response using separate tool_calls.\n"
                   "  One tool_call for each item. Never call only one and stop.\n"
                   "- For complex problems, you may use tools sequentially across multiple turns if needed.\n"
                   "- After receiving all tool results, provide a complete final answer summarizing everything.\n"
                   "- Always obey these rules exactly."
    }
]


# ====================== STREAMING WITH REALTIME CONNECTION ======================
def stream_model(messages):
    payload = {
        "model": MODEL,
        "messages": messages,
        "tools": TOOLS_SCHEMAS,
        "tool_choice": "auto",
        "stream": True,
        "temperature": 0.7,
        "top_p": 0.95,
        "max_tokens": 4096,
        "presence_penalty": 0.0,
        "frequency_penalty": 0.0
    }

    print("\nConnecting to server...", end="", flush=True)

    accumulated_content = ""
    accumulated_tool_calls = []
    accumulated_function_call = {"name": "", "arguments": ""}
    token_count = 0
    start_time = None

    for attempt in range(MAX_RETRIES):
        try:
            with requests.post(LLAMA_SERVER_URL, json=payload, stream=True, timeout=TIMEOUT) as resp:
                resp.raise_for_status()
                print(" Connected ✓", flush=True)
                print("Assistant: ", end="", flush=True)

                for line in resp.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data: "):
                        continue
                    data = line[6:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue

                    delta = chunk.get("choices", [{}])[0].get("delta", {})

                    if delta.get("content") is not None:
                        token = delta["content"]
                        if start_time is None:
                            start_time = time.time()
                        print(token, end="", flush=True)
                        accumulated_content += token
                        token_count += 1

                    if "tool_calls" in delta:
                        for tc_delta in delta["tool_calls"]:
                            idx = tc_delta.get("index", 0)
                            while len(accumulated_tool_calls) <= idx:
                                accumulated_tool_calls.append({
                                    "id": "", "type": "function", "function": {"name": "", "arguments": ""}
                                })
                            tc = accumulated_tool_calls[idx]
                            if "id" in tc_delta:
                                tc["id"] += tc_delta.get("id", "")
                            if "function" in tc_delta:
                                f = tc_delta["function"]
                                if "name" in f:
                                    tc["function"]["name"] += f.get("name", "")
                                if "arguments" in f:
                                    tc["function"]["arguments"] += f.get("arguments", "")

                    if "function_call" in delta:
                        fc = delta["function_call"]
                        if "name" in fc:
                            accumulated_function_call["name"] += fc.get("name", "")
                        if "arguments" in fc:
                            accumulated_function_call["arguments"] += fc.get("arguments", "")

                break

        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                print(" Failed ✗")
                print(f"   [Connection error: {e}]")
                accumulated_content = f"[Error: {e}]"
                break
            wait = (2 ** attempt) * 1.5
            print(f" Failed (retry {attempt+1}/{MAX_RETRIES} in {wait:.1f}s)", flush=True)
            time.sleep(wait)
            print("Connecting to server...", end="", flush=True)

    if token_count > 3 and start_time is not None:
        elapsed = time.time() - start_time
        speed = token_count / elapsed
        print(f"  ({speed:.1f} tokens/s)", end="")
    print()

    # Stronger cleaning of bad characters
    accumulated_content = accumulated_content.strip()
    accumulated_content = accumulated_content.encode('utf-8', 'ignore').decode('utf-8')

    msg = {"role": "assistant", "content": accumulated_content or None}

    if accumulated_tool_calls:
        clean = []
        for tc in accumulated_tool_calls:
            if tc["function"]["name"]:
                clean.append({
                    "id": tc["id"] or None,
                    "type": "function",
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"]
                    }
                })
        if clean:
            msg["tool_calls"] = clean

    elif accumulated_function_call["name"]:
        msg["function_call"] = accumulated_function_call

    return msg


# ====================== CONVERSATION PROCESSOR ======================
def process_conversation_turn(history):
    """
    Handles the loop of calling the model, checking for tools, 
    executing tools, and calling the model again until a text response is given.
    Returns the final text content.
    """
    step = 0
    max_steps = 20
    final_response = ""

    while step < max_steps:
        step += 1
        assistant_msg = stream_model(history)
        history.append(assistant_msg)

        tool_calls = assistant_msg.get("tool_calls")
        function_call = assistant_msg.get("function_call")

        # If no tools called, we are done
        if not tool_calls and not function_call:
            final_response = assistant_msg.get("content", "")
            break

        print("\n   🔧 Executing tool calls...\n")
        tool_messages = []

        if tool_calls:
            for tc in tool_calls:
                fname = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"])
                except:
                    args = {}

                print(f"   [TOOL CALL] {fname}")
                print(f"   Arguments : {json.dumps(args, indent=4)}")

                result = TOOLS.get(fname)(**args) if fname in TOOLS else {"error": "Unknown tool"}

                print("   [TOOL RESULT]")
                print(json.dumps(result, indent=4))
                print("   ───────────────────────────────\n")

                tool_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", "call_1"),
                    "name": fname,
                    "content": json.dumps(result)
                })

        elif function_call:
            fname = function_call["name"]
            try:
                args = json.loads(function_call["arguments"])
            except:
                args = {}

            print(f"   [TOOL CALL] {fname}")
            print(f"   Arguments : {json.dumps(args, indent=4)}")

            result = TOOLS.get(fname)(**args) if fname in TOOLS else {"error": "Unknown tool"}

            print("   [TOOL RESULT]")
            print(json.dumps(result, indent=4))
            print("   ───────────────────────────────\n")

            tool_messages.append({
                "role": "tool",
                "name": fname,
                "content": json.dumps(result)
            })

        history.extend(tool_messages)
        print("   Results processed — continuing if needed...\n")
    
    print("-" * 70)
    return final_response


# ====================== HTTP SERVER ======================
class ChatRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = 'index.html'
        return SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        if self.path == '/chat':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                user_message = data.get('prompt', '').strip()
                
                if not user_message:
                    self.send_response(400)
                    self.end_headers()
                    return

                print(f"\n[WEB REQUEST] User: {user_message}")
                HISTORY.append({"role": "user", "content": user_message})
                
                # Run the conversation loop
                response_text = process_conversation_turn(HISTORY)
                
                # Send response back to web client
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                
                response_data = {"response": response_text}
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
                
            except Exception as e:
                print(f"Error handling web request: {e}")
                self.send_response(500)
                self.end_headers()
        else:
            self.send_error(404)

def run_server():
    server_address = ('', WEB_PORT)
    httpd = HTTPServer(server_address, ChatRequestHandler)
    print(f"🌐 Web interface running at http://localhost:{WEB_PORT}")
    httpd.serve_forever()


# ====================== CHAT LOOP ======================
def chat():
    # Start web server in a separate thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    print("Assistant ready — type 'exit' to quit.\n")

    while True:
        try:
            user = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break
        
        if user.lower() in ("exit", "quit", "bye"):
            print("Goodbye!")
            break
        
        if not user:
            continue

        HISTORY.append({"role": "user", "content": user})
        process_conversation_turn(HISTORY)


if __name__ == "__main__":
    chat()
