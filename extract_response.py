"""Extract and display the generated code from the speed test"""
import json
import urllib.request

def get_response(message):
    data = json.dumps({"message": message, "history": []}).encode('utf-8')
    req = urllib.request.Request(
        "http://localhost:3851/api/chat/stream",
        data=data,
        headers={'Content-Type': 'application/json'}
    )
    
    full_response = ""
    with urllib.request.urlopen(req, timeout=120) as response:
        buffer = ""
        for line in response:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                buffer += line[6:]
                try:
                    event = json.loads(buffer)
                    buffer = ""
                    if event.get("type") == "chunk":
                        full_response += event.get("text", "")
                    elif event.get("type") == "done":
                        break
                except json.JSONDecodeError:
                    continue
    
    return full_response

# Get the response
print("Fetching response...")
response = get_response("Create a simple card with a user profile showing name, email, and a green active badge")
print("\n" + "="*80)
print("GENERATED RESPONSE:")
print("="*80)
print(response)
print("\n" + "="*80)
