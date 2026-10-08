from collections import Counter

import pytest

from randomization import generate_item_order

DOCS = list(range(1, 31))
MODELS = ["gemma4:e2b", "gpt-5.4-nano"]


def test_total_length_and_uniqueness():
    order = generate_item_order(DOCS, MODELS, seed=42)
    assert len(order) == 60
    assert len({(d, m) for d, m in order}) == 60  # every (doc, model) pair exactly once


def test_each_document_once_per_block():
    order = generate_item_order(DOCS, MODELS, seed=42)
    block1, block2 = order[:30], order[30:]
    assert sorted(d for d, _ in block1) == DOCS
    assert sorted(d for d, _ in block2) == DOCS


def test_model_split_is_balanced_within_each_block():
    order = generate_item_order(DOCS, MODELS, seed=42)
    for block in (order[:30], order[30:]):
        counts = Counter(m for _, m in block)
        assert counts[MODELS[0]] == 15
        assert counts[MODELS[1]] == 15


def test_block2_mirrors_block1_model_assignment():
    order = generate_item_order(DOCS, MODELS, seed=42)
    block1 = {d: m for d, m in order[:30]}
    block2 = {d: m for d, m in order[30:]}
    for doc in DOCS:
        assert block1[doc] != block2[doc]


def test_same_document_never_adjacent():
    for seed in range(20):
        order = generate_item_order(DOCS, MODELS, seed=seed)
        for i in range(len(order) - 1):
            assert order[i][0] != order[i + 1][0]


def test_deterministic_given_seed():
    assert generate_item_order(DOCS, MODELS, seed=7) == generate_item_order(DOCS, MODELS, seed=7)


def test_different_seeds_differ():
    assert generate_item_order(DOCS, MODELS, seed=1) != generate_item_order(DOCS, MODELS, seed=2)


def test_leading_model_varies_across_seeds():
    leaders = {generate_item_order(DOCS, MODELS, seed=s)[0][1] for s in range(30)}
    assert leaders == set(MODELS)  # both models get to lead block 1


def test_requires_exactly_two_models():
    with pytest.raises(ValueError):
        generate_item_order(DOCS, ["only-one"], seed=0)
