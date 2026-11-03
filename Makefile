RUN_BASE = docker compose run --rm base
RUN_CORE = docker compose run --rm core
DJANGO_MANAGE = $(RUN_BASE) python manage.py

all: init active_academic_years dragonpay_channels upload  students enrollments

init: modules module_permissions roles superuser_role 

migrate:
	$(RUN_BASE) migrate

migrations:
	$(RUN_BASE) makemigrations

collectstatic:
	$(DJANGO_MANAGE) collectstatic --noinput

admin_theme:
	$(DJANGO_MANAGE) loaddata admin_theme.json

shell:
	$(DJANGO_MANAGE) shell_plus

bash:
	$(RUN_CORE) bash

test:
	$(RUN_CORE) pytest

test_cov:
	$(RUN_CORE) pytest --cov

test_deploy:
	$(RUN_CORE) python manage.py check --deploy

superuser:
	$(DJANGO_MANAGE) createsuperuser

superuser_role:
	$(DJANGO_MANAGE) initialize_superuser_role

student:
	$(DJANGO_MANAGE) initialize_test_student_user

test_students:
	$(DJANGO_MANAGE) initialize_test_student_user teststudent02 Jane Doe jdoe@example.com TEST20220002
	$(DJANGO_MANAGE) initialize_test_student_user teststudent03 Mark Valdez mvaldez@example.com TEST20220003

modules:
	$(DJANGO_MANAGE) initialize_modules

module_permissions:
	$(DJANGO_MANAGE) initialize_module_permissions

roles:
	$(DJANGO_MANAGE) initialize_reserved_roles

dragonpay_channels:
	$(DJANGO_MANAGE) initialize_dragonpay_channels

active_academic_years:
	$(DJANGO_MANAGE) initialize_current_academic_year 1
	$(DJANGO_MANAGE) initialize_current_academic_year 0

academic_years:
	$(DJANGO_MANAGE) initialize_academic_year 2022 2023
	$(DJANGO_MANAGE) initialize_academic_year 2021 2022
	

fees:
	$(DJANGO_MANAGE) upload_fee files/fee_data.csv
	$(DJANGO_MANAGE) upload_misc_fee_spec files/misc_fee_spec_data.csv
	$(DJANGO_MANAGE) upload_misc_fee_spec_fees files/misc_fee_spec_fees_data.csv
	$(DJANGO_MANAGE) upload_other_fee_spec files/other_fee_spec_data.csv
	$(DJANGO_MANAGE) upload_other_fee_spec_fees files/other_fee_spec_fees_data.csv

curriculums:
	$(DJANGO_MANAGE) upload_curriculum files/curriculum_data.csv
	$(DJANGO_MANAGE) upload_curriculum_period files/curriculum_period_data.csv
	$(DJANGO_MANAGE) update_curriculum_period_order
	$(DJANGO_MANAGE) upload_curriculum_subject files/curriculum_subject_data.csv
	$(DJANGO_MANAGE) upload_class files/class_data.csv > logs/upload/class.log

subjects:
	$(DJANGO_MANAGE) upload_subject_grouping files/subject_grouping_data.csv
	$(DJANGO_MANAGE) upload_subject files/subject_data.csv
	
upload:
	$(DJANGO_MANAGE) upload_religion files/religion_data.csv
	$(DJANGO_MANAGE) upload_personnel files/personnel_data.csv
	$(DJANGO_MANAGE) upload_school files/school_data.csv
	$(DJANGO_MANAGE) upload_department files/department_data.csv
	$(DJANGO_MANAGE) upload_department files/department_data.csv
	$(DJANGO_MANAGE) upload_course files/course_data.csv
	$(DJANGO_MANAGE) upload_building files/building_data.csv
	$(DJANGO_MANAGE) upload_classification files/room_classification_data.csv
	$(DJANGO_MANAGE) upload_room files/room_data.csv
	$(DJANGO_MANAGE) upload_subject_grouping files/subject_grouping_data.csv
	$(DJANGO_MANAGE) upload_subject files/subject_data.csv
	$(DJANGO_MANAGE) upload_curriculum files/curriculum_data.csv
	$(DJANGO_MANAGE) upload_curriculum_period files/curriculum_period_data.csv
	$(DJANGO_MANAGE) update_curriculum_period_order
	$(DJANGO_MANAGE) upload_curriculum_subject files/curriculum_subject_data.csv
	$(DJANGO_MANAGE) upload_curriculum_subject_requisite files/curriculum_subject_requisite_data.csv
	$(DJANGO_MANAGE) upload_class files/class_data.csv > logs/upload/class.log
	$(DJANGO_MANAGE) upload_fee files/fee_data.csv
	$(DJANGO_MANAGE) upload_misc_fee_spec files/misc_fee_spec_data.csv
	$(DJANGO_MANAGE) upload_misc_fee_spec_fees files/misc_fee_spec_fees_data.csv
	$(DJANGO_MANAGE) upload_other_fee_spec files/other_fee_spec_data.csv
	$(DJANGO_MANAGE) upload_other_fee_spec_fees files/other_fee_spec_fees_data.csv
	$(DJANGO_MANAGE) upload_tuition_fee_rate files/tuition_fee_rate_data.csv
	$(DJANGO_MANAGE) upload_tuition_fee_rate_class files/tuition_fee_rate_class_data.csv > logs/upload/tuition_fee_rate_class.log
	$(DJANGO_MANAGE) upload_discount files/discount_data.csv
	$(DJANGO_MANAGE) upload_laboratory_fee files/laboratory_fee_data.csv 2021 2022
	$(DJANGO_MANAGE) upload_remark_code files/remark_code_data.csv
	
