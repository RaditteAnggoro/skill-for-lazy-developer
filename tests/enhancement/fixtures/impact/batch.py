from payment import approve_repayment


def replay(events):
    return [approve_repayment(event, amount) for event, amount in events]
