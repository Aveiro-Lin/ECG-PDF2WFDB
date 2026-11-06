#!/usr/bin/env python3
"""Create a tiny de-identified sample from a public WFDB release."""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import re
import shutil
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_IDS = (1, 3, 8, 149)
FORBIDDEN_TEXT = re.compile(
    r"姓名|患者编号|病历号|登记号|住院号|门诊号|医师|医生|"
    r"(?<!\d)(?:19|20)\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2}(?:日)?(?!\d)|"
    r"(?<!\d)\d{7,}(?!\d)"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--metadata-file", default="ecg_database.csv")
    parser.add_argument("--ecg-ids", type=int, nargs="+", default=list(DEFAULT_IDS))
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def opaque_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest().upper()[:16]
    return prefix + digest


def copy_record(release_root: Path, output_root: Path, row: pd.Series) -> None:
    for column in ("filename_lr", "filename_hr"):
        relative = Path(str(row[column]))
        for suffix in (".hea", ".dat"):
            source = release_root / f"{relative}{suffix}"
            if not source.is_file():
                raise FileNotFoundError(source)
            target = output_root / f"{relative}{suffix}"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    ecg_id = int(row["ecg_id"])
    bucket = f"{(ecg_id // 1000) * 1000:05d}"
    relative = Path("validity_masks") / bucket / f"{ecg_id:05d}_mask.npz"
    source = release_root / relative
    if not source.is_file():
        raise FileNotFoundError(source)
    target = output_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def write_records(metadata: pd.DataFrame, output_root: Path) -> None:
    lines: list[str] = []
    for column in ("filename_lr", "filename_hr"):
        lines.extend(metadata[column].astype(str).tolist())
    (output_root / "RECORDS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_trace_subset(
    release_root: Path,
    output_root: Path,
    original_metadata: pd.DataFrame,
    metadata: pd.DataFrame,
    source_row_index: pd.DataFrame,
    record_id_map: dict[str, str],
) -> None:
    trace_root = output_root / "trace_compat"
    trace_root.mkdir(parents=True, exist_ok=True)
    row_by_id = {
        int(row.ecg_id): int(row.row_index)
        for row in source_row_index.itertuples(index=False)
    }
    selected_indices = [row_by_id[int(ecg_id)] for ecg_id in original_metadata.ecg_id]
    full_data = np.load(release_root / "trace_compat" / "full_data.npy", mmap_mode="r")
    valid_mask = np.load(release_root / "trace_compat" / "valid_mask.npy", mmap_mode="r")
    np.save(trace_root / "full_data.npy", np.asarray(full_data[selected_indices], dtype=np.float32))
    np.save(trace_root / "valid_mask.npy", np.asarray(valid_mask[selected_indices], dtype=bool))

    row_index = pd.DataFrame(
        {
            "row_index": list(range(len(metadata))),
            "ecg_id": metadata.ecg_id.astype(int).tolist(),
            "record_uid": metadata.record_uid.astype(str).tolist(),
            "record_name": [f"{int(ecg_id):05d}" for ecg_id in metadata.ecg_id],
        }
    )
    row_index.to_csv(trace_root / "row_index.csv", index=False)

    evaluation = pd.read_csv(release_root / "trace_compat" / "evaluation_subsets.csv")
    evaluation = evaluation[evaluation.ecg_id.isin(metadata.ecg_id)].copy()
    evaluation["row_index"] = range(len(evaluation))
    evaluation["record_uid"] = evaluation["record_uid"].map(record_id_map)
    evaluation.to_csv(trace_root / "evaluation_subsets.csv", index=False)

    compat = pd.read_csv(release_root / "trace_compat" / "ptbxl_compat_database.csv")
    compat = compat[compat.ecg_id.isin(metadata.ecg_id)].copy()
    compat["patient_id"] = compat["patient_id"].map(
        dict(zip(original_metadata.patient_id, metadata.patient_id))
    )
    compat["record_uid"] = compat["record_uid"].map(record_id_map)
    compat.to_csv(trace_root / "ptbxl_compat_database.csv", index=False)

    statements = pd.read_csv(release_root / "trace_compat" / "scp_statements.csv", index_col=0)
    used_codes: set[str] = set()
    for value in metadata.scp_codes.astype(str):
        used_codes.update(ast.literal_eval(value).keys())
    statements = statements.loc[sorted(used_codes)] if used_codes else statements.iloc[0:0]
    statements.index.name = "scp_code"
    statements.to_csv(trace_root / "scp_statements.csv")
    statements.to_csv(output_root / "ecg_statements.csv")


def write_manifest(output_root: Path) -> None:
    excluded = {"MANIFEST.csv", "SHA256SUMS.txt"}
    files = sorted(
        path
        for path in output_root.rglob("*")
        if path.is_file() and path.name not in excluded and "__pycache__" not in path.parts
    )
    rows: list[dict[str, object]] = []
    for path in files:
        relative = path.relative_to(output_root).as_posix()
        if relative.startswith("records500/"):
            role = "wfdb_500hz_reconstruction_grid"
        elif relative.startswith("records100/"):
            role = "wfdb_100hz_derived_grid"
        elif relative.startswith("validity_masks/"):
            role = "observed_interval_mask"
        elif relative.startswith("trace_compat/"):
            role = "trace_compatibility"
        else:
            role = "metadata_or_documentation"
        rows.append(
            {
                "path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "role": role,
            }
        )
    with (output_root / "MANIFEST.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=("path", "size_bytes", "sha256", "role"))
        writer.writeheader()
        writer.writerows(rows)
    (output_root / "SHA256SUMS.txt").write_text(
        "".join(f"{row['sha256']}  {row['path']}\n" for row in rows), encoding="utf-8"
    )


def main() -> int:
    args = parse_args()
    release_root = args.release_root.resolve()
    output_root = args.output_root.resolve()
    metadata_path = release_root / args.metadata_file
    if not metadata_path.is_file():
        raise SystemExit(f"Metadata file not found: {metadata_path}")
    if output_root.exists():
        if not args.overwrite:
            raise SystemExit(f"Output exists; pass --overwrite: {output_root}")
        for path in sorted(output_root.rglob("*"), reverse=True):
            if path.is_file() or path.is_symlink():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
    output_root.mkdir(parents=True, exist_ok=True)

    ids = sorted(set(int(value) for value in args.ecg_ids))
    metadata_all = pd.read_csv(metadata_path)
    missing = sorted(set(ids).difference(metadata_all.ecg_id.astype(int)))
    if missing:
        raise SystemExit(f"Unknown public ECG IDs: {missing}")
    original = metadata_all[metadata_all.ecg_id.isin(ids)].copy().sort_values("ecg_id")
    text = "\n".join(original.report.fillna("").astype(str).tolist())
    if FORBIDDEN_TEXT.search(text):
        raise SystemExit("The selected diagnosis text contains a forbidden identifier pattern.")

    metadata = original.copy()
    patient_map = {
        value: opaque_id("PAT", value) for value in original.patient_id.astype(str).unique()
    }
    record_map = {
        value: opaque_id("REC", value) for value in original.record_uid.astype(str).unique()
    }
    metadata["patient_id"] = metadata["patient_id"].astype(str).map(patient_map)
    metadata["record_uid"] = metadata["record_uid"].astype(str).map(record_map)

    for _, row in original.iterrows():
        copy_record(release_root, output_root, row)
    metadata.to_csv(output_root / "ecg_database.csv", index=False)
    write_records(metadata, output_root)
    source_row_index = pd.read_csv(release_root / "trace_compat" / "row_index.csv")
    write_trace_subset(release_root, output_root, original, metadata, source_row_index, record_map)

    qc = pd.read_csv(release_root / "quality_control" / "record_qc.csv")
    (output_root / "quality_control").mkdir(parents=True, exist_ok=True)
    qc[qc.ecg_id.isin(metadata.ecg_id)].to_csv(
        output_root / "quality_control" / "record_qc.csv", index=False
    )
    (output_root / "LICENSE_DATA.txt").write_text(
        "The example records are a small de-identified subset of a separately\n"
        "distributed clinical ECG release. They retain that release's data terms\n"
        "and attribution requirements. The authoritative provenance, governance\n"
        "and version information are supplied by the source data record.\n"
        "Licence reference: https://creativecommons.org/licenses/by/4.0/\n",
        encoding="utf-8",
    )
    (output_root / "README.md").write_text(
        "# ECG conversion sample\n\n"
        "This directory contains four de-identified records selected to cover the "
        "EDAN, PSCRIPT, PSCRIPT_BUNDLE and MUSE layout families. It is a loader and "
        "smoke-test sample, not a replacement for the complete source release.\n\n"
        "The sample preserves a PTB-XL-compatible metadata schema with generic opaque "
        "IDs. Waveforms are vector-reconstructed lead segments; they are not native "
        "digital 12-lead recordings.\n\n"
        "```python\n"
        "import pandas as pd\n"
        "import wfdb\n"
        "from pathlib import Path\n\n"
        "root = Path('sample')\n"
        "meta = pd.read_csv(root / 'ecg_database.csv')\n"
        "signal, fields = wfdb.rdsamp(str(root / meta.iloc[0].filename_hr))\n"
        "print(signal.shape, fields['fs'], fields['sig_name'])\n"
        "```\n\n"
        "The example data retain the source release's data terms; see "
        "`LICENSE_DATA.txt`. The processing code is MIT-licensed.\n",
        encoding="utf-8",
    )
    write_manifest(output_root)
    print(f"Wrote {len(metadata)} sample records to {output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
