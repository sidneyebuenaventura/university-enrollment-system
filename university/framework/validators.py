from rest_framework.exceptions import ValidationError


def csv_file_validator(value):
    valid_content_types = ["text/csv", "application/csv"]

    if value and value.content_type not in valid_content_types:
        raise ValidationError("Invalid csv file")


def receipt_file_validator(value):
    valid_content_types = ["image/jpeg", "image/png", "application/pdf"]
    max_size = 5 * 1024 * 1024

    if value and value.content_type not in valid_content_types:
        raise ValidationError("Upload the receipt as a JPG, PNG or PDF file.")

    if value and value.size > max_size:
        raise ValidationError("The receipt can't be bigger than 5 MB.")


def excel_file_validator(value):
    valid_content_types = [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ]

    if value and value.content_type not in valid_content_types:
        raise ValidationError("Invalid excel file")
