from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from university.core.accounts.models import School
from university.core.demo.seed import (
    ADMIN_USERNAME,
    DEMO_PASSWORD,
    STUDENT_USERNAME,
    DemoSeeder,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Fills an empty database with demo schools, courses, students and payments"

    def add_arguments(self, parser):
        parser.add_argument("--students", type=int, default=40)
        parser.add_argument(
            "--seed", type=int, default=42, help="Random seed for repeatable data"
        )

    def handle(self, *args, **options):
        if options["students"] < 1:
            raise CommandError("--students has to be at least 1.")

        usernames = [ADMIN_USERNAME, STUDENT_USERNAME]
        if School.objects.exists() or User.objects.filter(username__in=usernames):
            raise CommandError(
                "The database already has data. seed_demo only runs on an empty "
                "database."
            )

        with transaction.atomic():
            DemoSeeder(students=options["students"], seed=options["seed"]).run()

        self.stdout.write(self.style.SUCCESS("Demo data created."))
        self.stdout.write(f"  Admin:   {ADMIN_USERNAME} / {DEMO_PASSWORD}")
        self.stdout.write(f"  Student: {STUDENT_USERNAME} / {DEMO_PASSWORD}")
