# Privacy and de-identification boundaries

The processing pipeline is intended for authorised institutional use with a
source-specific governance approval. It separates public outputs from a protected
linkage workspace.

## Public output

The public package excludes source PDFs, direct identifiers, source filenames,
exact dates, clinician names, document metadata, the private HMAC key and the
source-to-public mapping. Public patient and record identifiers are opaque. Numeric
ages at or above 90 are suppressed. Diagnosis-region text is retained only when
allowed by the source data governance and after identifier-pattern checks.

## Private workspace

The private root may contain the HMAC secret, source paths, source hashes and local
identifiers. It must remain outside public archives and source-control repositories.
The build script creates private checkpoints separately from public records.

## Scope limits

Pattern scans reduce common direct-identifier leakage but do not prove irreversible
anonymisation or eliminate linkage risk from unusual clinical text and demographic
combinations. Every source dataset requires an independent privacy, ethics and
licensing review before redistribution.

The vector reconstruction itself does not create a new clinical acquisition. It
represents printed lead paths and preserves missing intervals; downstream users
must not interpret periodic completion as recovered physiology.
