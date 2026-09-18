# `docker/`

Reserved for shared/infra-level Docker assets that aren't specific to
either app — e.g. a shared base image, an Nginx reverse-proxy config for
production, or Postgres init scripts.

Each app's own Dockerfile lives with that app (`frontend/Dockerfile`,
`backend/Dockerfile`), since a Dockerfile needs to sit next to what it
builds. This folder is for things that sit *above* both of them.

Empty for now, by design — `docker-compose.yml` at the repo root is
enough for Phase 1's local dev / single-command setup.
