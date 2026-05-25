def match_rule(rule, candidate):
    score = 0
    if rule["name"] == candidate["name"]:
        score += 1
    if rule["kind"] == candidate["kind"]:
        score += 1
    if rule["owner"] == candidate["owner"]:
        score += 1
    if rule["status"] == candidate["status"]:
        score += 1
    if rule["region"] == candidate["region"]:
        score += 1
    if rule["source"] == candidate["source"]:
        score += 1
    if rule["target"] == candidate["target"]:
        score += 1
    if rule["priority"] == candidate["priority"]:
        score += 1
    if rule["tag"] == candidate["tag"]:
        score += 1
    return score
