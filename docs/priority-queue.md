# Priority Queue — Design

> Written by Claude (Claude Code), 2026-07-31, alongside the implementation it describes.
>
> Supersedes `expedite.md` and `expedite_simple.md`. Both contained useful halves of the
> answer but neither works alone; this document corrects the factual errors in the former
> and closes the gap in the latter. Verified against the pinned dependencies, the
> django-q2 source (v1.10.0), and the DLCS protagonist API.

## Goal

A VIP lane for PDF submissions. Processing is identical to the standard queue; the only
difference is that a priority submission must not wait behind a backlog (e.g. 100 queued
items) in either the composite-handler **or** DLCS itself. Anyone with valid credentials
may use the lane — no per-customer gating. Additional compute cost must be ~zero.

## Why the previous documents don't work as written

**`expedite.md` (Option A, `ALT_CLUSTERS`)** — two factual errors:

1. This repo pins `django-q==1.3.9` (original django-q, unmaintained since 2021).
   `ALT_CLUSTERS` does not exist in that library — it is a feature of **django-q2**, the
   maintained drop-in fork. A library migration is a prerequisite the document never
   mentions.
2. Even in django-q2, a single `qcluster` process does **not** monitor multiple queues
   with a combined worker pool. One `qcluster` process serves exactly one cluster; an
   alternate cluster is a *separate process*, selected at startup via the
   `Q_CLUSTER_NAME` environment variable (`django_q/conf.py`; docs "Multiple Queues").
   `ALT_CLUSTERS` is only a dict of per-cluster config overrides keyed by that name.

