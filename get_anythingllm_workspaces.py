import requests
import json

API_KEY = "R212Y2R-Z494M7R-J8Q01DP-JY4DV4N"

BASE_URL = "http://localhost:3001/api/v1"

headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

response = requests.get(f"{BASE_URL}/workspaces", headers=headers)

if response.status_code == 200:
    workspaces = response.json()

    json.dump(workspaces, open("workspaces.json", "w"), ensure_ascii=False, indent=2)
    print("Workspaces:")
    for workspace in workspaces.get("workspaces", []):
        print(f"ID: {workspace.get('id')}")
        print(f"Name: {workspace.get('name')}")
        print(f"Slug: {workspace.get('slug')}")
        print(f"Created: {workspace.get('createdAt')}")
        print(f"Chat Provider: {workspace.get('chatProvider')}")
        print(f"Chat Model: {workspace.get('chatModel')}")
        print("-" * 50)
else:
    print("Hata:", response.status_code, response.text)
