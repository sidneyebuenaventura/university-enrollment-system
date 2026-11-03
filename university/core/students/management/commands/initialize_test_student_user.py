from django.core.management.base import BaseCommand, CommandError

from university.core.students.services import test_student_create
from university.framework.exceptions import ServiceException


class Command(BaseCommand):
    help = "Creates test Student User"

    def add_arguments(self, parser):
        parser.add_argument("username", nargs="?", default="student", type=str)
        parser.add_argument("first_name", nargs="?", default="Juan", type=str)
        parser.add_argument("last_name", nargs="?", default="dela Cruz", type=str)
        parser.add_argument(
            "email", nargs="?", default="jdelacruz@example.com", type=str
        )
        parser.add_argument(
            "student_number", nargs="?", default="TEST20220001", type=str
        )

    def handle(self, *args, **options):
        try:
            test_student_create(
                username=options["username"],
                email=options["email"],
                first_name=options["first_name"],
                last_name=options["last_name"],
                student_number=options["student_number"],
            )
        except ServiceException as e:
            raise CommandError(str(e))
