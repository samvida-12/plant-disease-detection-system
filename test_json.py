import json, os

print("Current working dir:", os.getcwd())

path = "disease_info.json"
print("Exists?", os.path.exists(path))

with open(path, "r", encoding="utf-8") as f:
    text = f.read()

print("File size (bytes):", len(text))
print("First 50 chars:", repr(text[:50]))

data = json.loads(text)
print("Loaded OK. Number of entries:", len(data))