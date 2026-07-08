"""
===========================================================
TribeIQ Scoring Library
===========================================================

Returns RAW scores (0-100)

No weights are applied here.

Recommendation Engine applies weights.
"""


# ===========================================================
# Generic Distribution Match
# ===========================================================

def distribution_match(distribution, targets):

    if not targets:
        return 100

    if "All" in targets:
        return 100

    score = 0

    for target in targets:

        score += distribution.get(target, 0)

    return min(round(score, 2), 100)


# ===========================================================
# Interest Match
# ===========================================================

def interest_match(property_interests, event_interests):

    if not event_interests:
        return 100

    if "All" in event_interests:
        return 100

    total = sum(property_interests.values())

    if total == 0:
        return 0

    overlap = 0

    for interest in event_interests:

        overlap += property_interests.get(

            interest.title(),

            0

        )

    return min(

        round((overlap / total) * 100, 2),

        100

    )


# ===========================================================
# Occupation
# ===========================================================

def occupation_score(profile, event):

    score = distribution_match(

        profile["Occupation Distribution"],

        event["Target Occupation"]

    )

    return score, f"{score:.1f}% occupation match"


# ===========================================================
# Age
# ===========================================================

def age_score(profile, event):

    score = distribution_match(

        profile["Age Distribution"],

        event["Target Age Band"]

    )

    return score, f"{score:.1f}% age match"


# ===========================================================
# Tenure
# ===========================================================

def tenure_score(profile, event):

    score = distribution_match(

        profile["Tenure Distribution"],

        event["Target Tenure Band"]

    )

    return score, f"{score:.1f}% tenure match"


# ===========================================================
# Region
# ===========================================================

def region_score(profile, event):

    if "Target Region" not in event:

        return 100, "Region not considered"

    score = distribution_match(

        profile["Region Distribution"],

        event["Target Region"]

    )

    return score, f"{score:.1f}% region match"


# ===========================================================
# Interest
# ===========================================================

def interest_score(profile, event):

    score = interest_match(

        profile["Top Interests"],

        event["Target Interests"]

    )

    return score, f"{score:.1f}% interest match"


# ===========================================================
# Community Size
# ===========================================================

def community_size_score(profile, event):

    target = event["Community Size"]

    if target == "All":

        return 100, "All community sizes"

    if target == profile["Community Size"]:

        return 100, "Community size matches"

    return 0, "Community size mismatch"


# ===========================================================
# Community Stage
# ===========================================================

def community_stage_score(profile, event):

    target = event.get(

        "Ideal Community Stage",

        "All"

    )

    if target == "All":

        return 100, "All stages"

    if target == profile["Community Stage"]:

        return 100, "Community stage matches"

    return 0, "Community stage mismatch"


# ===========================================================
# Registry
# ===========================================================

SCORERS = {

    "occupation": occupation_score,

    "age": age_score,

    "tenure": tenure_score,

    "interest": interest_score,

    "community_size": community_size_score,

    "community_stage": community_stage_score

}