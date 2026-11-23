import re


EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]*\w")


def find_emails(text: str) -> list[str]:
    return EMAIL_PATTERN.findall(text)
