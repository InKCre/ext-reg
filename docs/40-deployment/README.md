# Deployment

- [Local development](local-development.md)
- [Production Registry](production-registry.md)
- [Pull-request previews](pull-request-previews.md)

Workflow files and `Dockerfile` are executable delivery authority. These
documents own the operational intent, safety boundaries, failure behavior, and
recovery facts that those files cannot express clearly enough.

Python release intent belongs to the Registry, Toolkit or Core Runtime
`.changes/` directory and is prepared with Towncrier. Client Web Runtime release
intent belongs to `.changeset/` and is prepared with Changesets. Generated
Version PRs run the same required repository check through an explicit workflow
dispatch; package publication waits for the prepared version on protected
`main`. Registry service deployment remains an independent operation.
