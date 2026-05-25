MATCH_FIELDS = (
    "name",
    "kind",
    "owner",
    "status",
    "region",
    "source",
    "target",
    "priority",
    "tag",
)


def match_rule(rule, candidate):
    return sum(1 for field in MATCH_FIELDS if rule[field] == candidate[field])
