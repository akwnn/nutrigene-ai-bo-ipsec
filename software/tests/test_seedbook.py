from __future__ import annotations

import torch

from boec.seedbook import IndexedGaussianNoise, derive_seed


def test_seed_labels_are_stable_independent_and_order_free():
    a = derive_seed(7, "opening", "family", 3)
    assert a == derive_seed(7, "opening", "family", 3)
    assert a != derive_seed(7, "noise", "family", 3)
    assert derive_seed(7, "noise", "family", 3) == derive_seed(
        7, "noise", "family", 3
    )


def test_indexed_noise_does_not_depend_on_chunking():
    source = IndexedGaussianNoise(11, sigma_rel=0.1, sigma_add=0.01)
    f = torch.tensor([[0.2], [0.5], [0.9]], dtype=torch.double)
    together = source.observe(torch.arange(3), f)
    split = tuple(
        torch.cat(
            [
                source.observe(torch.arange(2), f[:2])[i],
                source.observe(torch.arange(2, 3), f[2:])[i],
            ]
        )
        for i in range(2)
    )
    assert all(torch.equal(a, b) for a, b in zip(together, split))


def test_draw_is_the_public_name_for_indexed_observation_noise():
    source = IndexedGaussianNoise(11, sigma_rel=0.1, sigma_add=0.01)
    indices = torch.arange(2)
    latent = torch.tensor([[0.2], [0.5]], dtype=torch.double)
    drawn = source.draw(indices, latent)
    observed = source.observe(indices, latent)
    assert all(torch.equal(a, b) for a, b in zip(drawn, observed))
