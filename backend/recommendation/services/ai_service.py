import requests

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

def generate_reason(prompt):
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": "tinyllama:latest",
                "prompt": prompt,
                "stream": False
            },
            timeout=20
        )
        return response.json().get("response", "").strip()
    except Exception as e:
        print("AI ERROR:", e)
        return None


def build_prompt(data):
    return f"""
You are a college advisor.

Student:
- Cutoff: {data['cutoff']}
- Budget: {data['budget']}

College:
- Name: {data['college']}
- Course: {data['course']}
- Fees: {data['fees']}
- Placement: {data['placement']}%
- Distance: {data['distance']} km

Give a SHORT reason (max 2 lines) why this college is suitable.
Focus on placement, affordability, and distance.
"""