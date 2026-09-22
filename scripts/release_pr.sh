#!/usr/bin/env bash
set -euo pipefail

if git diff --quiet; then
  echo "No pending Python release fragments."
  exit 0
fi

git config user.name github-actions[bot]
git config user.email 41898282+github-actions[bot]@users.noreply.github.com
git switch --force-create release/python
git add --all
git commit -m "chore(release): prepare Python packages"
git push --force origin HEAD:release/python

number=$(gh pr list --head release/python --state open --json number --jq '.[0].number // empty')
if [ -z "$number" ]; then
  gh pr create \
    --base main \
    --head release/python \
    --title "chore(release): prepare Python packages" \
    --body "Generated from checked protected main. This pull request prepares Python versions and changelogs; it publishes nothing."
fi
gh workflow run ci.yml --ref release/python -f base_revision="$GITHUB_SHA"