So Option A quietly collapses into the "two processes" shape of Option B. That is still
cheap (see [Cost](#cost)) — but the design below is written around how the library
actually behaves.

**`expedite_simple.md` (DLCS `/queue/priority` only)** — solves half the problem. It
routes the *DLCS ingest step* to DLCS's priority queue but changes nothing about the
composite-handler's own queue. In the motivating scenario (100 items queued locally), a
priority submission still waits behind 100 fetch/rasterize/upload jobs before the DLCS
call ever happens. However, its plumbing (URL shape, `priority` flag on `Collection`,
pass-through to `dlcs.ingest`) is needed regardless, because DLCS has its own queue that
can also back up.

## Design

Two complementary halves, one submission flag:

1. **Local VIP lane** — a second queue with a small dedicated worker pool, so priority
   tasks skip the composite-handler backlog. Implemented with django-q2 `ALT_CLUSTERS`
   plus a second `qcluster` process inside the **existing** engine containers.
2. **DLCS VIP lane** — priority submissions are ingested via
   `POST /customers/{customer}/queue/priority` (verified present in protagonist's
   `CustomerQueueController`: *"The processing is the same but the priority queue is for
   images that need to be processed quickly"*), so they also skip any DLCS-side backlog.

### API surface

```
POST /customers/{customer}/queue            → standard (unchanged)
POST /customers/{customer}/queue/priority   → VIP lane
```

Same request body, same auth, same response shape. Mirroring DLCS's own URL scheme keeps
the composite-handler a faithful proxy of DLCS semantics (RFC011) and makes priority use
auditable in access logs. No header or schema change needed.

### Routing mechanics (verified against django-q2 v1.10.0 source)

- `async_task(..., cluster=<name>)` → `get_broker(<name>)` → for the SQS broker,
  `<name>` **is the SQS queue name** (`brokers/__init__.py`: `list_key` ==
  queue name; `tasks.py`: `get_broker(task.get("cluster"))`).
- A worker process started with `Q_CLUSTER_NAME=<name>` merges
  `ALT_CLUSTERS[<name>]` over the root `Q_CLUSTER` config and consumes from queue
  `<name>` (`conf.py`: `CLUSTER_NAME = conf.get("cluster_name", PREFIX)`).
- With the ORM broker (local dev without SQS), the same `cluster=<name>` value keys rows
  in the `OrmQ` table and routing works identically — no SQS required for dev/tests.
- `cluster=None` routes to the default cluster, i.e. today's behaviour.

### Graceful degradation

If `PRIORITY_QUEUE_NAME` is not configured, priority submissions are accepted, enqueue to
the **standard** local queue, and still ingest via DLCS `/queue/priority`. This makes the
rollout safe (API can deploy before engine/infra) and keeps the DLCS half working even if
the local lane is ever disabled.

## Changes

### 0. Prerequisite: migrate `django-q` → `django-q2` (standalone step)

- `src/requirements.txt`: replace `django-q==1.3.9` with `django-q2==1.10.0`
  (same `django_q` import path and `INSTALLED_APPS` entry — no code changes;
  pulls in `django-picklefield`; supports Django ≥4.2, Python 3.9–3.13).
- `python manage.py migrate` — django-q2 ships additional `django_q` migrations
  (already run by `entrypoint.sh` when `MIGRATE=True`).
- **Ship and deploy this alone first.** It swaps an unmaintained 2021 library running
  against Django 4.2 for the maintained fork — worth doing even without this feature —
  and isolates the riskiest change so any fallout is unambiguous.

### 1. Settings — `src/app/settings.py`

```python
PRIORITY_QUEUE_NAME = env.str("PRIORITY_QUEUE_NAME", default="")

if PRIORITY_QUEUE_NAME:
    Q_CLUSTER["ALT_CLUSTERS"] = {
        PRIORITY_QUEUE_NAME: {
            "workers": env("PRIORITY_WORKER_COUNT", cast=int, default=1),
        },
    }
```

The alt cluster inherits everything else (timeout, retry, max_attempts, broker choice)
from the root `Q_CLUSTER`. With SQS in use, `PRIORITY_QUEUE_NAME` must equal the name of
a real SQS queue (to be created in infra, mirroring the standard one).

### 2. Model — `src/app/common/models.py` (+ migration)

```python
class Collection(models.Model):
    ...
    priority = models.BooleanField(default=False)
```

`CollectionSerializer` needs **no change** — it uses `fields = "__all__"`.

### 3. URLs — `src/app/api/urls.py`

```python
path("customers/<int:customer>/queue", CollectionAPIView.as_view()),
path("customers/<int:customer>/queue/priority", CollectionAPIView.as_view(priority=True)),
```

### 4. View — `src/app/api/views.py`

```python
class CollectionAPIView(AbstractAPIView):
    priority = False

    def post(self, request, *args, **kwargs):
        ...
        serializer = CollectionSerializer(
            data={
                "json_data": request.data,
                "customer": kwargs["customer"],
                "priority": self.priority,
            }
        )
        ...
        for serializer in serializers:
            member = serializer.save()
            async_task(
                "app.engine.tasks.process_member",
                {"id": member.id, "auth": request.headers["Authorization"]},
                task_name=f"Submission: [{member.id}]",
                cluster=settings.PRIORITY_QUEUE_NAME or None if self.priority else None,
            )
```

Optionally include `"priority": collection.priority` in
`_build_collection_response_body` for observability.

### 5. DLCS client — `src/app/common/dlcs.py`

```python
def ingest(self, customer, json, auth, priority=False):
    endpoint = "queue/priority" if priority else "queue"
    response = requests.post(
        f"{self._api_root}customers/{customer}/{endpoint}",
        ...
    )
```

### 6. Engine task — `src/app/engine/tasks.py`

`__initiate_dlcs_ingest` passes `priority=member.collection.priority` to `dlcs.ingest`.

### 7. Worker entrypoint — `entrypoints/entrypoint-worker.sh`

Run both clusters in the existing engine container; exit (→ container restart) if either
dies. Behaviour is unchanged when `PRIORITY_QUEUE_NAME` is unset:

```bash
bash entrypoint.sh

if [[ -n "$PRIORITY_QUEUE_NAME" ]]; then
  python manage.py qcluster &
  Q_CLUSTER_NAME="$PRIORITY_QUEUE_NAME" python manage.py qcluster &
  wait -n
  exit 1
else
  python manage.py qcluster
fi
```

### 8. Config templates & docs

- `.env.dist`: add `PRIORITY_QUEUE_NAME=` (blank = disabled) and
  `PRIORITY_WORKER_COUNT=1` under the Django Q section.
- `README.md`: document the endpoint, the two env vars, and the SQS queue requirement.

### Infrastructure (outside this repo)

- One new SQS queue, named to match `PRIORITY_QUEUE_NAME`, same settings as the standard
  queue (visibility timeout must remain ≥ `ENGINE_WORKER_RETRY`).
- Set `PRIORITY_QUEUE_NAME` / `PRIORITY_WORKER_COUNT` on the engine and API services.
- **No new instances, services, or replicas.**

## Cost

The marginal footprint is one extra `qcluster` process group per engine instance
(sentinel + 1 worker + monitor + pusher — a few hundred MB RAM, ~zero CPU while idle).
Idle priority workers do not lend capacity to the standard queue; that is the point —
they are always free when a VIP job lands. When a VIP job runs it shares the instance's
CPU with standard rasterization work, which is acceptable: the problem being solved is
*queue wait* (hours behind a backlog), not execution speed.

If even that idle footprint must go, the same code supports a scale-from-zero deployment
(a separate engine service running only the priority cluster, autoscaled 0→1 on SQS queue
depth). That is purely a deployment change — not designed here, and not recommended as a
starting point.

## Testing

Integration tests (`src/tests/`, pytest-docker, ORM broker):

- `POST /customers/{c}/queue/priority` returns 202, persists `Collection.priority=True`,
  and reports `"priority": true` in the response; the standard endpoint reports `false`.
- Existing suite must pass unchanged after the django-q2 swap (step 0).
- The `dlcs.ingest` endpoint switch has no automated coverage (the test stack runs no
  engine); it is verified by inspection/mock — see implementation notes below.

Note: the test stack's `docker-compose.yml` referenced a `Dockerfile.CompositeHandler`
that never existed in this repo (a leftover from the protagonist monorepo import), so the
integration tests were unrunnable as imported. Fixed as part of this work: the compose
file now builds the root `Dockerfile` and supplies the required env vars, and
`pytest-docker` is bumped to a version that uses Docker Compose v2.

## Rollout order

1. **PR 1**: django-q2 migration only. Deploy, soak.
2. **Infra**: create the priority SQS queue.
3. **PR 2**: everything else. Deployable before or after the env vars are set — the
   feature is inert until `PRIORITY_QUEUE_NAME` is configured, and priority submissions
   degrade gracefully (standard local queue + DLCS priority ingest) in the meantime.

## Decisions & open items

- **Access control**: none — any authenticated caller may use the lane (matches DLCS's
  own priority queue). If abuse ever makes the VIP queue back up, per-customer gating can
  be added at the view layer later.
- **Priority worker count**: default 1 per engine instance (3 with the current 3
  replicas). Tune via `PRIORITY_WORKER_COUNT` only if VIP volume grows.
- **In-flight work is not preempted**: a VIP job skips the queue but still waits for a
  free priority worker; with `workers: 1` per instance, concurrent VIP jobs queue behind
  each other. Acceptable for the stated "rare, needed by CoP" use case.
