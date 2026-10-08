import random


def generate_item_order(document_ids: list[int], model_names: list[str], seed=None) -> list[list]:
    """Build a reviewer's fixed presentation order as two balanced blocks.

    The documents are shuffled and split into halves S1/S2. Block 1 pairs S1
    with one model and S2 with the other; block 2 mirrors the assignment.
    Each block is shuffled independently. Guarantees: every document appears
    exactly once per block (so its two extractions are never adjacent), and
    each model contributes half the items of each block.
    """
    if len(model_names) != 2:
        raise ValueError("Exactly two models are required")

    rng = random.Random(seed)

    docs = list(document_ids)
    rng.shuffle(docs)
    half = len(docs) // 2
    s1, s2 = docs[:half], docs[half:]

    models = list(model_names)
    rng.shuffle(models)  # which model leads block 1 is randomized per reviewer
    model_a, model_b = models

    block1 = [[d, model_a] for d in s1] + [[d, model_b] for d in s2]
    block2 = [[d, model_b] for d in s1] + [[d, model_a] for d in s2]
    rng.shuffle(block1)
    rng.shuffle(block2)

    # Block structure prevents same-document adjacency within blocks, but not
    # across the seam: fix by swapping block 2's first item if it repeats the
    # document that ends block 1.
    if len(block2) > 1 and block2[0][0] == block1[-1][0]:
        j = rng.randrange(1, len(block2))
        block2[0], block2[j] = block2[j], block2[0]

    return block1 + block2
