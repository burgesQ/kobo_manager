"""Tiny stdlib prompts for the wizards (tests monkeypatch ``builtins.input``)."""

from __future__ import annotations

_YES = {"y", "yes", "o", "oui"}
_NO = {"n", "no", "non"}


def ask_yes_no(question: str, default: bool) -> bool:
    hint = "Y/n" if default else "y/N"
    while True:
        answer = input(f"{question} [{hint}] ").strip().lower()
        if not answer:
            return default
        if answer in _YES:
            return True
        if answer in _NO:
            return False


def ask_text(question: str, default: str) -> str:
    suffix = f" [{default}]" if default else ""
    return input(f"{question}{suffix}: ").strip() or default
