import ast
from collections.abc import Iterable
from importlib import import_module
from pathlib import Path
from typing import Any

from django.apps import AppConfig, apps
from django.conf import settings
from django.db import models
from django.test.utils import isolate_apps
from ninja import ModelSchema, Schema

INVENTED_SOFT_DELETE_NAMES = frozenset(
    {
        "archived_at",
        "removed_at",
        "trashed_at",
        "is_archived",
        "is_removed",
        "is_trashed",
    }
)
SOFT_DELETE_TIMESTAMP_TO_FLAG = {"revoked_at": "is_revoked", "deleted_at": "is_deleted"}
SOFT_DELETE_NAMES_AND_VISIBILITY = (
    "Use revoked_at / is_revoked to keep the row listed with a revoked badge, "
    "or deleted_at / is_deleted to hide it from every user-facing read."
)


def soft_delete_violations(model_classes: Iterable[type[models.Model]]) -> list[str]:
    violations: list[str] = []
    for model in model_classes:
        fields_by_name = {field.name: field for field in model._meta.get_fields()}
        violations.extend(
            f"{model.__name__}.{name}: soft-delete has two names. "
            f"{SOFT_DELETE_NAMES_AND_VISIBILITY}"
            for name in sorted(INVENTED_SOFT_DELETE_NAMES)
            if hasattr(model, name)
        )
        for timestamp, flag in SOFT_DELETE_TIMESTAMP_TO_FLAG.items():
            field = fields_by_name.get(timestamp)
            if field is None:
                continue
            if not (isinstance(field, models.DateTimeField) and field.null):
                violations.append(
                    f"{model.__name__}.{timestamp}: make it "
                    "models.DateTimeField(null=True, blank=True); "
                    "None means the row is live."
                )
            if not isinstance(getattr(model, flag, None), property):
                violations.append(
                    f"{model.__name__}.{timestamp}: add an {flag} @property "
                    f"that returns {timestamp} is not None."
                )
    return violations


def choices_class_name(field: models.Field[Any, Any]) -> str:
    model = field.model
    for name, value in vars(model).items():
        if (
            isinstance(value, type)
            and issubclass(value, models.Choices)
            and value.choices == field.choices
        ):
            return f"{model.__name__}.{name}"
    return f"the TextChoices class of {model.__name__}.{field.name}"


def is_bare_str(annotation: object) -> bool:
    return annotation is str or annotation == (str | None)


def choices_fields_by_name(
    model_classes: Iterable[type[models.Model]],
) -> dict[str, list[models.Field[Any, Any]]]:
    by_name: dict[str, list[models.Field[Any, Any]]] = {}
    for model in model_classes:
        for field in model._meta.get_fields():
            if isinstance(field, models.Field) and field.choices:
                by_name.setdefault(field.name, []).append(field)
    return by_name


def model_of(schema: type[ModelSchema]) -> type[models.Model]:
    model = schema.Meta.model  # type: ignore[attr-defined]
    return apps.get_model(model) if isinstance(model, str) else model


def app_label_of(schema: type[Schema]) -> str | None:
    app = apps.get_containing_app_config(schema.__module__)
    return app.label if app else None


def models_a_schema_can_mirror(
    schema: type[Schema], model_classes: Iterable[type[models.Model]]
) -> list[type[models.Model]]:
    if issubclass(schema, ModelSchema):
        return [model_of(schema)]
    app_label = app_label_of(schema)
    return [model for model in model_classes if model._meta.app_label == app_label]


def choices_schema_violations(
    model_classes: Iterable[type[models.Model]],
    schema_classes: Iterable[type[Schema]],
) -> list[str]:
    all_models = list(model_classes)
    violations: list[str] = []
    for schema in schema_classes:
        choices_fields = choices_fields_by_name(
            models_a_schema_can_mirror(schema, all_models)
        )
        for name, schema_field in schema.model_fields.items():
            if not is_bare_str(schema_field.annotation):
                continue
            violations.extend(
                f"{schema.__name__}.{name}: {field.model.__name__}.{name} has choices. "
                f"Type it as {choices_class_name(field)} so the generated TS "
                "is a union, not string."
                for field in choices_fields.get(name, [])
            )
    return violations


