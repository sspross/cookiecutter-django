import factory
from factory.declarations import LazyAttribute, Sequence

from users.models import User


class UserFactory(factory.django.DjangoModelFactory[User]):
    class Meta:
        model = User
        django_get_or_create = ("username",)

    username = Sequence(lambda n: f"user-{n}")
    email = LazyAttribute(lambda obj: f"{obj.username}@example.com")
    password = factory.django.Password("pw-12345!")
