# README connection positioning evidence

PR implementation changes only README.md and README.en.md. This separate evidence branch is not intended to merge.

Tool: bmdy6/skill-readme-from-code main at 7a9f5d7c7f7c0082bbfad70234c9f8f1c19e3cc4.
Baseline target: cbd92cc55396ca8b2541fb88315176d8bc94b539.

Both before and after: `node scripts/run.mjs audit --repo <repo> --work <phase> --brief audit-config.json --online`.
The same brief specifies the existing gh clone command and bilingual output keywords; it does not change budget or suppress failures.
`before-default` retains the initial unconfigured audit, whose installation detector did not recognize gh repo clone.
`before` and `after` are the comparable configured audits (67/100 each).
V3/V7 pass; V5 failures are identical; V6 only has the existing word budget failure (508 → 503).

Screens use GitHub Markdown API HTML and the audit tool's Chromium renderer: 1280×800 desktop with 838px content and 72px header reserve, light/dark; 390×844 mobile informational. No live GitHub browser UI acceptance is claimed. All hero images loaded. English screenshots use the same exported firstScreen renderer with README.en.md (baseline via git show, after via file read).

Raw local reports are retained by the executor. Public JSON copies replace absolute repository paths with <repo> or repo://skill-bot-keepalive; check results and measurements are unchanged. PNGs are copied byte-for-byte.

The runtime keepalive/network commands were not executed: this is a documentation-only change, not a new cloud, quota or disconnect-recovery measurement. Existing performance tables and command blocks are byte-identical.