def collected_test_names(module: ast.Module) -> list[str]:
    names = []
    for node in module.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            names.append(node.name)
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            names.extend(
                method.name
                for method in node.body
                if isinstance(method, ast.FunctionDef | ast.AsyncFunctionDef)
            )
    return [name for name in names if name.startswith("test")]


def live_journey_violations(live_test_files: Iterable[Path]) -> list[str]:
    test_names = [
        name
        for path in live_test_files
        for name in collected_test_names(ast.parse(path.read_text()))
    ]
    if len(test_names) <= 1:
        return []
    return [
        f"Found {len(test_names)} live test functions: {', '.join(test_names)}. "
        "Keep one journey: extend the existing one with a step, and put anything "
        "reachable from client into tests/test_*.py."
    ]


def project_app_configs() -> list[AppConfig]:
    return [
        app
        for app in apps.get_app_configs()
        if Path(app.path).parent == settings.BASE_DIR
    ]


def project_models() -> list[type[models.Model]]:
    return [model for app in project_app_configs() for model in app.get_models()]


def all_subclasses(cls: type[Schema]) -> list[type[Schema]]:
    return [
        found
        for subclass in cls.__subclasses__()
        for found in [subclass, *all_subclasses(subclass)]
    ]


def import_every_schema_through_the_urlconf() -> None:
    import_module(settings.ROOT_URLCONF)


def project_schemas() -> list[type[Schema]]:
    import_every_schema_through_the_urlconf()
    app_names = {app.name for app in project_app_configs()}
    return [
        schema
        for schema in all_subclasses(Schema)
        if schema.__module__.split(".")[0] in app_names
        and ".tests" not in schema.__module__
    ]


def project_live_test_files() -> list[Path]:
    return sorted(Path(settings.BASE_DIR).glob("*/tests/live/**/*.py"))


def test_project_schemas_type_choices_fields_with_their_choices_class() -> None:
    assert choices_schema_violations(project_models(), project_schemas()) == []


def test_project_schemas_are_found_so_the_check_cannot_pass_empty() -> None:
    assert {schema.__name__ for schema in project_schemas()} >= {"ApiKeyOut"}


def test_project_has_one_live_journey() -> None:
    assert live_journey_violations(project_live_test_files()) == []


def test_project_live_journey_is_found_so_the_check_cannot_pass_empty() -> None:
    assert project_live_test_files() != []


def test_project_models_use_the_two_soft_delete_names() -> None:
    assert soft_delete_violations(project_models()) == []


def test_project_models_are_found_so_the_checks_cannot_pass_empty() -> None:
    assert {model.__name__ for model in project_models()} >= {"User", "UserApiKey"}


def test_live_tests_reject_a_second_journey_but_not_a_nested_helper(
    tmp_path: Path,
) -> None:
    first = tmp_path / "test_journey.py"
    first.write_text(
        "def test_journey(page, live_server):\n"
        "    def test_looking_helper():\n"
        "        pass\n"
    )
    second = tmp_path / "settings_test.py"
    second.write_text(
        "class TestSettings:\n    def test_settings_page(self, page):\n        pass\n"
    )

    assert live_journey_violations([first, second]) == [
        "Found 2 live test functions: test_journey, test_settings_page. Keep one "
        "journey: extend the existing one with a step, and put anything reachable "
        "from client into tests/test_*.py."
    ]


@isolate_apps("core")
def test_schema_rejects_str_for_a_choices_field() -> None:
    class Invoice(models.Model):  # noqa: DJ008
        class Status(models.TextChoices):
            DRAFT = "draft"
            PAID = "paid"

        status = models.CharField(max_length=8, choices=Status.choices)

        class Meta:
            app_label = "core"

    class InvoiceOut(Schema):
        __module__ = "core.schemas"

        status: str

    class InvoicePatchIn(Schema):
        __module__ = "core.schemas"

        status: str | None = None

    assert choices_schema_violations([Invoice], [InvoiceOut, InvoicePatchIn]) == [
        "InvoiceOut.status: Invoice.status has choices. Type it as Invoice.Status "
        "so the generated TS is a union, not string.",
        "InvoicePatchIn.status: Invoice.status has choices. Type it as "
        "Invoice.Status so the generated TS is a union, not string.",
    ]


