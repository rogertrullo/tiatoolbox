"""Unit test package for Unet."""

from pathlib import Path
from typing import Callable

import numpy as np
import pytest
import torch

from tiatoolbox.models.architecture import fetch_pretrained_weights
from tiatoolbox.models.architecture.unet import UNetModel
from tiatoolbox.utils.misc import select_device
from tiatoolbox.wsicore.wsireader import WSIReader

ON_GPU = False

# Test pretrained Model =============================


def test_functional_unet(remote_sample: Callable) -> None:
    """Test for unet."""
    # convert to pathlib Path to prevent wsireader complaint
    mini_wsi_svs = Path(remote_sample("wsi2_4k_4k_svs"))

    pretrained_weights = fetch_pretrained_weights("fcn-tissue_mask")

    reader = WSIReader.open(mini_wsi_svs)
    with pytest.raises(ValueError, match=r".*Unknown encoder*"):
        _ = UNetModel(3, 2, encoder="resnet101", decoder_block=[3])

    with pytest.raises(ValueError, match=r".*Unknown type of skip connection*"):
        _ = UNetModel(3, 2, encoder="unet", skip_type="attention")

    # test creation
    _ = UNetModel(5, 5, encoder="resnet50")
    _ = UNetModel(3, 2, encoder="resnet50")
    _ = UNetModel(3, 2, encoder="unet")

    # test inference
    read_kwargs = {"resolution": 2.0, "units": "mpp", "coord_space": "resolution"}
    batch = np.array(
        [
            reader.read_bounds([0, 0, 1024, 1024], **read_kwargs),
            reader.read_bounds([1024, 1024, 2048, 2048], **read_kwargs),
        ],
    )
    batch = torch.from_numpy(batch)

    model = UNetModel(3, 2, encoder="resnet50", decoder_block=[3])
    pretrained = torch.load(pretrained_weights, map_location="cpu")
    model.load_state_dict(pretrained)
    output = model.infer_batch(model, batch, device=select_device(on_gpu=ON_GPU))
    _ = output[0]

    # run untrained network to test for architecture
    model = UNetModel(
        3,
        2,
        encoder="unet",
        decoder_block=[3],
        encoder_levels=[32, 64],
        skip_type="concat",
    )
    _ = model.infer_batch(model, batch, device=select_device(on_gpu=ON_GPU))
