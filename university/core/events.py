from university.framework.events import EventBus

# Event names should follow the <service_name>.<event_name> format
USER_PASSWORD_RESET = "core.user_password_reset"

STAFF_CREATED = "core.staff_created"
STAFF_UPDATED = "core.staff_updated"

ROLE_CREATED = "core.role_created"
ROLE_UPDATED = "core.role_updated"
ROLE_DELETED = "core.role_deleted"

STUDENT_PASSWORD_GENERATED = "core.student_password_generated"

PRE_ENROLLMENT_REMINDER_SENT = "core.pre_enrollment_reminder_sent"
PRE_ENROLLMENT_STARTED = "core.pre_enrollment_started"
PRE_ENROLLMENT_ENDED = "core.pre_enrollment_ended"

ENROLLMENT_REMINDER_SENT = "core.enrollment_reminder_sent"
ENROLLMENT_STARTED = "core.enrollment_started"
ENROLLMENT_ENDED = "core.enrollment_ended"

ENROLLMENT_ENROLLED = "core.enrollment_enrolled"

GRADE_SHEET_CREATED = "core.grade_sheet_created"
GRADE_SHEET_DRAFTED = "core.grade_sheet_drafted"
GRADE_SHEET_SUBMITTED = "core.grade_sheet_submitted"

REQUEST_ADD_SUBJECT_APPROVED = "core.request_add_subject_approved"
REQUEST_ADD_SUBJECT_REJECTED = "core.request_add_subject_rejected"

REQUEST_CHANGE_SCHEDULE_APPROVED = "core.request_change_schedule_approved"
REQUEST_CHANGE_SCHEDULE_REJECTED = "core.request_change_schedule_rejected"

REQUEST_OPEN_CLASS_FOR_APPROVAL = "core.request_open_class_for_approval"
REQUEST_OPEN_CLASS_REVIEW_UPDATED = "core.request_open_class_review_updated"
REQUEST_OPEN_CLASS_APPROVED = "core.request_open_class_approved"
REQUEST_OPEN_CLASS_REJECTED = "core.request_open_class_rejected"

REQUEST_WITHDRAWAL_FOR_APPROVAL = "core.request_withdrawal_for_approval"
REQUEST_WITHDRAWAL_REVIEW_UPDATED = "core.request_withdrawal_review_updated"
REQUEST_WITHDRAWAL_APPROVED = "core.request_withdrawal_approved"
REQUEST_WITHDRAWAL_REJECTED = "core.request_withdrawal_rejected"


bus = EventBus(service_name="core")
