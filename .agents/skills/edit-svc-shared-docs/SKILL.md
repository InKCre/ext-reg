---
name: edit-svc-shared-docs
description: Thin discovery wrapper for the canonical InKCre shared-doc workflow in `docs/_shared/00-meta/skills/edit-svc-shared-docs`. Use when changing Hub truth or the local shared reference.
---

# Edit InKCre Shared Docs

This file is discovery-only. The canonical workflow belongs to `InKCre/docs`.

Before changing shared truth or `docs/_shared`:

1. initialize the mount with `git submodule update --init --recursive docs/_shared` when needed
2. read [the canonical skill](../../../docs/_shared/00-meta/skills/edit-svc-shared-docs/SKILL.md)
3. follow its Hub-first commit/push and isolated Spoke-ref workflow

Do not copy or extend the canonical workflow here. Never edit `docs/_shared/**`
from the Spoke context.
