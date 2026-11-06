# ECG-PDF2WFDB

ECG-PDF2WFDB is a standalone processing toolkit for reconstructing vector ECG
traces from supported clinical-report PDF layouts and exporting WFDB records,
validity masks and standardized array representations. Optional model adapters,
including a TRACE-compatible representation, can be generated from the same
reconstructed signals.

The repository is a software release. It is designed to accept authorised source
PDFs from an institution or project and does not require the source data to be
distributed with the code. A four-record de-identified example is included only
for loader and smoke-test checks; it is not a replacement for the complete source
release.

<p align="center">
  <img src="./Private%20ECG%20Reconstruction%20Pipeline.png" alt="ECG-PDF2WFDB reconstruction pipeline" width="100%">
</p>

The diagram summarizes the conversion flow from supported ECG report PDFs to
reconstructed WFDB records, validity masks and standardized arrays. The TRACE
panel represents an optional model-specific adapter; source linkage artifacts
remain outside the public output.

## What the pipeline does

`processing/build_dataset.py` reads restricted local source PDFs and:

- identifies EDAN, PSCRIPT, PSCRIPT_BUNDLE and MUSE layouts;
- reconstructs printed lead paths on a 500-Hz coordinate grid;
- exports 500-Hz and 100-Hz WFDB records with validity masks;
- creates standardized 250-Hz arrays, including an optional `(record, 12, 2500)`
  TRACE-compatible adapter;
- extracts de-identified metadata and conservative PTB-XL/SCP-style mappings;
- keeps source-to-public linkage artifacts in a separate private directory.

The reconstructed records are not native digital ECG exports. Successive printed
lead windows may be asynchronous, and missing intervals remain missing in the WFDB
representation. Standardized arrays are loader-compatible representations and do
not recover unobserved physiology or cross-lead synchrony.

The parser is validated for the four layouts above. It is not a universal ECG-PDF
parser; other institutions and vendors may require new layout rules and independent
privacy review.

## Repository layout

```text
processing/
  build_dataset.py
  verify_release.py
  finalize_manifest.py
scripts/
  prepare_sample.py
sample/
  four de-identified records for smoke tests
DATA_DICTIONARY.md
PRIVACY.md
SAMPLE_DATA_NOTICE.md
requirements.txt
```

The example sample covers one record from each supported layout family and is about
1.3 MB. It contains WFDB records at 500 and 100 Hz, validity masks, standardized
arrays, metadata, a minimal statement table and SHA-256 checksums. It contains no
source PDFs, private identifier keys or source-to-public mappings.

## Optional model adapters

The core release format is WFDB plus validity masks and de-identified metadata.
The builder also emits `trace_compat/` arrays for projects that use the TRACE
input contract: finite arrays at 250 Hz with shape `(record, 12, 2500)` and an
aligned validity mask. This directory is an optional compatibility layer and can
be ignored by users who need only WFDB or their own downstream array format.

## Install

The processing environment was tested with Python 3.10.18:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Use the example

```python
from pathlib import Path
import pandas as pd
import wfdb

root = Path("sample")
metadata = pd.read_csv(root / "ecg_database.csv")
signal, fields = wfdb.rdsamp(str(root / metadata.iloc[0].filename_hr))
print(signal.shape, fields["fs"], fields["sig_name"])
```

Verify the sample files from the project root:

```bash
(cd sample && sha256sum --quiet -c SHA256SUMS.txt)
```

## Recreate the example from a public release

The sample builder reads a public WFDB release and remaps the example's opaque
identifiers so the example remains independent of the source release's identifiers:

```bash
python scripts/prepare_sample.py \
  --release-root /path/to/public-release \
  --metadata-file ecg_database.csv \
  --output-root sample --overwrite
```

The script reads only public release files. It never reads source PDFs or private
linkage directories.

## Build a release from restricted source PDFs

The source PDFs and private mapping workspace are not distributed. On an authorised
institutional system, build a release with explicit paths:

```bash
python processing/build_dataset.py \
  --input-root /restricted/source/pdf/root \
  --output-root /path/to/public-release \
  --private-root /restricted/private-audit-root \
  --ptbxl-root /path/to/PTB-XL
```

Run the release audit after assembly:

```bash
python processing/verify_release.py \
  --public-root /path/to/public-release \
  --report /path/to/public-release/quality_control/release_validation.json
```

For a dataset-specific patient split, pass `--split-file` explicitly. The verifier
otherwise checks only generic metadata, privacy, waveform, mask and array
properties.

Regenerate manifests only after the approved release files are final:

```bash
python processing/finalize_manifest.py --root /path/to/public-release
```

## Licences and responsible use

The processing code is released under the MIT licence in `LICENSE`. The example
records retain the data terms and attribution requirements of their source release;
see `LICENSE_DATA.txt` in the example directory and `SAMPLE_DATA_NOTICE.md`.
Privacy and field definitions are documented in `PRIVACY.md` and
`DATA_DICTIONARY.md`.
