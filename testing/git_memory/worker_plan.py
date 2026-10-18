"""Strict outcome check for the declared bounded-worker planning smoke task.

This checks a concrete plan, rather than counting numbers in arbitrary prose.
It is not evidence of implementation correctness or broad product usefulness.
"""
import json


def check(text):
    decoder = json.JSONDecoder()
    for offset, character in enumerate(text):
        if character != '{':
            continue
        try:
            plan, _ = decoder.raw_decode(text[offset:])
        except ValueError:
            continue
        if not isinstance(plan, dict):
            continue
        sizes = plan.get('batch_sizes')
        if (plan.get('item_count') == 70 and not isinstance(plan.get('item_count'), bool)
                and isinstance(sizes, list) and sizes == [32, 32, 6]
                and all(type(n) is int for n in sizes)
                and plan.get('preserves_order') is True
                and isinstance(plan.get('source'), (str, list, dict)) and bool(plan['source'])):
            return True
    return False
