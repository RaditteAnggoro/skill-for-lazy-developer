from auth import may_approve
from payment import approve_repayment


def approve_request(actor, event, amount):
    if not may_approve(actor):
        return 'denied'
    return approve_repayment(event, amount)
