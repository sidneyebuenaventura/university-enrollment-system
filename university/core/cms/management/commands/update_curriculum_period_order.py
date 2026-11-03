import argparse
import sys

from django.core.management.base import BaseCommand

from university.core.cms.models import Curriculum, Semesters
from university.framework.utils import LoadScreen

load_screen = LoadScreen()

sem_mapping = [
    Semesters.FIRST_SEMESTER,
    Semesters.SECOND_SEMESTER,
    Semesters.SUMMER,
]


class Command(BaseCommand):
    help = "Run curriculum data upload functionality"

    def add_arguments(self, parser):
        parser.add_argument("csvfile", nargs="?", type=argparse.FileType("r"))

    def handle(self, *args, **options):
        spinner = load_screen.spinning_cursor()
        sys.stdout.write("Curriculum Period Order update... ")

        for curriculum in Curriculum.objects.all():
            load_screen.spinner(spinner)

            curriculum_periods = curriculum.curriculum_periods.all().order_by(
                "year_level"
            )
            curriculum_periods.update(order=0)

            order = 1
            for year_level in range(5):
                for sem in sem_mapping:
                    curr_period = curriculum_periods.filter(
                        semester=sem, year_level=year_level + 1
                    ).first()
                    if curr_period:
                        curr_period.order = order
                        curr_period.save()
                        order += 1

        message = "\nSUCCESSFULLY UPDATED CURRICULUM PERIOD ORDER DATA."
        load_screen.print_statement(message, None)
