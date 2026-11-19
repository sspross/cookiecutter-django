# Async runtime ships by default

Every generated project carries django-rq, a Redis service and a `worker`
process in each deployment manifest, but no jobs. Most projects end up needing
background work, and retrofitting a runtime touches `INSTALLED_APPS`, the
settings, every manifest and CI, which costs more than carrying it from day
one. RQ over Celery: one broker instead of a broker plus a result backend.

The cost is a Redis dependency, and a few manifest lines, in projects that
never write a job.

How to add a job: `docs/ARCHITECTURE.md` "Background jobs".
