# Public output data dictionary

This dictionary describes the generic release layout produced by the processing
pipeline. Dataset-specific governance, labels and access terms belong to the
source data record.

## `ecg_database.csv`

| Field | Meaning |
|---|---|
| `ecg_id` | Sequential public record index. |
| `patient_id` | Opaque keyed patient identifier. The private key is never released. |
| `record_uid` | Opaque keyed record identifier. |
| `age` | Numeric age when available; ages 90 years or older are suppressed. |
| `age_is_90_plus` | Boolean indicator for the suppressed age group. |
| `sex` | `1` male, `0` female, empty when unavailable. |
| `report`, `diagnosis_text` | Screened diagnosis-region text when permitted by the source governance. |
| `scp_codes` | Python-literal mapping from PTB-XL/SCP statement code to `100.0`; code presence is not clinical confidence. |
| `mapping_status` | Mapping provenance, including `rule_based_unverified`. |
| `source_representation` | Describes vector-reconstructed printed lead segments. |
| `source_template`, `layout_subtype` | PDF layout family used by the extractor. |
| `reconstruction_fs` | Reconstruction coordinate rate, 500 Hz. |
| `is_original_digital_waveform` | Always `False` for this pipeline. |
| `is_fully_synchronous_12lead_10s` | Always `False` for printed sequential lead layouts. |
| `valid_intervals_seconds` | Per-lead observed intervals on the reconstruction grid. |
| `filename_lr`, `filename_hr` | Relative extension-free WFDB paths at 100 and 500 Hz. |

## Waveform files

`records500/` contains 5,000-sample, 12-lead WFDB records at 500 Hz. `records100/`
contains 1,000-sample records derived from the 500-Hz grid. Units are mV, lead order
is `I, II, III, AVR, AVL, AVF, V1, V2, V3, V4, V5, V6`, and unobserved intervals are
represented as missing samples.

`validity_masks/` contains `mask500` and `mask100` arrays aligned with the WFDB
records. A `True` entry indicates that a printed waveform segment was observed at
that coordinate.

## TRACE compatibility files

`trace_compat/full_data.npy` has shape `(record, 12, 2500)` and stores finite,
independently resampled, periodically completed and standardized lead arrays at
250 Hz. `trace_compat/valid_mask.npy` records the original observed support before
periodic completion. These arrays are compatibility inputs, not recovered native
digital recordings.

`trace_compat/ptbxl_compat_database.csv` mirrors the main metadata with the fields
needed by PTB-XL-style loaders. `trace_compat/scp_statements.csv` contains only
statement rows used by the release.
