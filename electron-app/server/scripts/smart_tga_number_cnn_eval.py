"""Evaluate a small CNN race-number crop detector for Smart TGA.

This is offline Smart TGA tooling. It trains a tiny PyTorch CNN on the reviewed
number-vs-confuser crop corpus using grouped holdout folds. It is meant to test
whether a stronger visual classifier is worth pursuing before any Auto-build
Layers integration.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageEnhance
from torch import nn
from torch.utils.data import DataLoader, Dataset


DEFAULT_MANIFEST = Path("_smart_tga_runs/cycle65_arcachevy_reviewed_corpus_v1/manifest.json")
IMG_SIZE = 64
FOLD_STRATEGY = "balanced_group_counts_v1"


def _source_group(record: dict[str, Any]) -> str:
    if record["label"] == "number":
        return str(record.get("folder") or Path(record.get("car_num", record["file"])).parent.name)
    return str(record.get("probe_label") or Path(record.get("paint", record["file"])).stem)


def _paint_group(record: dict[str, Any]) -> str:
    source = record.get("paint") or record.get("car_num") or record.get("car") or record.get("file")
    path = Path(str(source))
    parent = path.parent.name if path.parent.name else "unknown"
    return f"{parent}/{path.stem}"


def _load_manifest(path: Path, group_mode: str) -> list[dict[str, Any]]:
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError(f"expected manifest list in {path}")
    for rec in records:
        rec["truth"] = 1 if rec["label"] == "number" else 0
        rec["group"] = _source_group(rec) if group_mode == "source" else _paint_group(rec)
    return records


def _make_folds(records: list[dict[str, Any]], fold_count: int, seed: int) -> list[list[int]]:
    groups = sorted({str(rec["group"]) for rec in records})
    rng = random.Random(seed)
    group_rows: list[dict[str, Any]] = []
    total_pos = sum(1 for rec in records if rec["truth"] == 1)
    total_neg = len(records) - total_pos
    target_pos = total_pos / max(1, fold_count)
    target_neg = total_neg / max(1, fold_count)
    target_total = len(records) / max(1, fold_count)
    for group in groups:
        indexes = [idx for idx, rec in enumerate(records) if str(rec["group"]) == group]
        pos = sum(1 for idx in indexes if records[idx]["truth"] == 1)
        neg = len(indexes) - pos
        group_rows.append({"group": group, "indexes": indexes, "pos": pos, "neg": neg, "count": len(indexes), "jitter": rng.random()})
    group_rows.sort(key=lambda row: (-int(row["count"]), -max(int(row["pos"]), int(row["neg"])), float(row["jitter"])))

    folds: list[list[str]] = [[] for _ in range(fold_count)]
    fold_stats = [{"count": 0, "pos": 0, "neg": 0} for _ in range(fold_count)]
    remaining = list(group_rows)

    def assign_row(row: dict[str, Any], fold_index: int) -> None:
        folds[fold_index].append(str(row["group"]))
        fold_stats[fold_index]["count"] += int(row["count"])
        fold_stats[fold_index]["pos"] += int(row["pos"])
        fold_stats[fold_index]["neg"] += int(row["neg"])

    for class_key in ("pos", "neg"):
        for row in list(sorted(remaining, key=lambda item: (-int(item[class_key]), -int(item["count"]), float(item["jitter"])))):
            missing = [idx for idx in range(fold_count) if fold_stats[idx][class_key] == 0]
            if not missing:
                break
            if int(row[class_key]) <= 0:
                continue
            best_fold = min(missing, key=lambda idx: (fold_stats[idx]["count"], fold_stats[idx]["pos"], fold_stats[idx]["neg"]))
            assign_row(row, best_fold)
            remaining.remove(row)

    for row in remaining:
        best_fold = min(
            range(fold_count),
            key=lambda idx: (
                abs((fold_stats[idx]["pos"] + int(row["pos"])) - target_pos)
                + abs((fold_stats[idx]["neg"] + int(row["neg"])) - target_neg)
                + 0.25 * abs((fold_stats[idx]["count"] + int(row["count"])) - target_total),
                fold_stats[idx]["count"],
            ),
        )
        assign_row(row, best_fold)

    valid: list[list[int]] = []
    for fold_groups in folds:
        group_set = set(fold_groups)
        test_idx = [idx for idx, rec in enumerate(records) if rec["group"] in group_set]
        if len({records[idx]["truth"] for idx in test_idx}) < 2:
            continue
        train_idx = [idx for idx in range(len(records)) if idx not in test_idx]
        if len({records[idx]["truth"] for idx in train_idx}) < 2:
            continue
        valid.append(test_idx)
    return valid


def _pil_to_tensor(img: Image.Image, augment: bool, rng: random.Random) -> torch.Tensor:
    img = img.convert("RGB").resize((IMG_SIZE, IMG_SIZE), Image.Resampling.LANCZOS)
    if augment:
        if rng.random() < 0.7:
            img = img.rotate(rng.uniform(-8.0, 8.0), resample=Image.Resampling.BICUBIC, fillcolor=(0, 0, 0))
        if rng.random() < 0.5:
            img = ImageEnhance.Color(img).enhance(rng.uniform(0.82, 1.18))
        if rng.random() < 0.5:
            img = ImageEnhance.Contrast(img).enhance(rng.uniform(0.85, 1.20))
        if rng.random() < 0.35:
            img = ImageEnhance.Brightness(img).enhance(rng.uniform(0.88, 1.12))
    arr = np.asarray(img).astype(np.float32) / 255.0
    arr = np.transpose(arr, (2, 0, 1))
    return torch.from_numpy(arr)


class CropDataset(Dataset):
    def __init__(self, records: list[dict[str, Any]], indexes: list[int], augment: bool, seed: int):
        self.records = records
        self.indexes = indexes
        self.augment = augment
        self.seed = seed

    def __len__(self) -> int:
        return len(self.indexes)

    def __getitem__(self, item: int) -> tuple[torch.Tensor, torch.Tensor]:
        idx = self.indexes[item]
        rec = self.records[idx]
        rng = random.Random(self.seed + idx * 1009 + item)
        img = Image.open(rec["file"])
        tensor = _pil_to_tensor(img, self.augment, rng)
        label = torch.tensor(float(rec["truth"]), dtype=torch.float32)
        return tensor, label


class TinyNumberCNN(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 96, 3, padding=1),
            nn.BatchNorm2d(96),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((1, 1)),
        )
        self.head = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(0.25),
            nn.Linear(96, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.head(self.features(x)).squeeze(1)


def _predict(model: nn.Module, loader: DataLoader, device: torch.device) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    probs: list[np.ndarray] = []
    truths: list[np.ndarray] = []
    with torch.no_grad():
        for x, y in loader:
            logits = model(x.to(device))
            probs.append(torch.sigmoid(logits).cpu().numpy())
            truths.append(y.numpy())
    return np.concatenate(probs), np.concatenate(truths).astype(np.int32)


def _contact_sheet(records: list[dict[str, Any]], out_path: Path, title: str) -> None:
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


def _train_fold(
    records: list[dict[str, Any]],
    train_idx: list[int],
    test_idx: list[int],
    args: argparse.Namespace,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    train_ds = CropDataset(records, train_idx, augment=True, seed=seed)
    test_ds = CropDataset(records, test_idx, augment=False, seed=seed + 17)
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=0)
    test_loader = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)
    model = TinyNumberCNN().to(device)
    pos = sum(records[idx]["truth"] for idx in train_idx)
    neg = len(train_idx) - pos
    pos_weight = torch.tensor([max(1.0, neg / max(1.0, float(pos))) * args.pos_weight_scale], device=device)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    for _epoch in range(args.epochs):
        model.train()
        for x, y in train_loader:
            opt.zero_grad(set_to_none=True)
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
    return _predict(model, test_loader, device)


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    records = _load_manifest(args.manifest, args.holdout_mode)
    folds = _make_folds(records, args.folds, args.seed)
    if args.max_folds:
        folds = folds[:args.max_folds]
    fold_results: list[dict[str, Any]] = []
    mistakes: list[dict[str, Any]] = []
    fold_prob_cache: list[dict[str, Any]] = []
    for fold_no, test_idx in enumerate(folds):
        train_idx = [idx for idx in range(len(records)) if idx not in test_idx]
        probs, truth = _train_fold(records, train_idx, test_idx, args, args.seed + fold_no * 31)
        fold_prob_cache.append({"fold": fold_no, "test_idx": test_idx, "probs": probs.tolist(), "truth": truth.tolist()})
        pred = (probs >= args.threshold).astype(np.int32)
        fold_mistakes: list[dict[str, Any]] = []
        for local_idx, p, t, prob in zip(test_idx, pred, truth, probs):
            if int(p) == int(t):
                continue
            rec = records[local_idx]
            mistake = {
                "file": rec["file"],
                "truth": int(t),
                "pred": int(p),
                "prob": round(float(prob), 4),
                "label": rec["label"],
                "group": rec["group"],
                "fold": fold_no,
            }
            fold_mistakes.append(mistake)
            mistakes.append(mistake)
        fold_results.append({
            "fold": fold_no,
            "train": len(train_idx),
            "test": len(test_idx),
            "test_groups": sorted({records[idx]["group"] for idx in test_idx}),
            "accuracy": round(float((pred == truth).mean()), 4),
            "false_positive": int(((pred == 1) & (truth == 0)).sum()),
            "false_negative": int(((pred == 0) & (truth == 1)).sum()),
            "mistakes": fold_mistakes,
        })
    accuracies = [f["accuracy"] for f in fold_results]
    threshold_sweep: list[dict[str, Any]] = []
    for threshold in [round(v, 2) for v in np.linspace(0.15, 0.85, 15)]:
        fold_acc: list[float] = []
        fp_total = 0
        fn_total = 0
        fp_files: set[str] = set()
        fn_files: set[str] = set()
        for cache in fold_prob_cache:
            probs = np.asarray(cache["probs"], dtype=np.float32)
            truth = np.asarray(cache["truth"], dtype=np.int32)
            pred = (probs >= threshold).astype(np.int32)
            fold_acc.append(float((pred == truth).mean()))
            for idx, p, t in zip(cache["test_idx"], pred, truth):
                if int(p) == int(t):
                    continue
                rec = records[idx]
                if int(t) == 0 and int(p) == 1:
                    fp_total += 1
                    fp_files.add(rec["file"])
                elif int(t) == 1 and int(p) == 0:
                    fn_total += 1
                    fn_files.add(rec["file"])
        threshold_sweep.append({
            "threshold": threshold,
            "mean_accuracy": round(float(np.mean(fold_acc)), 4) if fold_acc else 0.0,
            "min_accuracy": round(float(np.min(fold_acc)), 4) if fold_acc else 0.0,
            "total_false_positive": fp_total,
            "total_false_negative": fn_total,
            "unique_false_positive_files": len(fp_files),
            "unique_false_negative_files": len(fn_files),
        })
    best_threshold = max(threshold_sweep, key=lambda r: (r["mean_accuracy"], r["min_accuracy"])) if threshold_sweep else None
    summary = {
        "manifest": str(args.manifest),
        "holdout_mode": args.holdout_mode,
        "model": "tiny_cnn_v1",
        "fold_strategy": FOLD_STRATEGY,
        "samples": len(records),
        "positive_samples": sum(1 for r in records if r["truth"] == 1),
        "hard_negative_samples": sum(1 for r in records if r["truth"] == 0),
        "folds": len(fold_results),
        "epochs": args.epochs,
        "loss": args.loss,
        "focal_gamma": args.focal_gamma if args.loss == "focal" else None,
        "pos_weight_scale": args.pos_weight_scale,
        "threshold": args.threshold,
        "mean_accuracy": round(float(np.mean(accuracies)), 4) if accuracies else 0.0,
        "min_accuracy": round(float(np.min(accuracies)), 4) if accuracies else 0.0,
        "total_false_positive": sum(f["false_positive"] for f in fold_results),
        "total_false_negative": sum(f["false_negative"] for f in fold_results),
        "unique_false_positive_files": len({m["file"] for m in mistakes if m["truth"] == 0 and m["pred"] == 1}),
        "unique_false_negative_files": len({m["file"] for m in mistakes if m["truth"] == 1 and m["pred"] == 0}),
        "threshold_sweep": threshold_sweep,
        "best_threshold_by_mean": best_threshold,
        "fold_results": fold_results,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "cnn_eval.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    mistake_records: list[dict[str, Any]] = []
    by_file = {rec["file"]: rec for rec in records}
    for mistake in mistakes[:36]:
        rec = dict(by_file[mistake["file"]])
        rec.update(mistake)
        mistake_records.append(rec)
    _contact_sheet(mistake_records, args.output / "mistakes_contact_sheet.png", "Smart TGA CNN mistakes")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=Path("_smart_tga_runs/smart_tga_number_cnn_eval"))
    parser.add_argument("--holdout-mode", choices=["source", "paint"], default="source")
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--max-folds", type=int, default=0)
    parser.add_argument("--epochs", type=int, default=18)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=0.0012)
    parser.add_argument("--weight-decay", type=float, default=0.0008)
    parser.add_argument("--loss", choices=["bce", "focal"], default="bce")
    parser.add_argument("--focal-gamma", type=float, default=2.0)
    parser.add_argument("--pos-weight-scale", type=float, default=1.0)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--cpu", action="store_true")
    return parser.parse_args()


def main() -> None:
    summary = evaluate(parse_args())
    brief = {k: v for k, v in summary.items() if k != "fold_results"}
    print(json.dumps(brief, indent=2))


if __name__ == "__main__":
    main()
