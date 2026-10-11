# Approved real-data fixtures

This is the ONLY place a real (or real-derived) requirements export may be committed.

Rules:

1. Only files that your security / export-control reviewer has approved for this repository, **after anonymising**.
2. Each file must be named in `APPROVALS.md` with: who approved it, the date, and the ticket or record.
   CI (`guard:no-real-data`) fails if a file here is not named there.
3. Prefer small excerpts (a few dozen requirements) that still show the awkward parts of the real format.
4. Never put the real export anywhere else in the repo. The guard refuses `.reqif`, `.mdzip`, `.sysml`, `.kpar`, `.xlsx`, `.csv`, `.docx`, `.pdf`, `.db` and similar anywhere outside this folder.

If you are unsure whether a file is allowed, it is not. Ask first.
