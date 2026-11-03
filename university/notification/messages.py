from dataclasses import dataclass


@dataclass
class EmailMessage:
    subject: str
    body: str = None
    template: str = None


class MessageKeys:
    USER_PASSWORD_RESET = "user_password_reset"
    STUDENT_LOGIN_CREDENTIALS = "student_login_credentials"
    PRE_ENROLLMENT_REMINDER = "pre_enrollment_reminder"
    ENROLLMENT_REMINDERS = "enrollment_reminders"
    ENROLLMENT_SUCCESS = "enrollment_success"
    STATEMENT_OF_ACCOUNT = "statement_of_account"
    REQUEST_ADD_SUBJECT_APPROVED = "request_add_subject_approved"
    REQUEST_ADD_SUBJECT_REJECTED = "request_add_subject_rejected"
    REQUEST_CHANGE_SCHEDULE_APPROVED = "request_change_schedule_approved"
    REQUEST_CHANGE_SCHEDULE_REJECTED = "request_change_schedule_rejected"
    REQUEST_OPEN_CLASS_FOR_APPROVAL = "request_open_class_for_approval"
    REQUEST_OPEN_CLASS_REVIEW_UPDATED = "request_open_class_review_updated"
    REQUEST_OPEN_CLASS_APPROVED = "request_open_class_approved"
    REQUEST_OPEN_CLASS_REJECTED = "request_open_class_rejected"
    REQUEST_WITHDRAWAL_FOR_APPROVAL = "request_withdrawal_for_approval"
    REQUEST_WITHDRAWAL_REVIEW_UPDATED = "request_withdrawal_review_updated"
    REQUEST_WITHDRAWAL_APPROVED = "request_withdrawal_approved"
    REQUEST_WITHDRAWAL_REJECTED = "request_withdrawal_rejected"


EMAIL_MESSAGES = {
    MessageKeys.USER_PASSWORD_RESET: EmailMessage(
        subject="Password Reset",
        template="notification/user_password_reset.html",
    ),
    MessageKeys.STUDENT_LOGIN_CREDENTIALS: EmailMessage(
        subject="Login Credentials",
        template="notification/student_login_credentials.html",
    ),
    MessageKeys.PRE_ENROLLMENT_REMINDER: EmailMessage(
        subject="Pre Enrollment Reminder",
        template="notification/pre_enrollment_reminder.html",
    ),
    MessageKeys.ENROLLMENT_REMINDERS: EmailMessage(
        subject="Enrollment Reminders",
        template="notification/enrollment_reminders.html",
    ),
    MessageKeys.ENROLLMENT_SUCCESS: EmailMessage(
        subject="Enrollment Success",
        template="notification/enrollment_success.html",
    ),
    MessageKeys.STATEMENT_OF_ACCOUNT: EmailMessage(
        subject="Your Enrollment Statement of Account",
        template="notification/statement_of_account.html",
    ),
    MessageKeys.REQUEST_ADD_SUBJECT_APPROVED: EmailMessage(
        subject="Add Subject Request Approved",
        template="notification/request_add_subject_approved.html",
    ),
    MessageKeys.REQUEST_ADD_SUBJECT_REJECTED: EmailMessage(
        subject="Add Subject Request Rejected",
        template="notification/request_add_subject_rejected.html",
    ),
    MessageKeys.REQUEST_CHANGE_SCHEDULE_APPROVED: EmailMessage(
        subject="Change Schedule Request Approved",
        template="notification/request_change_schedule_approved.html",
    ),
    MessageKeys.REQUEST_CHANGE_SCHEDULE_REJECTED: EmailMessage(
        subject="Change Schedule Request Rejected",
        template="notification/request_change_schedule_rejected.html",
    ),
    MessageKeys.REQUEST_OPEN_CLASS_FOR_APPROVAL: EmailMessage(
        subject="Open Class Request For Approval",
        template="notification/request_open_class_for_approval.html",
    ),
    MessageKeys.REQUEST_OPEN_CLASS_REVIEW_UPDATED: EmailMessage(
        subject="Open Class Request Update",
        template="notification/request_open_class_review_updated.html",
    ),
    MessageKeys.REQUEST_OPEN_CLASS_APPROVED: EmailMessage(
        subject="Open Class Request Approved",
        template="notification/request_open_class_approved.html",
    ),
    MessageKeys.REQUEST_OPEN_CLASS_REJECTED: EmailMessage(
        subject="Open Class Request Rejected",
        template="notification/request_open_class_rejected.html",
    ),
    MessageKeys.REQUEST_WITHDRAWAL_FOR_APPROVAL: EmailMessage(
        subject="Withdrawal Request For Approval",
        template="notification/request_withdrawal_for_approval.html",
    ),
    MessageKeys.REQUEST_WITHDRAWAL_REVIEW_UPDATED: EmailMessage(
        subject="Withdrawal Request Update",
        template="notification/request_withdrawal_review_updated.html",
    ),
    MessageKeys.REQUEST_WITHDRAWAL_APPROVED: EmailMessage(
        subject="Withdrawal Request Approved",
        template="notification/request_withdrawal_approved.html",
    ),
    MessageKeys.REQUEST_WITHDRAWAL_REJECTED: EmailMessage(
        subject="Withdrawal Request Rejected",
        template="notification/request_withdrawal_rejected.html",
    ),
}
