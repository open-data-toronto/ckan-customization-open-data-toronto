import json

f1 = 'prepare_intake.json'
f2 = 'prepare_intake_original.json'


with open(f1, "r") as f:
    prior = json.load(f)["result"]
    prior_new = prior["new"]
    prior_existing = prior["existing"]

with open(f2, "r") as f:
    refactor = json.load(f)["result"]
    refactor_new = refactor["new"]
    refactor_existing = refactor["existing"]

def dict_eq(d1, d2):
    try:
        assert set(d1.keys()) == set(d2.keys())
        for k, d1_value in d1.items():
            d2_value = d2[k]
            if isinstance(d1_value, list):
                assert all(d1v in d2_value for d1v in d1_value)
            else:
                assert d1_value == d2_value
    except AssertionError:
        breakpoint()
        raise
dict_eq(refactor_new, prior_new)
dict_eq(refactor_existing, prior_existing)
