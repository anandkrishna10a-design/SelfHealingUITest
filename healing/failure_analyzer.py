
from healing.ollama_client import ask_ollama
import ast


def clean_locator(response):
    """Extract a CSS ID locator from the model response."""

    if not response:
        return ""

    locator = response.strip()
    locator = locator.replace("```css", "")
    locator = locator.replace("```html", "")
    locator = locator.replace("```", "")

    lines = [
        line.strip()
        for line in locator.splitlines()
        if line.strip()
    ]

    if not lines:
        return ""

    locator = lines[0]

    for prefix in ("Locator:", "CSS:", "Answer:"):
        if locator.lower().startswith(prefix.lower()):
            locator = locator[len(prefix):].strip()

    return locator.strip().strip("`'\"")


def analyze_locator_failure(old_locator, page_elements):
    """
    Ask Ollama to suggest a replacement locator.

    If Ollama returns an empty response, NONE, or the original
    broken locator, use a conservative fallback for login buttons.
    """

    failed_lower = old_locator.lower()

    if any(term in failed_lower for term in ("search", "query")):
        purpose = (
            "PRODUCT SEARCH INPUT. Choose the input used to search "
            "products. Do not choose a button."
        )

    elif "password" in failed_lower:
        purpose = (
            "PASSWORD INPUT. Choose the password input. "
            "Do not choose a button."
        )

    elif any(
        term in failed_lower
        for term in ("username", "user-name", "user_name")
    ):
        purpose = (
            "USERNAME INPUT. Choose the username input. "
            "Do not choose a button."
        )

    elif "login" in failed_lower or "sign-in" in failed_lower:
        purpose = (
            "LOGIN BUTTON. Choose the button whose text is Login "
            "or Sign In. Never choose Sign Up or Register."
        )

    else:
        purpose = (
            "Infer the intended element from the failed locator "
            "and the live candidate information."
        )

    prompt = f"""
You repair broken Playwright CSS ID locators.

Failed locator:
{old_locator}

Intended purpose:
{purpose}

Live elements:
{page_elements}

Rules:
1. Choose only an element listed in the live elements.
2. Copy its ID exactly and return it as a CSS ID locator.
3. Never invent an ID.
4. Never return the failed locator.
5. Match the element's tag and semantic purpose.
6. For login, choose Login or Sign In, never Sign Up.
7. If no suitable element exists, return NONE.
8. Return only one locator, without explanations or Markdown.

Example:
Failed locator: #login-btn
Intended purpose: LOGIN BUTTON

Live elements:
{{'tag': 'button', 'id': 'sign-in-btn', 'text': 'Login'}}
{{'tag': 'button', 'id': 'signup-btn', 'text': 'Sign Up'}}

Answer:
#sign-in-btn

Now solve the actual case using the live elements above.
"""

    response = ask_ollama(prompt)
    suggestion = clean_locator(response)

    # Accept a model suggestion only if it differs from the
    # failed locator and is not an explicit refusal.
    if (
        suggestion
        and suggestion.upper() != "NONE"
        and suggestion.lower() != old_locator.lower()
    ):
        return suggestion

    # Conservative fallback for login buttons.
    # Only select an exact Login or Sign In button from the
    # supplied live candidates.
    if "login" in failed_lower or "sign-in" in failed_lower:
        for line in page_elements.splitlines():
            try:
                candidate = ast.literal_eval(line.strip())
            except (ValueError, SyntaxError):
                continue

            if not isinstance(candidate, dict):
                continue

            candidate_id = candidate.get("id", "")
            candidate_text = (
                candidate.get("text", "").strip().lower()
            )

            if (
                candidate.get("tag") == "button"
                and candidate_id
                and candidate_text in ("login", "sign in")
            ):
                return f"#{candidate_id}"

    return ""


if __name__ == "__main__":
    candidates = """
{'tag': 'button', 'id': 'sign-in-btn', 'text': 'Login'}
{'tag': 'button', 'id': 'signup-btn', 'text': 'Sign Up'}
"""

    print("Testing login-button healing with Ollama...\n")

    suggestion = analyze_locator_failure(
        "#login-btn",
        candidates,
    )

    print("Suggested replacement:", repr(suggestion))
