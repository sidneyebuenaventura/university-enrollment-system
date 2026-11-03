from rest_framework.exceptions import ValidationError


def csv_file_validator(value):
    valid_content_types = ["text/csv", "application/csv"]

    if value and value.content_type not in valid_content_types:
        raise ValidationError("Invalid csv file")


def excel_file_validator(value):
    valid_content_types = [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ]

    if value and value.content_type not in valid_content_types:
        raise ValidationError("Invalid excel file")
