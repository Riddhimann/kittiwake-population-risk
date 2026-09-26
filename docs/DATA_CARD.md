# Dataset card

| Property | Value |
| --- | --- |
| Subject | Black-legged Kittiwake (*Rissa tridactyla*) |
| Identifier | GPDD Main ID 6633, as stated in the supplied report/file name |
| Observations | 36 |
| Time window | 1949–1984, annual |
| Fields | `SampleYear`, `Population` |
| Missing/duplicate records | None in the supplied workbook |
| Recorded range | 8–208 |
| Source provenance | User-supplied workbook attributed by the report to the Global Population Dynamics Database |
| Source URL/license | Not present in the supplied project files; must be verified before redistribution beyond this project |

The `Population` field is treated as a positive population count/index because the workbook provides no sampling-unit metadata. It should not be silently interpreted as the global abundance of the species. The series describes one historical record and ends in 1984.

The workbook is retained byte-for-byte as `data/kittiwake_gpdd_6633.xlsx`; its SHA-256 is recorded in `artifacts/metadata.json`. The loader validates numeric values, chronological ordering, uniqueness, positivity and sample size. It does not impute or interpolate observations.

Before scientific reuse, recover the GPDD record metadata, sampling location, unit, collection protocol, original citation and redistribution terms. Population viability conclusions depend on these details.

