"""Optional LSTM predictor (PyTorch).

Imports lazily so the backend boots without `torch` installed. The LSTM is a
secondary signal source; the ensemble still works if it's absent.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class LSTMConfig:
    sequence_length: int = 60
    hidden_size: int = 128
    num_layers: int = 2
    dropout: float = 0.3
    lr: float = 1e-4
    epochs: int = 30
    batch_size: int = 64
    patience: int = 5
    device: str = "cpu"  # 'cuda' auto-detect below


class LSTMDirectionModel:
    """3-class (down/flat/up) probabilistic LSTM."""

    def __init__(self, cfg: LSTMConfig | None = None):
        self.cfg = cfg or LSTMConfig()
        self._net = None
        self._feature_names: list[str] = []
        self._input_size: int | None = None
        try:
            import torch  # noqa: F401
            self._torch_ok = True
        except ImportError:
            self._torch_ok = False

    def _build(self, input_size: int):
        import torch.nn as nn

        class _Net(nn.Module):
            def __init__(self, in_feat: int, hidden: int, layers: int, dropout: float):
                super().__init__()
                self.lstm = nn.LSTM(
                    input_size=in_feat,
                    hidden_size=hidden,
                    num_layers=layers,
                    dropout=dropout if layers > 1 else 0.0,
                    batch_first=True,
                )
                self.head = nn.Sequential(
                    nn.LayerNorm(hidden), nn.Linear(hidden, 64),
                    nn.ReLU(), nn.Dropout(dropout), nn.Linear(64, 3)
                )

            def forward(self, x):  # x: (B, T, F)
                out, _ = self.lstm(x)
                return self.head(out[:, -1, :])

        return _Net(input_size, self.cfg.hidden_size, self.cfg.num_layers, self.cfg.dropout)

    def _seq_stack(self, X: pd.DataFrame, y: pd.Series | None = None):
        arr = X.to_numpy(dtype=np.float32)
        L = self.cfg.sequence_length
        if len(arr) <= L:
            raise ValueError(f"need > {L} bars, have {len(arr)}")
        xs = np.stack([arr[i - L : i] for i in range(L, len(arr))])
        if y is not None:
            ys = y.to_numpy(dtype=np.int64)[L:]
            return xs, ys
        return xs

    def fit(self, X: pd.DataFrame, y: pd.Series) -> dict:
        if not self._torch_ok:
            raise RuntimeError("torch not installed — skip LSTM or `pip install torch`")
        import torch
        from torch.optim import AdamW
        from torch.optim.lr_scheduler import CosineAnnealingLR
        from torch.utils.data import DataLoader, TensorDataset

        device = "cuda" if torch.cuda.is_available() else self.cfg.device
        self._feature_names = list(X.columns)
        self._input_size = X.shape[1]

        xs, ys = self._seq_stack(X, y)
        split = int(0.8 * len(xs))
        tr = TensorDataset(torch.from_numpy(xs[:split]), torch.from_numpy(ys[:split]))
        vl = TensorDataset(torch.from_numpy(xs[split:]), torch.from_numpy(ys[split:]))
        trdl = DataLoader(tr, batch_size=self.cfg.batch_size, shuffle=False)
        vldl = DataLoader(vl, batch_size=self.cfg.batch_size)

        net = self._build(self._input_size).to(device)
        opt = AdamW(net.parameters(), lr=self.cfg.lr)
        sched = CosineAnnealingLR(opt, T_max=self.cfg.epochs)
        loss_fn = torch.nn.CrossEntropyLoss()
        best = float("inf")
        bad = 0
        history = []
        for epoch in range(self.cfg.epochs):
            net.train()
            total = 0.0
            for xb, yb in trdl:
                xb, yb = xb.to(device), yb.to(device)
                opt.zero_grad()
                logits = net(xb)
                loss = loss_fn(logits, yb)
                loss.backward()
                opt.step()
                total += loss.item() * len(xb)
            sched.step()
            train_loss = total / len(tr)
            net.eval()
            v_total = 0.0
            correct = 0
            with torch.no_grad():
                for xb, yb in vldl:
                    xb, yb = xb.to(device), yb.to(device)
                    logits = net(xb)
                    v_total += loss_fn(logits, yb).item() * len(xb)
                    correct += (logits.argmax(1) == yb).sum().item()
            val_loss = v_total / max(1, len(vl))
            val_acc = correct / max(1, len(vl))
            history.append({"epoch": epoch, "train": train_loss, "val": val_loss, "acc": val_acc})
            if val_loss < best - 1e-4:
                best = val_loss
                bad = 0
            else:
                bad += 1
                if bad >= self.cfg.patience:
                    break
        self._net = net
        return {"history": history, "best_val_loss": best}

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        import torch

        if self._net is None:
            raise RuntimeError("model not fitted")
        device = next(self._net.parameters()).device
        xs = self._seq_stack(X[self._feature_names])
        self._net.eval()
        with torch.no_grad():
            logits = self._net(torch.from_numpy(xs).to(device))
            probs = torch.softmax(logits, dim=1).cpu().numpy()
        return probs

    def save(self, path: str | Path) -> None:
        import torch

        if self._net is None:
            raise RuntimeError("model not fitted")
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {"state": self._net.state_dict(), "features": self._feature_names, "cfg": self.cfg.__dict__},
            p,
        )
