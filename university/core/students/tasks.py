from celery import shared_task

from .models import GeneralWeightedAverageSheet


@shared_task
def async_gwa_sheet_process(*, id: int):
    from .services import gwa_sheet_process

    gwa_sheet = GeneralWeightedAverageSheet.objects.filter(
        id=id, status=GeneralWeightedAverageSheet.Statuses.PENDING
    ).first()

    if not gwa_sheet:
        return

    gwa_sheet_process(gwa_sheet=gwa_sheet)