students:
	$(DJANGO_MANAGE) upload_student files/student_data.csv

enrollments:
	$(DJANGO_MANAGE) upload_student_enrollment files/enrollment_20223_and_below/student_enrollment_data.csv 0 1 > logs/upload/20223_below_enrollment.log
	$(DJANGO_MANAGE) upload_student_enrollment_gwa files/enrollment_20223_and_below/student_enrollment_gwa_data.csv > logs/upload/20223_below_enrollment_gwa.log
	$(DJANGO_MANAGE) upload_student_enrollment_fee files/enrollment_20223_and_below/student_enrollment_fee_data.csv > logs/upload/20223_below_enrollment_fee.log
	$(DJANGO_MANAGE) upload_student_enrollment_discount files/enrollment_20223_and_below/student_enrollment_discount_data.csv > logs/upload/20223_below_discount_enrollment.log
	$(DJANGO_MANAGE) upload_student_enrollment files/enrollment_20231/student_enrollment_data.csv 0 0 > logs/upload/20231_enrollment.log
	$(DJANGO_MANAGE) upload_student_enrollment_fee files/enrollment_20231/student_enrollment_fee_data.csv > logs/upload/20231_enrollment_fee.log
	$(DJANGO_MANAGE) upload_student_enrollment_discount files/enrollment_20231/student_enrollment_discount_data.csv > logs/upload/20231_enrollment_discount.log
	$(DJANGO_MANAGE) upload_student_enrollment_balance files/enrollment_20231/student_enrollment_balance_data.csv > logs/upload/enrollment_balance.log
	$(DJANGO_MANAGE) generate_soa  > logs/upload/generate_soa.log
	$(DJANGO_MANAGE) evaluate_student_latest_enrolled


20223_and_below_enrollments:
	$(DJANGO_MANAGE) upload_student_enrollment files/enrollment_20223_and_below/student_enrollment_data.csv 0 1 > logs/upload/20223_below_enrollmen.log
	$(DJANGO_MANAGE) upload_student_enrollment_gwa files/enrollment_20223_and_below/student_enrollment_gwa_data.csv > logs/upload/20223_below_enrollment_gwa.log
	$(DJANGO_MANAGE) upload_student_enrollment_fee files/enrollment_20223_and_below/student_enrollment_fee_data.csv > logs/upload/20223_below_enrollment_fee.log
	$(DJANGO_MANAGE) upload_student_enrollment_discount files/enrollment_20223_and_below/student_enrollment_discount_data.csv > logs/upload/20223_below_discount_enrollment.log



20231_enrollments:
	$(DJANGO_MANAGE) upload_student_enrollment files/enrollment_20231/student_enrollment_data.csv 0 0 > logs/upload/20231_enrollment.log
	$(DJANGO_MANAGE) upload_student_enrollment_fee files/enrollment_20231/student_enrollment_fee_data.csv > logs/upload/20231_enrollment_fee.log
	$(DJANGO_MANAGE) upload_student_enrollment_discount files/enrollment_20231/student_enrollment_discount_data.csv > logs/upload/20231_enrollment_discount.log
	$(DJANGO_MANAGE) upload_student_enrollment_balance files/enrollment_20231/student_enrollment_balance_data.csv > logs/upload/enrollment_balance.log

