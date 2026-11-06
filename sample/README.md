# ECG conversion sample

This directory contains four de-identified records selected to cover the EDAN, PSCRIPT, PSCRIPT_BUNDLE and MUSE layout families. It is a loader and smoke-test sample, not a replacement for the complete source release.

The sample preserves a PTB-XL-compatible metadata schema with generic opaque IDs. Waveforms are vector-reconstructed lead segments; they are not native digital 12-lead recordings.

```python
import pandas as pd
import wfdb
from pathlib import Path

root = Path('sample')
meta = pd.read_csv(root / 'ecg_database.csv')
signal, fields = wfdb.rdsamp(str(root / meta.iloc[0].filename_hr))
print(signal.shape, fields['fs'], fields['sig_name'])
```

The example data retain the source release's data terms; see `LICENSE_DATA.txt`. The processing code is MIT-licensed.
