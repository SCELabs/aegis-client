from __future__ import annotations


def prompt_email(*, input_fn=input, print_fn=print) -> str:
    while True:
        email = input_fn("Email: ").strip()
        if "@" in email and "." in email:
            return email
        print_fn("Please enter a valid email address.")
