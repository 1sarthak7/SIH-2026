"""
Feature Matching Service — Steps 3 & 4

Uses Kornia's LoFTR (Local Feature TRansformer) for dense feature matching.
The Siamese FPN encoders + Cross-Attention Transformer are all handled
by the LoFTR model internally.
"""

import torch
import numpy as np
from typing import Optional
from loguru import logger

from app.core.config import settings


class FeatureMatcher:
    """
    LoFTR-based feature matcher.

    Encapsulates model loading, GPU management, and batch inference.
    The LoFTR model internally handles:
    - FPN feature extraction (multi-scale)
    - Self-attention (intra-image geometry understanding)
    - Cross-attention (inter-image correspondence)
    - Coarse-to-fine matching (dense correspondence at sub-pixel accuracy)
    """

    def __init__(self, device: Optional[str] = None, pretrained: Optional[str] = None):
        self.device = device or settings.DEVICE

        # Validate CUDA availability
        if self.device == "cuda" and not torch.cuda.is_available():
            logger.warning("CUDA requested but not available, falling back to CPU")
            self.device = "cpu"

        self.pretrained = pretrained or settings.LOFTR_PRETRAINED
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load the LoFTR model."""
        import kornia.feature as KF

        logger.info(f"Loading LoFTR model (pretrained='{self.pretrained}') on {self.device}...")

        self.model = KF.LoFTR(pretrained=self.pretrained)
        self.model = self.model.to(self.device)
        self.model.eval()

        logger.success("LoFTR model loaded successfully.")

    def _prepare_tensor(self, image: np.ndarray) -> torch.Tensor:
        """
        Convert a numpy image to the tensor format LoFTR expects.

        LoFTR expects: (batch=1, channels=1, H, W), float32, range [0, 1]
        """
        if image.dtype != np.float32:
            image = image.astype(np.float32) / 255.0

        # Ensure 2D grayscale
        if image.ndim == 3:
            image = image[:, :, 0] if image.shape[2] <= 4 else image[0]

        # Add batch and channel dimensions: (H, W) → (1, 1, H, W)
        tensor = torch.from_numpy(image).unsqueeze(0).unsqueeze(0)
        return tensor.to(self.device)

    @torch.no_grad()
    def match_pair(
        self,
        image_a: np.ndarray,
        image_b: np.ndarray,
        confidence_threshold: Optional[float] = None,
    ) -> dict:
        """
        Find dense correspondences between two image patches.

        Args:
            image_a: First image patch (H, W), uint8 or float32
            image_b: Second image patch (H, W), uint8 or float32
            confidence_threshold: Minimum confidence to keep a match (0-1)

        Returns:
            dict with:
            - keypoints_a: (N, 2) array of (x, y) coordinates in image A
            - keypoints_b: (N, 2) array of (x, y) coordinates in image B
            - confidence: (N,) array of match confidence scores
            - num_matches: total number of matches after filtering
        """
        threshold = confidence_threshold or settings.LOFTR_CONFIDENCE_THRESHOLD

        # Prepare input tensors
        tensor_a = self._prepare_tensor(image_a)
        tensor_b = self._prepare_tensor(image_b)

        # Run LoFTR
        input_dict = {"image0": tensor_a, "image1": tensor_b}
        result = self.model(input_dict)

        # Extract results
        kpts_a = result["keypoints0"].cpu().numpy()  # (N, 2) — x, y
        kpts_b = result["keypoints1"].cpu().numpy()  # (N, 2) — x, y
        confidence = result["confidence"].cpu().numpy()  # (N,)

        # Filter by confidence
        mask = confidence >= threshold
        kpts_a = kpts_a[mask]
        kpts_b = kpts_b[mask]
        confidence = confidence[mask]

        logger.debug(
            f"  Matched: {mask.sum()}/{len(mask)} keypoints "
            f"(threshold={threshold:.2f}, "
            f"avg_conf={confidence.mean():.3f})" if len(confidence) > 0 else ""
        )

        return {
            "keypoints_a": kpts_a,
            "keypoints_b": kpts_b,
            "confidence": confidence,
            "num_matches": len(confidence),
        }

    @torch.no_grad()
    def match_patches(
        self,
        patches_a: list[dict],
        patches_b: list[dict],
        confidence_threshold: Optional[float] = None,
    ) -> list[dict]:
        """
        Match all patch pairs from two images.

        For efficiency, only matches patches that could potentially overlap
        (based on their spatial position in the original images).

        Args:
            patches_a: List of patch dicts from image A
            patches_b: List of patch dicts from image B
            confidence_threshold: Minimum confidence threshold

        Returns:
            List of match dicts, each containing:
            - keypoints_a: coordinates in original image A (offset-corrected)
            - keypoints_b: coordinates in original image B (offset-corrected)
            - confidence: match confidence scores
            - patch_a_id: source patch ID from image A
            - patch_b_id: source patch ID from image B
        """
        all_matches = []

        total_pairs = len(patches_a) * len(patches_b)
        logger.info(f"Matching {len(patches_a)} × {len(patches_b)} = {total_pairs} patch pairs...")

        for i, patch_a in enumerate(patches_a):
            for j, patch_b in enumerate(patches_b):
                result = self.match_pair(
                    patch_a["image"],
                    patch_b["image"],
                    confidence_threshold,
                )

                if result["num_matches"] > 0:
                    # Convert patch-local coordinates to full-image coordinates
                    kpts_a_global = result["keypoints_a"].copy()
                    kpts_a_global[:, 0] += patch_a["offset_x"]
                    kpts_a_global[:, 1] += patch_a["offset_y"]

                    kpts_b_global = result["keypoints_b"].copy()
                    kpts_b_global[:, 0] += patch_b["offset_x"]
                    kpts_b_global[:, 1] += patch_b["offset_y"]

                    all_matches.append({
                        "keypoints_a": kpts_a_global,
                        "keypoints_b": kpts_b_global,
                        "confidence": result["confidence"],
                        "patch_a_id": patch_a["patch_id"],
                        "patch_b_id": patch_b["patch_id"],
                    })

            # Progress logging
            if (i + 1) % 5 == 0 or i == len(patches_a) - 1:
                logger.info(f"  Processed patch {i + 1}/{len(patches_a)}")

        # Aggregate all matches
        if not all_matches:
            logger.warning("No matches found across any patch pairs!")
            return []

        total_matches = sum(m["confidence"].shape[0] for m in all_matches)
        logger.info(f"  Total raw matches across all patches: {total_matches}")

        return all_matches