@isolate_apps("core")
def test_schema_names_every_model_of_its_app_sharing_the_choices_field_name() -> None:
    class Invoice(models.Model):  # noqa: DJ008
        class Status(models.TextChoices):
            DRAFT = "draft"
            PAID = "paid"

        status = models.CharField(max_length=8, choices=Status.choices)

        class Meta:
            app_label = "core"

    class Shipment(models.Model):  # noqa: DJ008
        class Status(models.TextChoices):
            PACKED = "packed"
            SENT = "sent"

        status = models.CharField(max_length=8, choices=Status.choices)

        class Meta:
            app_label = "core"

    class StatusOut(Schema):
        __module__ = "core.schemas"

        status: str

    assert choices_schema_violations([Invoice, Shipment], [StatusOut]) == [
        "StatusOut.status: Invoice.status has choices. Type it as Invoice.Status "
        "so the generated TS is a union, not string.",
        "StatusOut.status: Shipment.status has choices. Type it as Shipment.Status "
        "so the generated TS is a union, not string.",
    ]


@isolate_apps("core")
def test_model_schema_is_checked_against_its_own_model_only() -> None:
    class Invoice(models.Model):  # noqa: DJ008
        class Status(models.TextChoices):
            DRAFT = "draft"
            PAID = "paid"

        status = models.CharField(max_length=8, choices=Status.choices)

        class Meta:
            app_label = "core"

    class Shipment(models.Model):  # noqa: DJ008
        class Status(models.TextChoices):
            PACKED = "packed"
            SENT = "sent"

        status = models.CharField(max_length=8, choices=Status.choices)

        class Meta:
            app_label = "core"

    class FreeTextStatusNote(models.Model):  # noqa: DJ008
        status = models.CharField(max_length=8)

        class Meta:
            app_label = "core"

    class ShipmentOut(ModelSchema):
        class Meta:
            model = Shipment
            fields = ["status"]

    class FreeTextStatusNoteOut(ModelSchema):
        class Meta:
            model = FreeTextStatusNote
            fields = ["status"]

    assert choices_schema_violations(
        [Invoice, Shipment, FreeTextStatusNote], [ShipmentOut, FreeTextStatusNoteOut]
    ) == [
        "ShipmentOut.status: Shipment.status has choices. Type it as "
        "Shipment.Status so the generated TS is a union, not string.",
    ]


@isolate_apps("core")
def test_schema_in_another_app_may_type_the_same_field_name_as_str() -> None:
    class Invoice(models.Model):  # noqa: DJ008
        class Status(models.TextChoices):
            DRAFT = "draft"
            PAID = "paid"

        status = models.CharField(max_length=8, choices=Status.choices)

        class Meta:
            app_label = "core"

    class HealthOut(Schema):
        __module__ = "users.schemas"

        status: str

    assert choices_schema_violations([Invoice], [HealthOut]) == []


@isolate_apps("core")
def test_soft_delete_rejects_an_invented_name() -> None:
    class Note(models.Model):  # noqa: DJ008
        archived_at = models.DateTimeField(null=True, blank=True)

        class Meta:
            app_label = "core"

    assert soft_delete_violations([Note]) == [
        "Note.archived_at: soft-delete has two names. Use revoked_at / is_revoked "
        "to keep the row listed with a revoked badge, or deleted_at / is_deleted "
        "to hide it from every user-facing read."
    ]


@isolate_apps("core")
def test_soft_delete_timestamp_needs_its_is_property() -> None:
    class Token(models.Model):  # noqa: DJ008
        revoked_at = models.DateTimeField(null=True, blank=True)

        class Meta:
            app_label = "core"

    assert soft_delete_violations([Token]) == [
        "Token.revoked_at: add an is_revoked @property that returns "
        "revoked_at is not None."
    ]


@isolate_apps("core")
def test_soft_delete_timestamp_is_a_nullable_datetime() -> None:
    class Token(models.Model):  # noqa: DJ008
        deleted_at = models.DateTimeField()

        class Meta:
            app_label = "core"

        @property
        def is_deleted(self) -> bool:
            return self.deleted_at is not None

    assert soft_delete_violations([Token]) == [
        "Token.deleted_at: make it models.DateTimeField(null=True, blank=True); "
        "None means the row is live."
    ]
