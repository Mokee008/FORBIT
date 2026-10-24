"""
src/coarse_noisy_loss.py - Coarse & Noisy Label Loss Module (30m Hansen vs 10m Sentinel-2)
Implements:
1. Coarse Spatial Consistency: 3x3 average pooling of 10m predictions to align with 30m Hansen labels
2. Shift-Tolerant Registration: Minimum loss across +/-1 pixel shifts to absorb boundary jitter
3. Symmetric / Noise-Robust BCE: Handles time-lagged and mislabeled training weak labels
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional

class CoarseConsistencyLoss(nn.Module):
    """
    Bridges 10m Sentinel-2 predictions with coarse 30m public Hansen GFC weak labels.
    Pools 10m sigmoid probabilities via 3x3 average pooling before loss computation.
    """
    def __init__(self, shift_tol: int = 1, label_smoothing: float = 0.05):
        super().__init__()
        self.shift_tol = shift_tol
        self.label_smoothing = label_smoothing

    def forward(self, pred_logits_10m: torch.Tensor, target_30m: torch.Tensor) -> torch.Tensor:
        """
        pred_logits_10m: (B, 1, H, W) - 10m resolution (e.g. 128x128)
        target_30m: (B, 1, H//3, W//3) or (B, 1, H, W) - 30m coarse weak labels
        """
        # Step 1: 3x3 Average Pooling from 10m to 30m spatial support
        prob_10m = torch.sigmoid(pred_logits_10m)
        pooled_prob_30m = F.avg_pool2d(prob_10m, kernel_size=3, stride=3)

        # Step 2: Ensure target is at 30m support
        if target_30m.shape[-2:] != pooled_prob_30m.shape[-2:]:
            target_pooled = F.max_pool2d(target_30m.float(), kernel_size=3, stride=3)
        else:
            target_pooled = target_30m.float()

        # Step 3: Apply label smoothing for noisy public labels
        smoothed_target = target_pooled * (1.0 - self.label_smoothing) + 0.5 * self.label_smoothing

        # Step 4: Shift-tolerant evaluation (+/- 1 pixel at 30m)
        best_loss = None
        eps = 1e-6

        for dy in range(-self.shift_tol, self.shift_tol + 1):
            for dx in range(-self.shift_tol, self.shift_tol + 1):
                shifted_prob = torch.roll(torch.roll(pooled_prob_30m, dy, dims=-2), dx, dims=-1)
                clamped_prob = torch.clamp(shifted_prob, eps, 1.0 - eps)

                # Binary cross-entropy on smoothed weak labels
                loss_field = -(
                    smoothed_target * torch.log(clamped_prob) +
                    (1.0 - smoothed_target) * torch.log(1.0 - clamped_prob)
                )
                loss_val = loss_field.mean(dim=[-2, -1], keepdim=True)

                if best_loss is None:
                    best_loss = loss_val
                else:
                    best_loss = torch.minimum(best_loss, loss_val)

        return best_loss.mean()

class NoiseRobustLoss(nn.Module):
    """
    Symmetric Cross-Entropy (SCE) combining BCE and Reverse Cross-Entropy (RCE).
    Provably robust to symmetric and asymmetric label noise in public satellite catalogs.
    """
    def __init__(self, alpha: float = 1.0, beta: float = 0.5):
        super().__init__()
        self.alpha = alpha
        self.beta = beta
        self.bce = nn.BCEWithLogitsLoss()

    def forward(self, pred_logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        # Align target resolution to pred_logits if different
        if target.shape[-2:] != pred_logits.shape[-2:]:
            target_aligned = F.interpolate(target.float(), size=pred_logits.shape[-2:], mode='nearest')
        else:
            target_aligned = target.float()

        # Standard BCE
        loss_ce = self.bce(pred_logits, target_aligned)

        # Reverse Cross Entropy (robust to noisy flip errors)
        prob = torch.sigmoid(pred_logits)
        prob = torch.clamp(prob, 1e-6, 1.0 - 1e-6)

        loss_rce = -(prob * torch.log(target_aligned + 1e-6) + (1.0 - prob) * torch.log(1.0 - target_aligned + 1e-6)).mean()

        return self.alpha * loss_ce + self.beta * loss_rce
