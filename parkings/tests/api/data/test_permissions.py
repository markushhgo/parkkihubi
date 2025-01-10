import pytest
from django.urls import reverse
from rest_framework.status import HTTP_200_OK, HTTP_403_FORBIDDEN

data_endpoints = ('event_parking_anonymized-list',)


def _get_api_client(api_user, data_user_api_client, enforcer_api_client,
                    operator_api_client, staff_api_client, user_api_client):
    if api_user == 'data_api':
        client = data_user_api_client
    elif api_user == 'enforcer_api':
        client = enforcer_api_client
    elif api_user == 'operator_api':
        client = operator_api_client
    elif api_user == 'staff_api':
        client = staff_api_client
    else:
        client = user_api_client

    return client


@pytest.mark.parametrize(
    'api_user, status_code',
    [
        ('data_api', HTTP_200_OK),
        ('enforcer_api', HTTP_403_FORBIDDEN),
        ('operator_api', HTTP_403_FORBIDDEN),
        ('staff_api', HTTP_403_FORBIDDEN),
        ('user_api', HTTP_403_FORBIDDEN)
    ]
)
def test_get_enforcement_api_permission(
    api_user, data_user_api_client, enforcer_api_client, operator_api_client,
    staff_api_client, user_api_client, status_code
):
    client = _get_api_client(api_user, data_user_api_client, enforcer_api_client,
                             operator_api_client, staff_api_client, user_api_client)

    for endpoint in data_endpoints:
        list_url = reverse('data:v1:{}'.format(endpoint))
        response = client.get(list_url)
        assert response.status_code == status_code

        # Add filter param?
        # valid_parking_url = reverse('enforcement:v1:valid_parking-list') + '?reg_num=ABC-123'
        # response = client.get(valid_parking_url)
        # assert response.status_code == status_code
