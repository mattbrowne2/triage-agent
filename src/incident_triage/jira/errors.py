class JiraError(Exception):
    pass


class TicketContainsPersonalDataError(JiraError):
    def __init__(self, email_count: int) -> None:
        super().__init__(
            f"Ticket rejected: it contains {email_count} customer email addresses. "
            "Remove customer personal data from the summary and description, then file it again."
        )
