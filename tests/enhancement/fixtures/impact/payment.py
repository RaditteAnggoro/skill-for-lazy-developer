from ledger import write_posting
from schedule import normalize_amount


def approve_repayment(event, amount):
    return write_posting(event, normalize_amount(amount))
