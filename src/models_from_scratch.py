"""
src/models_from_scratch.py - Neural Architectures Initialized from Scratch
RULE R1 ENFORCED: Zero pretrained weights, zero timm/torchvision backbones.
All weights initialized via Kaiming normal distribution with fixed RNG seed.
"""

import math
from typing import Tuple, Optional
import torch
import torch.nn as nn
import torch.nn.functional as F

def init_weights_kaiming(m: nn.Module):
    """Explicitly initializes module weights from scratch using He / Kaiming normal."""
    if isinstance(m, (nn.Conv2d, nn.Conv1d, nn.Linear)):
        nn.init.kaiming_normal_(m.weight, mode="fan_out", nonlinearity="relu")
        if m.bias is not None:
            nn.init.zeros_(m.bias)
    elif isinstance(m, (nn.BatchNorm2d, nn.BatchNorm1d, nn.LayerNorm)):
        nn.init.ones_(m.weight)
        nn.init.zeros_(m.bias)

class DoubleConv2d(nn.Module):
    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True)
        )
        self.apply(init_weights_kaiming)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)

class UNetFromScratch(nn.Module):
    """
    Lightweight 4-level U-Net (~1.8M params) built from scratch.
    Capable of training on free T4 GPU or Apple Silicon MPS in minutes.
    """
    def __init__(self, in_channels: int = 12, out_channels: int = 1):
        super().__init__()
        # Encoder
        self.inc = DoubleConv2d(in_channels, 32)
        self.down1 = nn.Sequential(nn.MaxPool2d(2), DoubleConv2d(32, 64))
        self.down2 = nn.Sequential(nn.MaxPool2d(2), DoubleConv2d(64, 128))
        self.down3 = nn.Sequential(nn.MaxPool2d(2), DoubleConv2d(128, 256))

        # Decoder with skip connections
        self.up1 = nn.ConvTranspose2d(256, 128, kernel_size=2, stride=2)
        self.conv_up1 = DoubleConv2d(256, 128)

        self.up2 = nn.ConvTranspose2d(128, 64, kernel_size=2, stride=2)
        self.conv_up2 = DoubleConv2d(128, 64)

        self.up3 = nn.ConvTranspose2d(64, 32, kernel_size=2, stride=2)
        self.conv_up3 = DoubleConv2d(64, 32)

        self.outc = nn.Conv2d(32, out_channels, kernel_size=1)
        self.apply(init_weights_kaiming)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)

        u1 = self.up1(x4)
        u1 = torch.cat([u1, x3], dim=1)
        u1 = self.conv_up1(u1)

        u2 = self.up2(u1)
        u2 = torch.cat([u2, x2], dim=1)
        u2 = self.conv_up2(u2)

        u3 = self.up3(u2)
        u3 = torch.cat([u3, x1], dim=1)
        u3 = self.conv_up3(u3)

        logits = self.outc(u3)
        return logits

class CoarseConsistencyLoss(nn.Module):
    """
    Loss function bridging 10 m predictions to coarse 30 m noisy Hansen labels.
    Uses 3x3 average pooling to match Hansen spatial support, with +/-1 px shift tolerance.
    """
    def __init__(self, shift_tol: int = 1):
        super().__init__()
        self.shift_tol = shift_tol
        self.bce = nn.BCEWithLogitsLoss(reduction='none')

    def forward(self, pred_logits_10m: torch.Tensor, target_30m: torch.Tensor) -> torch.Tensor:
        """
        pred_logits_10m: (B, 1, H, W) where H, W = 128 (10m)
        target_30m: (B, 1, H//3, W//3) or (B, 1, H, W) Hansen labels
        """
        # Pool 10m probabilities to 30m resolution (3x3 average pool)
        prob_10m = torch.sigmoid(pred_logits_10m)
        pooled_prob_30m = F.avg_pool2d(prob_10m, kernel_size=3, stride=3)

        if target_30m.shape[-2:] != pooled_prob_30m.shape[-2:]:
            target_pooled = F.max_pool2d(target_30m.float(), kernel_size=3, stride=3)
        else:
            target_pooled = target_30m.float()

        # Shift tolerance: test slight coordinate shifts (+-1 pixel at 30m) and take minimum loss
        best_loss = None
        for dy in range(-self.shift_tol, self.shift_tol + 1):
            for dx in range(-self.shift_tol, self.shift_tol + 1):
                shifted_prob = torch.roll(torch.roll(pooled_prob_30m, dy, dims=-2), dx, dims=-1)
                # Binary cross-entropy on pooled probabilities
                eps = 1e-6
                clamped_prob = torch.clamp(shifted_prob, eps, 1.0 - eps)
                loss_field = -(target_pooled * torch.log(clamped_prob) + (1.0 - target_pooled) * torch.log(1.0 - clamped_prob))
                loss_val = loss_field.mean(dim=[-2, -1], keepdim=True)

                if best_loss is None:
                    best_loss = loss_val
                else:
                    best_loss = torch.minimum(best_loss, loss_val)

        return best_loss.mean()

def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
