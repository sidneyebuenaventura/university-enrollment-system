from django.db.models import TextChoices

DESCRIPTION = """# Introduction
University Enrollment System API for the Admin and Student portals.

# Named Django Routes
Refer to the `Path Name` of each operation.
"""


class Tags(TextChoices):
    # Core Service - Accounts
    AUTH = "auth", "Auth"
    STAFFS = "staffs", "Staffs"
    FACULTY = "faculty", "Faculty"
    MODULES = "modules", "Modules"
    ROLES = "roles", "Roles"
    PERMISSIONS = "permissions", "Permissions"
    SCHOOLS = "schools", "Schools"
    DEPARTMENTS = "departments", "Departments"
    ACADEMIC_YEARS = "academic-years", "Academic Years"
    SEMESTERS = "semesters", "Semesters"
    DASHBOARDS = "dashboards", "Dashboards"
    # Core Service - CMS
    CURRICULUMS = "curriculums", "Curriculums"
    CURRICULUM_PERIODS = "curriculum-periods", "Curriculum Periods"
    CLASSES = "classes", "Classes"
    CLASS_SCHEDULES = "class-schedules", "Class Schedules"
    SUBJECTS = "subjects", "Subjects"
    COURSES = "courses", "Courses"
    ROOMS = "rooms", "Rooms"
    ROOM_CLASSIFICATIONS = "room-classifications", "Room Classifications"
    BUILDING = "buildings", "Buildings"
    FEES = "fees", "Fees"
    FEE_SPECIFICATION = "fee-specifications", "Fee Specifications"
    DISCOUNTS = "discounts", "Discounts"
    ANNOUNCEMENTS = "announcements", "Announcements"
    # Core Service - Students
    STUDENTS = "students", "Students"
    STUDENT_PROFILE = "student-profile", "Student Profile"
    STUDENT_ENROLLMENT = "student-enrollment", "Student Enrollment"
    STUDENT_GRADES = "student-grades", "Student Grades"
    STUDENT_CLASSES = "student-classes", "Student Classes"
    STUDENT_REQUESTS = "student-requests", "Student Requests"
    CHANGE_SCHEDULE_REQUESTS = "change-schedule-requests", "Change Schedule Requests"
    ADD_SUBJECT_REQUESTS = "add-subject-requests", "Add Subject Requests"
    OPEN_CLASS_REQUESTS = "open-class-requests", "Open Class Requests"
    WITHDRAWAL_REQUESTS = "withdrawal-requests", "Withdrawal Requests"
    CLASS_STUDENTS = "class-students", "Class Students"
    GRADE_SHEETS = "grade-sheets", "Grade Sheets"
    # Core Service - Maintenance
    MODULE_CONFIGURATIONS = "module-configurations", "Module Configurations"
    ENROLLMENT_SCHEDULES = "enrollment-schedules", "Enrollment Schedules"
    # Payment Service
    PAYMENTS = "payments", "Payments"
    PAYMENT_SETTLEMENTS = "settlements", "Payment Settlements"
    JOURNAL_VOUCHERS = "journal-vouchers", "Journal Vouchers"
    STATEMENT_OF_ACCOUNTS = "statement-of-accounts", "Statement of Accounts"
    DRAGONPAY = "dragonpay", "Dragonpay Payments"
    DRAGONPAY_CHANNELS = "dragonpay-channels", "Dragonpay Channels"
    BUKAS = "bukas", "Bukas Payments"
    OTC = "otc", "OTC Payments"
    CASHIER = "cashier", "Cashier Payments"
    # Framework
    ENUMS = "enums", "Enums"


TAGS = [{"name": name, "x-displayName": display} for name, display in Tags.choices]

TAG_GROUPS = [
    {
        "name": "Account Management",
        "tags": [
            Tags.AUTH,
            Tags.STAFFS,
            Tags.MODULES,
            Tags.ROLES,
            Tags.PERMISSIONS,
            Tags.SCHOOLS,
            Tags.DEPARTMENTS,
            Tags.FACULTY,
            Tags.DASHBOARDS,
        ],
    },
    {
        "name": "CMS",
        "tags": [
            Tags.CURRICULUMS,
            Tags.CURRICULUM_PERIODS,
            Tags.CLASSES,
            Tags.CLASS_SCHEDULES,
            Tags.SUBJECTS,
            Tags.ROOMS,
            Tags.ROOM_CLASSIFICATIONS,
            Tags.COURSES,
            Tags.BUILDING,
            Tags.FEES,
            Tags.FEE_SPECIFICATION,
            Tags.DISCOUNTS,
            Tags.ANNOUNCEMENTS,
        ],
    },
    {
        "name": "Maintenance",
        "tags": [
            Tags.MODULE_CONFIGURATIONS,
            Tags.ENROLLMENT_SCHEDULES,
            Tags.ACADEMIC_YEARS,
            Tags.SEMESTERS,
        ],
    },
    {
        "name": "Student Management",
        "tags": [
            Tags.STUDENTS,
            Tags.STUDENT_PROFILE,
            Tags.STUDENT_ENROLLMENT,
            Tags.STUDENT_GRADES,
            Tags.STUDENT_CLASSES,
            Tags.CLASS_STUDENTS,
            Tags.GRADE_SHEETS,
            Tags.STUDENT_REQUESTS,
            Tags.CHANGE_SCHEDULE_REQUESTS,
            Tags.ADD_SUBJECT_REQUESTS,
            Tags.OPEN_CLASS_REQUESTS,
            Tags.WITHDRAWAL_REQUESTS,
        ],
    },
    {
        "name": "Payments",
        "tags": [
            Tags.PAYMENTS,
            Tags.PAYMENT_SETTLEMENTS,
            Tags.JOURNAL_VOUCHERS,
            Tags.STATEMENT_OF_ACCOUNTS,
            Tags.DRAGONPAY,
            Tags.DRAGONPAY_CHANNELS,
            Tags.BUKAS,
            Tags.OTC,
            Tags.CASHIER,
        ],
    },
    {
        "name": "Framework",
        "tags": [
            Tags.ENUMS,
        ],
    },
]

EXTENSIONS_INFO = {
    "x-logo": {"url": "/static/logo.svg"},
}

EXTENSIONS_ROOT = {
    "x-tagGroups": TAG_GROUPS,
}
