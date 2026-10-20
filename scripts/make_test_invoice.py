"""Create one paid test invoice in the Stripe test account, so the dashboard gets a new day.

Run by .github/workflows/test-invoice.yml in the stripe-test environment. Reads STRIPE_TEST_KEY
and refuses anything that is not a test-mode secret key. Uses one test customer, found by email
or created on the first run, and Stripe's test card. Test mode only.

Run from the repo root: STRIPE_TEST_KEY=sk_test_... python3 scripts/make_test_invoice.py
"""

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request

KEY = os.environ.get("STRIPE_TEST_KEY", "")
if not KEY.startswith("sk_test_"):
    raise SystemExit("STRIPE_TEST_KEY must be a test-mode secret key (sk_test_...). Nothing was created.")

API = "https://api.stripe.com/v1"
EMAIL = "dashboard.test@example.com"  # reserved for documentation, never a real mailbox
AMOUNT = 1500  # 15.00 USD, the same price as the test plans
DESCRIPTION = "Dashboard test invoice"


def call(method: str, path: str, params: dict | None = None) -> dict:
    data = urllib.parse.urlencode(params).encode() if params is not None else None
    req = urllib.request.Request(API + path, data=data, method=method)
    token = base64.b64encode((KEY + ":").encode()).decode()
    req.add_header("Authorization", f"Basic {token}")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as err:
        raise SystemExit(f"{method} {path} failed: {err.read().decode()}")


def find_or_create_customer() -> str:
    query = urllib.parse.urlencode({"email": EMAIL, "limit": 1})
    found = call("GET", f"/customers?{query}")["data"]
    if found:
        return found[0]["id"]
    customer = call("POST", "/customers", {"email": EMAIL, "name": "Dashboard test subscriber"})["id"]
    card = call("POST", "/payment_methods/pm_card_visa/attach", {"customer": customer})["id"]
    call("POST", f"/customers/{customer}", {"invoice_settings[default_payment_method]": card})
    return customer


def main() -> None:
    customer = find_or_create_customer()
    call("POST", "/invoiceitems", {"customer": customer, "amount": AMOUNT, "currency": "usd", "description": DESCRIPTION})
    invoice = call("POST", "/invoices", {"customer": customer, "auto_advance": "false"})["id"]
    result = call("POST", f"/invoices/{invoice}/finalize", {})
    # Finalizing charges the default card, so the invoice can already be paid. Paying it again fails.
    if result["status"] != "paid":
        result = call("POST", f"/invoices/{invoice}/pay", {})
    print(result["id"], result["status"], result["amount_paid"])


if __name__ == "__main__":
    main()
