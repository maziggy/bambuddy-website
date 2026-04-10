# Contributing to the Bambuddy Website

This repo is the source for <https://bambuddy.cool> — plain HTML, CSS,
JavaScript, and static assets. There is no build step: what you see in
the repo is exactly what gets deployed.

## Quick edits

The HTML files here are **large** — `features.html` is over 130 KB,
`index.html` around 40 KB. GitHub's pencil icon works, but gets laggy
and awkward on files that size. **Use github.dev instead** for anything
non-trivial:

1. Navigate to <https://github.com/maziggy/bambuddy-website>
2. Press `.` (period) — VS Code opens in your browser with the full
   file tree, syntax highlighting, multi-cursor, find-and-replace,
   and a Source Control panel.
3. Edit the file(s) you want to change.
4. Open the **Source Control** panel (left sidebar, branch icon) —
   stage your changes, write a commit message, click **Commit & Push**.
5. github.dev will prompt you to create a branch (direct pushes to
   `main` are blocked). Accept the default name or customize it.
6. Switch back to github.com, open the repo, and you'll see a banner
   offering to open a PR from the new branch. Click it.

For tiny edits on small files (e.g. fixing a typo in `robots.txt`),
the pencil icon on github.com is fine.

## Preview before merging

[Cloudflare Pages](https://pages.cloudflare.com/) builds every PR
branch automatically. Because there's no build step, previews are
fast — usually ready within ~10 seconds of pushing.

1. Within a few seconds of opening the PR, a GitHub check appears:
   `Cloudflare Pages — Deploying...` (yellow dot).
2. The check turns green and `cloudflare-pages[bot]` posts a comment
   with a preview URL like
   `https://<branch>.bambuddy-website.pages.dev/`.
3. Click the URL — you'll see the entire site with your changes
   applied, exactly as it will look in production.

### What to check in the preview

- Does your edit render correctly on the page you changed?
- Is the responsive layout still working on **mobile** and **desktop**?
  (Use DevTools → responsive mode, or actually open it on your phone.)
- Do external links still resolve?
- No visual regressions on adjacent or linked pages?
- Are images, fonts, and stylesheets loading (no 404s in the browser
  console)?

If everything looks good on the preview, a maintainer will review and
merge. If the preview is broken, push more commits to the same branch
— the preview auto-rebuilds on each push.

## What goes here vs. in the wiki

- **Marketing copy, feature claims, download buttons, screenshots on
  the landing page, legal pages** → this repo (bambuddy-website)
- **User documentation, installation guides, feature walkthroughs,
  reference material** → [bambuddy-wiki](https://github.com/maziggy/bambuddy-wiki)

If in doubt, start with the wiki — it's easier to edit (Markdown
instead of HTML) and better integrated with search.

## Reporting issues or requesting changes

If you'd rather flag a problem without fixing it yourself, open an
issue at
[maziggy/bambuddy/issues](https://github.com/maziggy/bambuddy/issues)
and apply the `website` label. We use the main repo's issue tracker
for everything — this repo doesn't track its own issues.

## Copy changes tied to feature changes in the app

If you're updating the website because a feature in the main
[bambuddy](https://github.com/maziggy/bambuddy) repo changed (new
feature in the comparison table, new screenshot, updated version
number), open both PRs in parallel and link them to each other. See
the main repo's
[CONTRIBUTING.md](https://github.com/maziggy/bambuddy/blob/main/CONTRIBUTING.md#documentation-requirements)
for the full rules.
