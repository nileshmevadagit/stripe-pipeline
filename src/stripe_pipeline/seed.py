"""Create test-mode customers that have emails, so joins by customer_key work.

The Stripe CLI trigger creates customers with no email. This script adds the missing
ones. It is safe to rerun: a customer whose email already exists is skipped.

Run from the repo root: uv run python -m stripe_pipeline.seed --count 5
"""

from __future__ import annotations

import argparse
import os

import httpx

from stripe_pipeline.config import STRIPE_API_URL

EMAIL_DOMAIN = "example.com"  # reserved for documentation, never a real mailbox


def test_key() -> str:
    key = os.environ.get("STRIPE_TEST_KEY", "")
    if not key.startswith(("sk_test_", "rk_test_")):
        raise SystemExit("STRIPE_TEST_KEY must be a test-mode key (sk_test_ or rk_test_)")
    return key


def existing_emails(client: httpx.Client) -> set[str]:
    emails: set[str] = set()
    response = client.get("/customers", params={"limit": 100})
    response.raise_for_status()
    for customer in response.json()["data"]:
        if customer.get("email"):
            emails.add(customer["email"].lower())
    return emails


def seed(count: int) -> None:
    headers = {"Authorization": f"Bearer {test_key()}"}
    with httpx.Client(base_url=STRIPE_API_URL, headers=headers, timeout=30) as client:
        have = existing_emails(client)
        created = 0
        for number in range(1, count + 1):
            email = f"seed-customer-{number}@{EMAIL_DOMAIN}"
            if email in have:
                continue
            response = client.post(
                "/customers",
                data={"email": email, "name": f"Seed Customer {number}", "address[country]": "US"},
            )
            response.raise_for_status()
            created += 1
    print(f"created {created} customers, {count - created} already present")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--count", type=int, default=5, help="how many seed customers should exist")
    args = parser.parse_args()
    seed(args.count)


if __name__ == "__main__":
    main()
