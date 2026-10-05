"""External train/test evaluation for Smart TGA number classifiers.

This is offline Smart TGA tooling. It trains on one reviewed crop manifest and
tests on another, optionally excluding crops already seen in training. Use this
to check whether a promising fold result actually generalizes to newly reviewed
Smart TGA candidates before considering any Auto-build integration.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image, ImageDraw
from torch import nn
from torch.utils.data import DataLoader

from smart_tga_number_cnn_eval import CropDataset, TinyNumberCNN, _load_manifest
from smart_tga_number_cnn_meta_eval import META_DIM, MetaCropDataset, TinyNumberCNNMeta, _meta_vector


def _train_image_model(
    records: list[dict[str, Any]],
    train_idx: list[int],
    args: argparse.Namespace,
) -> nn.Module:
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    random.seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    dataset = CropDataset(records, train_idx, augment=True, seed=args.seed)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, num_workers=0)
    model = TinyNumberCNN().to(device)
    _train_loop(model, loader, records, train_idx, args, device, meta_model=False)
    return model


def _train_meta_model(
    records: list[dict[str, Any]],
    meta: np.ndarray,
    train_idx: list[int],
    args: argparse.Namespace,
) -> tuple[nn.Module, np.ndarray, np.ndarray]:
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    random.seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    train_meta = meta[train_idx]
    mean = train_meta.mean(axis=0).astype(np.float32)
    std = np.maximum(train_meta.std(axis=0).astype(np.float32), 1e-4)
    dataset = MetaCropDataset(records, train_idx, meta, mean, std, augment=True, seed=args.seed)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, num_workers=0)
    model = TinyNumberCNNMeta(meta.shape[1]).to(device)
    _train_loop(model, loader, records, train_idx, args, device, meta_model=True)
    return model, mean, std


def _train_loop(
    model: nn.Module,
    loader: DataLoader,
    records: list[dict[str, Any]],
    train_idx: list[int],
    args: argparse.Namespace,
    device: torch.device,
    meta_model: bool,
) -> None:
    pos = sum(records[idx]["truth"] for idx in train_idx)
    neg = len(train_idx) - pos
    pos_weight = torch.tensor([max(1.0, neg / max(1.0, float(pos))) * args.pos_weight_scale], device=device)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    for _epoch in range(args.epochs):
        model.train()
        for batch in loader:
            opt.zero_grad(set_to_none=True)
            if meta_model:
                x, meta_batch, y = batch
                logits = model(x.to(device), meta_batch.to(device))
            else:
                x, y = batch
                logits = model(x.to(device))
            target = y.to(device)
            if args.loss == "focal":
                bce = nn.functional.binary_cross_entropy_with_logits(
                    logits,
                    target,
                    pos_weight=pos_weight,
                    reduction="none",
                )
                prob = torch.sigmoid(logits)
                pt = torch.where(target > 0.5, prob, 1.0 - prob).clamp(1e-4, 1.0 - 1e-4)
                loss = (((1.0 - pt) ** args.focal_gamma) * bce).mean()
            else:
                loss = loss_fn(logits, target)
            loss.backward()
            opt.step()


def _predict_image(model: nn.Module, records: list[dict[str, Any]], indexes: list[int], args: argparse.Namespace) -> np.ndarray:
    device = next(model.parameters()).device
    dataset = CropDataset(records, indexes, augment=False, seed=args.seed + 17)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False, num_workers=0)
    probs: list[np.ndarray] = []
    model.eval()
    with torch.no_grad():
        for x, _y in loader:
            probs.append(torch.sigmoid(model(x.to(device))).cpu().numpy())
    return np.concatenate(probs)


def _predict_meta(
    model: nn.Module,
    records: list[dict[str, Any]],
    indexes: list[int],
    meta: np.ndarray,
    mean: np.ndarray,
    std: np.ndarray,
    args: argparse.Namespace,
) -> np.ndarray:
    device = next(model.parameters()).device
    dataset = MetaCropDataset(records, indexes, meta, mean, std, augment=False, seed=args.seed + 17)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False, num_workers=0)
    probs: list[np.ndarray] = []
    model.eval()
    with torch.no_grad():
        for x, meta_batch, _y in loader:
            probs.append(torch.sigmoid(model(x.to(device), meta_batch.to(device))).cpu().numpy())
    return np.concatenate(probs)


def _sheet(records: list[dict[str, Any]], out_path: Path, title: str) -> None:
    if not records:
        return
    cols = 6
    cell = 190
    rows = int(np.ceil(len(records) / cols))
    sheet = Image.new("RGB", (cols * cell, rows * cell), (28, 28, 28))
    draw = ImageDraw.Draw(sheet)
    for idx, rec in enumerate(records):
        x = (idx % cols) * cell
        y = (idx // cols) * cell
        img = Image.open(rec["file"]).convert("RGB").resize((156, 156), Image.Resampling.LANCZOS)
        sheet.paste(img, (x + 17, y + 24))
        draw.text((x + 6, y + 5), f"truth {rec['truth']} pred {rec['pred']} p {rec['prob']:.2f}", fill=(255, 220, 120))
        draw.text((x + 6, y + 176), str(rec.get("group", ""))[:27], fill=(220, 220, 220))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    draw.text((8, 8), title, fill=(255, 255, 255))
    sheet.save(out_path)


def _test_records(args: argparse.Namespace, train_records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[int], int]:
    test_records = _load_manifest(args.test_manifest, args.group_mode)
    indexes = list(range(len(test_records)))
    excluded = 0
    if args.exclude_train_files:
        train_files = {str(Path(rec["file"]).resolve()).lower() for rec in train_records}
        kept: list[int] = []
        for idx, rec in enumerate(test_records):
            if str(Path(rec["file"]).resolve()).lower() in train_files:
                excluded += 1
                continue
            kept.append(idx)
        indexes = kept
    if args.max_test_samples and len(indexes) > args.max_test_samples:
        indexes = indexes[: args.max_test_samples]
    if not indexes:
        raise ValueError("no test samples remain after filters")
    return test_records, indexes, excluded


def _threshold_sweep(records: list[dict[str, Any]], indexes: list[int], probs: np.ndarray) -> list[dict[str, Any]]:
    truth = np.asarray([records[idx]["truth"] for idx in indexes], dtype=np.int32)
    rows: list[dict[str, Any]] = []
    thresholds = [round(v, 2) for v in np.linspace(0.15, 0.85, 15)] + [0.9, 0.95, 0.98, 0.99]
    for threshold in thresholds:
        pred = (probs >= threshold).astype(np.int32)
        rows.append({
            "threshold": threshold,
            "accuracy": round(float((pred == truth).mean()), 4),
            "false_positive": int(((pred == 1) & (truth == 0)).sum()),
            "false_negative": int(((pred == 0) & (truth == 1)).sum()),
        })
    return rows


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    train_records = _load_manifest(args.train_manifest, args.group_mode)
    train_idx = list(range(len(train_records)))
    test_records, test_idx, excluded = _test_records(args, train_records)
    if args.model == "meta":
        train_meta = np.stack([_meta_vector(rec) for rec in train_records]).astype(np.float32)
        test_meta = np.stack([_meta_vector(rec) for rec in test_records]).astype(np.float32)
        if train_meta.shape[1] != META_DIM or test_meta.shape[1] != META_DIM:
            raise ValueError("unexpected metadata dimension")
        model, mean, std = _train_meta_model(train_records, train_meta, train_idx, args)
        probs = _predict_meta(model, test_records, test_idx, test_meta, mean, std, args)
    else:
        model = _train_image_model(train_records, train_idx, args)
        probs = _predict_image(model, test_records, test_idx, args)
    truth = np.asarray([test_records[idx]["truth"] for idx in test_idx], dtype=np.int32)
    pred = (probs >= args.threshold).astype(np.int32)
    mistakes: list[dict[str, Any]] = []
    for idx, p, t, prob in zip(test_idx, pred, truth, probs):
        if int(p) == int(t):
            continue
        rec = dict(test_records[idx])
        rec["pred"] = int(p)
        rec["prob"] = round(float(prob), 4)
        mistakes.append(rec)
    sweep = _threshold_sweep(test_records, test_idx, probs)
    best = max(sweep, key=lambda row: (row["accuracy"], -row["false_positive"], -row["false_negative"]))
    summary = {
        "train_manifest": str(args.train_manifest),
        "test_manifest": str(args.test_manifest),
        "model": f"external_{args.model}",
        "group_mode": args.group_mode,
        "train_samples": len(train_records),
        "train_positive": sum(1 for r in train_records if r["truth"] == 1),
        "train_negative": sum(1 for r in train_records if r["truth"] == 0),
        "test_samples_all": len(test_records),
        "test_samples": len(test_idx),
        "test_excluded_seen_train_files": excluded,
        "test_positive": int(truth.sum()),
        "test_negative": int(len(truth) - truth.sum()),
        "epochs": args.epochs,
        "loss": args.loss,
        "threshold": args.threshold,
        "accuracy": round(float((pred == truth).mean()), 4),
        "false_positive": int(((pred == 1) & (truth == 0)).sum()),
        "false_negative": int(((pred == 0) & (truth == 1)).sum()),
        "threshold_sweep": sweep,
        "best_threshold_by_accuracy": best,
        "mistakes": [
            {
                "file": rec["file"],
                "label": rec["label"],
                "truth": rec["truth"],
                "pred": rec["pred"],
                "prob": rec["prob"],
                "group": rec.get("group"),
            }
            for rec in mistakes
        ],
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "external_eval.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _sheet(mistakes[:36], args.output / "mistakes_contact_sheet.png", "Smart TGA external eval mistakes")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-manifest", type=Path, required=True)
    parser.add_argument("--test-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", choices=["image", "meta"], default="image")
    parser.add_argument("--group-mode", choices=["source", "paint"], default="paint")
    parser.add_argument("--exclude-train-files", action="store_true")
    parser.add_argument("--max-test-samples", type=int, default=0)
    parser.add_argument("--epochs", type=int, default=28)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=0.0012)
    parser.add_argument("--weight-decay", type=float, default=0.0008)
    parser.add_argument("--loss", choices=["bce", "focal"], default="focal")
    parser.add_argument("--focal-gamma", type=float, default=2.0)
    parser.add_argument("--pos-weight-scale", type=float, default=1.0)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--cpu", action="store_true")
    return parser.parse_args()


def main() -> None:
    summary = evaluate(parse_args())
    brief = {k: v for k, v in summary.items() if k not in {"mistakes", "threshold_sweep"}}
    print(json.dumps(brief, indent=2))


if __name__ == "__main__":
    main()
