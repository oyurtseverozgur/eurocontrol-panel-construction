# Data

`raw/` holds the 17 annual EUROCONTROL files `co2_emmissions_by_state_2010.csv` ... `_2026.csv`
(CO2 emissions by State, Small Emitters Tool), downloaded on 4 July 2026 from
https://ansperformance.eu/reference/dataset/emissions/ .

Source: EUROCONTROL, Aviation Intelligence Portal. The files are reproduced unchanged, with attribution,
so that the published results can be reproduced exactly; the portal is updated monthly and a later
download will not give the same record counts. `raw/SHA256SUMS.txt` lists the hash of every file;
`analysis.py` refuses to run if any file differs. The 2026 file covers January to May only.
