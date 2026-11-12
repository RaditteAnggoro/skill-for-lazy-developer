from statements import INSERT_POSTING, SELECT_POSTINGS


def write_posting(event, amount):
    return INSERT_POSTING, (event, amount)


def read_postings(day):
    return SELECT_POSTINGS, (day,)
