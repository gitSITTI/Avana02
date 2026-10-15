# Keeping secrets and private names out of the repository

Two checks run before every commit and again in CI over the **whole history**.

| Check | Finds | Needs |
|---|---|---|
| gitleaks | credentials: cloud keys, tokens, private keys, passwords in code | nothing; the pinned release downloads itself, checksum verified |
| Private-term list | names you never want published: a programme, a person, an employer, a host, a part-number prefix | a list **you keep outside the repository** |

Both are wired the same way for GitHub Actions and GitLab CI, and both are covered by `tools/test_secret_guards.py`, which breaks each guard on purpose (a made-up token, a made-up private word) and checks that it fails.

## Turn it on in your clone

```bash
make hooks        # same as: python tools/setup_hooks.py
```

This points `core.hooksPath` at `.githooks/` for this clone only, and installs gitleaks 8.30.1 into `.cache/bin/` after checking its SHA-256. From then on every commit runs:

| Hook | Runs | Blocks a commit when |
|---|---|---|
| `pre-commit` | `tools/denylist_check.py staged` | a staged file, or its name, holds a term from your list |
| | `tools/check_no_real_data.py` | a requirement-export file type or a data folder is present |
| | `tools/run_gitleaks.py staged` | the staged change holds a secret |
| `commit-msg` | `tools/denylist_check.py message` | the message, or the author or committer name or email, holds a term |

If gitleaks is missing, the hook **blocks** the commit and says how to install it. A missing scanner never counts as a clean scan.

`git commit --no-verify` skips the hooks. CI runs the same checks again, so that only delays the failure.

## The private-term list

The list is the one thing that must **not** be in the repository, because it would publish the names it hides. It comes from, in order:

1. `DENYLIST_TERMS`: the terms themselves, in an environment variable (this is how a CI secret arrives)
2. `DENYLIST_FILE`: the path of a file of terms (a GitLab **File** variable, or a master copy kept elsewhere on your machine)
3. `.denylist` in the repository root (git-ignored; the real-data guard and a test refuse it if it is ever tracked)

Format: one term per line. Blank lines and lines starting with `#` are ignored.

```text
# .denylist: never commit this file
some-private-project
internal-hostname
~acme42
```

- A plain term matches case-insensitively anywhere, including inside longer words.
- A term starting with `~` ignores spaces, dots, dashes and underscores between its characters, and must start where a word starts. `~acme42` matches `ACME-42`, `Acme 42`, `acme_42` and `ACME42s`, but not `pacme42` or `acme421`. Use it for names that people write several ways.
- It reads text. Images, PDFs and other binary files are skipped, but their **file names** are checked.

What it checks, in each place it runs:

| Mode | Looks at |
|---|---|
| `staged` | staged files and their names |
| `message FILE` | the commit message, and the author and committer identity git is about to use |
| `tree` | every tracked or not-yet-ignored file and file name in the working tree |
| `history` | every commit's author, committer and message; every line added or removed in every commit; every file name; every branch and tag name |
| `ci` | `tree` and `history` together; fails when there is no list |

`history` matters: a term deleted in a later commit is still in the history, and a public repository's history is public.

**What it prints.** File and line locations such as `notes/a.md:12`. Never a term, and never the text around one. On GitHub Actions and GitLab CI it prints only a count, because the log of a public repository is public. Run `python tools/denylist_check.py tree` and `... history` on your own machine to see the places.

### One list per repository

Rules differ by repository. Keep a separate list for each:

- **Public repository:** every term, including your own name and email if they must not appear.
- **Private repository:** only the terms that must not appear *anywhere*. Your own name may be allowed there.

Keep your master copies somewhere private, since the files are not in git. A tidy way is one file per repository, with `DENYLIST_FILE` pointing at it from your shell profile or from a per-repository `git config` alias.

### Set it up in CI

**GitHub:** Settings, Secrets and variables, Actions, New repository secret, name `DENYLIST`, value the whole list. With the GitHub CLI: `gh secret set DENYLIST < .denylist`.

**GitLab:** Settings, CI/CD, Variables, type **File**, key `DENYLIST_FILE`, value the whole list.

The job **fails** when the list is missing, so a forgotten secret cannot pass as a clean scan. Only pull requests from forks, which are never given secrets, skip that one step (GitHub sets `DENYLIST_OPTIONAL` for you; on a GitLab fork or mirror with no list, set the variable `DENYLIST_OPTIONAL` to `1`).

## What gitleaks is set to

`.gitleaks.toml` extends gitleaks' built-in rules and allowlists only the lockfile. To add an exception, allowlist one path or one regex, never a folder. To upgrade, change `VERSION` and the five hashes at the top of `tools/run_gitleaks.py` (the hashes come from the release's `gitleaks_<version>_checksums.txt`). Behind a firewall, mirror the release files and set `GITLEAKS_BASE_URL`; the checksum is still checked.

## Check what is already there

```bash
make secrets      # gitleaks over every commit, then the private-term check over the tree and the history (when you have a list)
```

## If something is found

- **A secret:** revoke or rotate it first. Git history is permanent and public repositories are scraped. Then remove it from the code and load it from an environment variable. Rewriting history comes last, and it does not un-expose the secret.
- **A private term in the working tree:** remove it, and run `history` too.
- **A private term already in a public history:** treat it as exposed. Rewrite the history and force-push, and know that clones, forks and caches may already hold it.

## Limits

- It catches the terms you listed. It does not know what you forgot, and it is a safety net, not a substitute for judgement.
- Splitting a term across lines, encoding it, or putting it inside an image defeats a text search.
- The CI job in this repository has not run on GitHub or GitLab yet; each step was run locally in a clean checkout.
