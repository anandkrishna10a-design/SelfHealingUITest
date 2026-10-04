from healing.ollama_client import ask_ollama


def clean_locator(response):

    locator = response.strip()

    locator = locator.replace("```css", "")
    locator = locator.replace("```html", "")
    locator = locator.replace("```", "")

    return locator.strip()


def analyze_locator_failure(old_locator, page_elements):

    prompt = f"""
You are repairing a broken Playwright UI test locator.

FAILED LOCATOR:
{old_locator}

The failed locator DOES NOT EXIST anymore.
NEVER return the failed locator.

CURRENT LIVE BUTTONS:
{page_elements}

The failed locator was used for a CLICK action.

Your job is to find the CURRENT button that has the same
semantic purpose as the failed locator.

SEMANTIC RULES:

- The old locator contains the word "login".
- "Login", "Log in", and "Sign in" represent the same action.
- "Sign Up" means account registration and is NOT login.
- Prefer the visible text of the button when determining purpose.
- Only choose an ID that exists in CURRENT LIVE BUTTONS.
- NEVER return {old_locator}.

Return exactly ONE CSS ID locator.

Example:
#signin-btn

Return ONLY the locator.
Do not explain.
Do not use Markdown.
"""

    response = ask_ollama(prompt)

    return clean_locator(response)


if __name__ == "__main__":

    old_locator = "#login-btn"

    sample_elements = """
{'tag': 'button', 'id': 'signin-btn', 'text': 'Login'}
{'tag': 'button', 'id': 'signup-btn', 'text': 'Sign Up'}
"""

    print("Testing improved failure analyzer...\n")

    suggestion = analyze_locator_failure(
        old_locator,
        sample_elements
    )

    print("Suggested replacement:")
    print(suggestion)