# Security policy

This is a research prototype (read "What has and has not been checked" in the [README](README.md) first). There are no releases and no supported-version table: fixes go to the default branch.

## Reporting a vulnerability

Please report privately, not in a public issue.

1. On the repository's **Security** tab, choose **Report a vulnerability**. This is GitHub's private channel. If the button is not there, the maintainer has not switched it on yet.
2. If you cannot use it, open a public issue that says only that you have a security report, with no details, and ask for a private way to send it.

No response time is promised. Say what you saw, what you expected, and how to reproduce it with **made-up data**.

## What counts as a vulnerability

`reqin` makes these promises about connectors ([`reqin/CONNECTORS.md`](reqin/CONNECTORS.md) lists them, and each has a test). A way to break one is a vulnerability:

- **Read-only.** A connector sends only `GET`. Nothing writes to a source system.
- **TLS is always verified.** There is no switch to turn it off.
- **Secrets stay out of the output.** Credentials come from environment variables, and their values are scrubbed from errors and from the audit log.
- **No credential forwarding.** A redirect to another host, or from https to http, is refused.

Also welcome:

- The real-data guard (`tools/check_no_real_data.py`) letting through a file type it should refuse. It is a tripwire for honest mistakes, not a guarantee, and a person still decides what is sensitive.
- A crafted input file (ReqIF, SysML v2 JSON, Excel, CSV, Word or PDF) that makes an importer run code, read or write files you did not name, or use unbounded memory. The importers read files from other tools, but they are **not claimed to be hardened against hostile files**, and no fuzzing or dedicated review has been reported in the README.

## Known limits (reports about these are bug reports, not vulnerabilities)

- No connector has been run against a real MSOSA, Teamwork Cloud, DOORS, DOORS Next or Agility system. Differences from the fake servers in the tests are expected to turn up.
- The DOORS script (`reqin/connectors/doors9/export_requirements.dxl`) has never run in DOORS.
- OAuth and form sign-in are not built. Credentials are a token, basic authentication or a cookie from an environment variable, or your own `auth_hook`.
- The clickable prototype (`prototype/`) is a single page with made-up data and no server part. Opened with network access it requests IBM Plex fonts from Google Fonts. No requirement data is sent, but the request does tell Google the page was opened. Offline it works with the browser's own fonts.
- The `Containerfile` has not been built, and neither CI file (`.github/workflows/ci.yml`, `.gitlab-ci.yml`) has run on its platform yet.

## If you find real program data in this repository

Do not repost it and do not quote it in an issue or pull request. Requirements for aerospace and defence programs can be export-controlled, and quoting them spreads the problem. Report it privately as above, naming the file and line only, so the maintainer can remove it and clean the history.

## Handling secrets in the project's own CI

The only secret the GitHub workflow can read is the optional `FORBIDDEN_TERMS` (a list of patterns for the guard to scan for; keep it out of the repository). Pull requests from forks do not receive it. The workflow's token is read-only and the workflow never uses `pull_request_target`; `tools/test_workflows.py` checks both.
