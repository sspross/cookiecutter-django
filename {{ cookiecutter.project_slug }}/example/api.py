"""HTTP edge for the `example` app.

The api module exports a Ninja `Router` and stays thin: deserialize,
dispatch to selector or service, serialize. All read-side logic lives in
`selectors`; all write-side logic lives in `services`. Validation errors
from `full_clean` are translated to 422 by the global handler in
`core.api`.

CSRF: GETs are unprotected (idempotent reads). Mutations are wrapped with
`csrf_protect_route` so Django's CSRF check runs on POST/PATCH/DELETE.
"""

from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate
from ninja.responses import Status

from core.csrf import csrf_protect_route
from example import selectors, services
from example.filters import ProjectFilters, TagFilters, TaskFilters
from example.models import Project, Tag, Task
from example.schemas import (
    ProjectIn,
    ProjectOut,
    ProjectPatch,
    TagIn,
    TagOut,
    TagPatch,
    TaskIn,
    TaskOut,
    TaskPatch,
)

router = Router()


@router.get("/tags", response=list[TagOut], tags=["tags"])
@paginate(LimitOffsetPagination)
def list_tags(request, filters: Query[TagFilters]):
    return selectors.list_tags(filters=filters)


@router.get("/tags/{tag_id}", response=TagOut, tags=["tags"])
def get_tag(request, tag_id: int) -> Tag:
    return get_object_or_404(Tag, pk=tag_id)


@router.post("/tags", response={201: TagOut}, tags=["tags"])
@csrf_protect_route
def create_tag(request, payload: TagIn):
    tag = services.create_tag(**payload.dict())
    return Status(201, tag)


@router.patch("/tags/{tag_id}", response=TagOut, tags=["tags"])
@csrf_protect_route
def update_tag(request, tag_id: int, payload: TagPatch) -> Tag:
    tag = get_object_or_404(Tag, pk=tag_id)
    return services.update_tag(tag=tag, **payload.dict(exclude_unset=True))


@router.delete("/tags/{tag_id}", response={204: None}, tags=["tags"])
@csrf_protect_route
def delete_tag(request, tag_id: int):
    tag = get_object_or_404(Tag, pk=tag_id)
    services.delete_tag(tag=tag)
    return Status(204, None)


# --- Projects --------------------------------------------------------------


@router.get("/projects", response=list[ProjectOut], tags=["projects"])
@paginate(LimitOffsetPagination)
def list_projects(request, filters: Query[ProjectFilters]):
    return selectors.list_projects(filters=filters)


@router.get("/projects/{project_id}", response=ProjectOut, tags=["projects"])
def get_project(request, project_id: int) -> Project:
    return get_object_or_404(
        Project.objects.prefetch_related("tags"), pk=project_id
    )


@router.post("/projects", response={201: ProjectOut}, tags=["projects"])
@csrf_protect_route
def create_project(request, payload: ProjectIn):
    project = services.create_project(**payload.dict())
    return Status(201, project)


@router.patch(
    "/projects/{project_id}", response=ProjectOut, tags=["projects"]
)
@csrf_protect_route
def update_project(request, project_id: int, payload: ProjectPatch) -> Project:
    project = get_object_or_404(Project, pk=project_id)
    return services.update_project(
        project=project, **payload.dict(exclude_unset=True)
    )


@router.delete(
    "/projects/{project_id}", response={204: None}, tags=["projects"]
)
@csrf_protect_route
def delete_project(request, project_id: int):
    project = get_object_or_404(Project, pk=project_id)
    services.delete_project(project=project)
    return Status(204, None)


# --- Tasks -----------------------------------------------------------------


@router.get("/tasks", response=list[TaskOut], tags=["tasks"])
@paginate(LimitOffsetPagination)
def list_tasks(request, filters: Query[TaskFilters]):
    return selectors.list_tasks(filters=filters)


@router.get("/tasks/{task_id}", response=TaskOut, tags=["tasks"])
def get_task(request, task_id: int) -> Task:
    return get_object_or_404(Task, pk=task_id)


@router.post("/tasks", response={201: TaskOut}, tags=["tasks"])
@csrf_protect_route
def create_task(request, payload: TaskIn):
    task = services.create_task(**payload.dict())
    return Status(201, task)


@router.patch("/tasks/{task_id}", response=TaskOut, tags=["tasks"])
@csrf_protect_route
def update_task(request, task_id: int, payload: TaskPatch) -> Task:
    task = get_object_or_404(Task, pk=task_id)
    return services.update_task(task=task, **payload.dict(exclude_unset=True))


@router.delete("/tasks/{task_id}", response={204: None}, tags=["tasks"])
@csrf_protect_route
def delete_task(request, task_id: int):
    task = get_object_or_404(Task, pk=task_id)
    services.delete_task(task=task)
    return Status(204, None)
