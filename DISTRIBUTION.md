# Marketplace distribution

This repository distributes `actions/arc42-tqi/` from
[JACKT72xp/architecture-actions-public](https://github.com/JACKT72xp/architecture-actions-public).
It is an independent Git repository with a one-way subtree export, not a GitHub
fork relationship. The upstream monorepo remains the source of truth for analyzer
code, tests, dependencies, and product documentation.

## Ownership and contributions

Send analyzer issues and pull requests to the upstream repository. The README,
contribution guide, example workflow, release guide, and historical design documents receive deterministic
changes during export to describe this distribution correctly. Historical design
snapshots and the monorepo's GHCR release script are excluded. Other exported
files are identical to their upstream blobs.

`UPSTREAM.json` records the upstream commit and SHA-256 hashes of exported files.
CI rebuilds the expected export from that commit and compares the actual bytes;
editing the manifest alone cannot hide a change. Changes to `.github/`,
`DISTRIBUTION.md`, and `.gitignore` belong to this repository and are reviewed here.

## Initial setup

1. Push the recorded source commit to upstream `main` before pushing this
   repository. CI fetches the public source repository and needs that commit.
2. Push this repository's initial commit to `main` and confirm all CI jobs pass.
3. In Settings > Actions > General, enable **Allow GitHub Actions to create and
   approve pull requests** for the sync workflow. It creates PRs; it does not
   approve or merge them. No cross-repository write token is required: source
   reads are public and destination writes use this repository's `GITHUB_TOKEN`.
4. Enable private vulnerability reporting and branch protection/rulesets for
   `main`; require review and validation. Restrict release-tag updates to maintainers.
5. Confirm that the Action name is available in Marketplace and that the owner
   has accepted the GitHub Marketplace Developer Agreement.

## Synchronization

After reviewing, merging and validating changes upstream, run **Sync reviewed
upstream source** from this repository's default branch with the full upstream
commit SHA. The workflow checks that the commit belongs to upstream `main`,
exports the subtree, opens a PR, and dispatches **Validate distribution** on its
branch. Review the diff and successful workflow before merging. Workflow-token
PRs do not automatically trigger normal push/PR checks, so explicit dispatch is
intentional. If PR creation is disabled, enable it and open the PR from the
already-pushed `sync/upstream-<SHA>` branch, then dispatch validation on that branch.
If a sync branch already exists, review/reuse that PR; the workflow never force-pushes.

For a local sync with a sibling source checkout:

```sh
python3 .github/scripts/sync_upstream.py \
  --source ../architecture-actions-public --ref FULL_UPSTREAM_COMMIT_SHA
python3 .github/scripts/sync_upstream.py \
  --source ../architecture-actions-public --check
```

Only committed upstream content is exported. Local uncommitted source changes are
not included. Sync also removes previously exported files deleted upstream.
Commit and review the resulting distribution changes before releasing.

## Releases

The source `action.yml` builds the root Dockerfile. This works for consumers in
other accounts without a registry login or a prepublished container. Builds need
network access to the pinned base image and package repositories; analysis itself
is offline by default. Docker Actions require Linux runners.

1. Set the desired package version upstream, review/merge it, then synchronize.
2. Run **Prepare Marketplace release** on the distribution's default branch with
   a matching version such as `v0.1.0`.
3. The workflow verifies provenance, unit/integration tests, lint, types, wheel
   build, dependency advisories, real Action outputs, and native Linux AMD64/ARM64
   container smoke tests. It then creates a new immutable-by-process tag and a
   **draft** release. Existing tags are never overwritten by this workflow.
4. Review the release notes and add scoring/compatibility changes. In GitHub's
   release editor, select **Publish this Action to the GitHub Marketplace**,
   choose a category, accept the agreement if prompted, and publish the release.
5. Verify the listing and test its usage example from another repository.

The workflow does not accept agreements or publish the Marketplace listing.
Do not advertise `v0.1.0` until the release has actually been published. Prefer
full distribution commit SHAs in security-sensitive consumer workflows:

```yaml
- uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683
- uses: JACKT72xp/arc42-tqi-action@FULL_DISTRIBUTION_COMMIT_SHA
  with:
    docs-path: docs
    adr-path: docs/adr
```

[GitHub Marketplace publication requirements](https://docs.github.com/en/actions/how-tos/create-and-publish-actions/publish-in-github-marketplace).
