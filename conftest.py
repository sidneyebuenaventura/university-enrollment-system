import pytest
from rest_framework.test import APIClient

from university.core.accounts.tests.factories import *
from university.core.cms.tests.factories import *
from university.core.students.tests.factories import *
from university.payment.tests.factories import *


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def staff_api_client(api_client, staff_user):
    api_client.force_authenticate(user=staff_user)
    return api_client


@pytest.fixture
def student_api_client(api_client, student):
    api_client.force_authenticate(user=student.user)
    return api_client
