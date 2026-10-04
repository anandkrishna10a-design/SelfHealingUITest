import json
import urllib.request
import urllib.error


OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5-coder:1.5b"


def ask_ollama(prompt):

    data = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }

    request_data = json.dumps(data).encode("utf-8")

    request = urllib.request.Request(
        OLLAMA_URL,
        data=request_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:

            result = json.loads(
                response.read().decode("utf-8")
            )

            return result["response"].strip()

    except urllib.error.URLError as error:

        return f"ERROR: Could not connect to Ollama: {error}"


if __name__ == "__main__":

    test_prompt = """
You are helping with Playwright UI test automation.

A Playwright test used this locator:

#login-btn

The webpage now contains:

<button id="signin-btn">Login</button>

What is the best replacement CSS locator?

Return ONLY the locator.
"""

    print("Sending test request to Ollama...\n")

    answer = ask_ollama(test_prompt)

    print("Ollama response:")
    print(answer)