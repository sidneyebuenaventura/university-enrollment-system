from django.core.management.base import BaseCommand

from university.core.accounts.models import Module


class Command(BaseCommand):
    help = "Creates default university.core.accounts.Module data"

    def handle(self, *args, **options):
        web_modules = [
            # Dashboards
            {
                "name": "Home",
                "sub_name": "Admin Dashboard",
                "description": "Announcements, enrollees statistics, & classes open statistics.",
                "codename": "web.dashboard_admin",
                "category": Module.Categories.DASHBOARD,
            },
            {
                "name": "Home",
                "sub_name": "Department Secretary Dashboard",
                "description": "Announcements, enrollees statistics, & classes open statistics.",
                "codename": "web.dashboard_department_secretary",
                "category": Module.Categories.DASHBOARD,
            },
            {
                "name": "Home",
                "sub_name": "Dean Dashboard",
                "description": "Announcements, enrollees statistics, & classes open statistics per course specific to school.",
                "codename": "web.dashboard_dean",
                "category": Module.Categories.DASHBOARD,
            },
            {
                "name": "Home",
                "sub_name": "Faculty Dashboard",
                "description": "Announcements, and faculty schedule",
                "codename": "web.dashboard_faculty",
                "category": Module.Categories.DASHBOARD,
            },
            {
                "name": "Home",
                "sub_name": "Guidance Counselor Dashboard",
                "description": "Announcements, statistics of students with failed grades, and students that are already interviewed.",
                "codename": "web.dashboard_guidance_counselor",
                "category": Module.Categories.DASHBOARD,
            },
            {
                "name": "Home",
                "sub_name": "Cashier Dashboard",
                "description": "Announcements, statistics of students with outstanding balance, fully paid, and total expected to pay over the counter.",
                "codename": "web.dashboard_cashier",
                "category": Module.Categories.DASHBOARD,
            },
            {
                "name": "Home",
                "sub_name": "VP Finance Dashboard",
                "description": "Announcements, and faculty schedule.",
                "codename": "web.dashboard_vp_finance",
                "category": Module.Categories.DASHBOARD,
            },
            {
                "name": "Home",
                "sub_name": "VP Acad Dashboard",
                "description": "Announcements, statistics of students enrolled, classes with uploaded grades, and classes open",
                "codename": "web.dashboard_vp_acad",
                "category": Module.Categories.DASHBOARD,
            },
            {
                "name": "Dashboard",
                "description": "Dashboard for Father President",
                "codename": "web.dashboard",
                "category": Module.Categories.DASHBOARD,
            },
            # Base
            {
                "name": "Search Students",
                "codename": "web.student_search",
                "category": Module.Categories.BASE,
            },
            {
                "name": "Grades",
                "codename": "web.grades",
                "category": Module.Categories.BASE,
            },
            {
                "name": "User Account",
                "codename": "web.user_accounts",
                "category": Module.Categories.BASE,
            },
            {
                "name": "User Roles",
                "codename": "web.user_roles",
                "category": Module.Categories.BASE,
            },
            {
                "name": "Faculty",
                "codename": "web.faculty",
                "category": Module.Categories.BASE,
            },
            # Configurations
            {
                "name": "Import Data",
                "codename": "web.configurations_import_data",
                "category": Module.Categories.CONFIGURATION,
            },
            {
                "name": "Module Configuration",
                "codename": "web.configurations_module_configuration",
                "category": Module.Categories.CONFIGURATION,
            },
            {
                "name": "Curriculum",
                "codename": "web.curriculums",
                "category": Module.Categories.CONFIGURATION,
            },
            {
                "name": "Blocked Enrollees",
                "codename": "web.blocked_enrollees",
                "category": Module.Categories.CONFIGURATION,
            },
            {
                "name": "Failed Students",
                "codename": "web.failed_students",
                "category": Module.Categories.CONFIGURATION,
            },
            # Transactions
            {
                "name": "Dragonpay",
                "codename": "web.dragonpay_transactions",
                "category": Module.Categories.TRANSACTION,
            },
            {
                "name": "Bukas",
                "codename": "web.bukas_transactions",
                "category": Module.Categories.TRANSACTION,
            },
            {
                "name": "Cashier",
                "codename": "web.cashier_transactions",
                "category": Module.Categories.TRANSACTION,
            },
            {
                "name": "Bank",
                "codename": "web.bank_transactions",
                "category": Module.Categories.TRANSACTION,
            },
            # CMS
            {
                "name": "Curriculum",
                "codename": "web.cms_curriculums",
                "category": Module.Categories.CMS,
            },
            {
                "name": "Courses",
                "codename": "web.cms_courses",
                "category": Module.Categories.CMS,
            },
            {
                "name": "Subjects",
                "codename": "web.cms_subjects",
                "category": Module.Categories.CMS,
            },
            {
                "name": "Rooms",
                "codename": "web.cms_rooms",
                "category": Module.Categories.CMS,
            },
            {
                "name": "Room Classifications",
                "codename": "web.cms_room_classifications",
                "category": Module.Categories.CMS,
            },
            {
                "name": "Buildings",
                "codename": "web.cms_buildings",
                "category": Module.Categories.CMS,
            },
            {
                "name": "Schools",
                "codename": "web.cms_schools",
                "category": Module.Categories.CMS,
            },
            {
                "name": "Fees",
                "codename": "web.cms_fees",
                "category": Module.Categories.CMS,
            },
            {
                "name": "Classes and Schedules",
                "codename": "web.cms_classes_and_schedules",
                "category": Module.Categories.CMS,
            },
            {
                "name": "Discounts",
                "codename": "web.cms_discounts",
                "category": Module.Categories.CMS,
            },
            {
                "name": "Academic Calendar",
                "codename": "web.academic_calendar",
                "category": Module.Categories.CMS,
            },
            # Student Requests
            {
                "name": "Schedule Change",
                "codename": "web.student_request_schedule_change",
                "category": Module.Categories.STUDENT_REQUEST,
            },
            {
                "name": "Class Opening",
                "codename": "web.student_request_class_opening",
                "category": Module.Categories.STUDENT_REQUEST,
            },
            {
                "name": "Subject Addition",
                "codename": "web.student_request_subject_addition",
                "category": Module.Categories.STUDENT_REQUEST,
            },
            {
                "name": "Withdrawal",
                "codename": "web.student_request_withdrawal",
                "category": Module.Categories.STUDENT_REQUEST,
            },
        ]

        mobile_modules = [
            {
                "name": "Home",
                "codename": "mobile.home",
                "category": Module.Categories.MOBILE,
            },
            {
                "name": "Pre-Enrollment",
                "codename": "mobile.pre_enrollment",
                "category": Module.Categories.MOBILE,
            },
            {
                "name": "Enrollment",
                "codename": "mobile.enrollment",
                "category": Module.Categories.MOBILE,
            },
            {
                "name": "Statement of Account",
                "codename": "mobile.soa",
                "category": Module.Categories.MOBILE,
            },
            {
                "name": "Curriculum",
                "codename": "mobile.curriculum_checklist",
                "category": Module.Categories.MOBILE,
            },
            {
                "name": "Grades",
                "codename": "mobile.curriculum_grades",
                "category": Module.Categories.MOBILE,
            },
            {
                "name": "Personal Details",
                "codename": "mobile.student_information",
                "category": Module.Categories.MOBILE,
            },
            {
                "name": "Request Submission",
                "codename": "mobile.request_submission",
                "category": Module.Categories.MOBILE,
            },
        ]

        for index, module in enumerate(web_modules):
            Module.objects.update_or_create(
                platform=Module.Platforms.WEB,
                codename=module.get("codename"),
                defaults={
                    "order": index,
                    "name": module.get("name"),
                    "sub_name": module.get("sub_name", None),
                    "description": module.get("description"),
                    "category": module.get("category"),
                },
            )

        for index, module in enumerate(mobile_modules):
            Module.objects.update_or_create(
                platform=Module.Platforms.MOBILE,
                codename=module.get("codename"),
                defaults={
                    "order": index,
                    "name": module.get("name"),
                    "sub_name": module.get("sub_name", None),
                    "description": module.get("description"),
                    "category": module.get("category"),
                },
            )
