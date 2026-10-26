# E4D QR label tools (locked layout, approved by Noah 27 Oct 2026)

Do not change the label layout. Same steps for every job:

1. `python3 extract.py "<job>/Room1.des" job.json` → 3D data for the page. Add keys: c{product}-p{part}, plus mz = R1C#/R1N#.
2. Build the page from `template.html` (replace `__DATA__`) → `<job-folder>/index.html` in this repo.
3. `python3 labels3.py "<Material>" ...` (set URL to the job's page) → 100×73 labels from the saved .opt files: sheet layout, part drawing with holes and edging, QR, Sheet#/Part#.
4. Check that every QR decodes to its own part, then push.
