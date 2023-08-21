import multiprocessing
import time
from datetime import datetime

import pytest
import requests

from prices import app

TEST_PORT = 3006


def server(port):
    app.run(port=port)


def wait_for_server_to_start(server_url):
    started = False
    while not started:
        try:
            requests.get(server_url)
            started = True
        except Exception as e:
            time.sleep(0.2)


@pytest.fixture(autouse=True, scope="session")
def lift_pass_pricing_app():
    """ starts the lift pass pricing flask app running on localhost """
    p = multiprocessing.Process(target=server, args=(TEST_PORT,))
    p.start()
    server_url = f"http://127.0.0.1:{TEST_PORT}"
    wait_for_server_to_start(server_url)
    yield server_url
    p.terminate()


@pytest.mark.parametrize('params, expected_price', [
    pytest.param(dict(type='1jour'), 35, id='Standard 1-day'),
    pytest.param(dict(type='1jour', age=10), 25, id='Under 15 gets 30% discount'),
    pytest.param(dict(type='1jour', age=5), 0, id='Under 6 free'),
    pytest.param(dict(type='1jour', date='2019-02-18'), 35, id='Holidays are the same'),
    pytest.param(dict(type='1jour', date='2019-02-11'), 23, id='Mondays that aren\'t holidays are 35% cheaper'),
])
def test__api__day_pass__pricing(lift_pass_pricing_app, params, expected_price):
    response = requests.get(lift_pass_pricing_app + "/prices", params=params)
    assert response.json() == {'cost': expected_price}


@pytest.mark.parametrize('params, expected_price', [
    pytest.param(dict(type='night'), 0, id='Standard night'),
    pytest.param(dict(type='night', age=45), 19, id='Standard night'),
    pytest.param(dict(type='night', age=10), 19, id='Under 15 no discount'),
    pytest.param(dict(type='night', age=5), 0, id='Under 6 free'),
    pytest.param(dict(type='night', age=25, date='2019-02-18'), 19, id='Holidays are the same'),
    pytest.param(dict(type='night', age=25, date='2019-02-11'), 19, id='No discounts on Monday'),
    pytest.param(dict(type='night', date='2019-02-11'), 0, id='Loophole for ageless people at night'),
])
def test__api__night_pass_pricing(lift_pass_pricing_app, params, expected_price):
    response = requests.get(lift_pass_pricing_app + "/prices", params=params)
    assert response.json() == {'cost': expected_price}

@pytest.mark.parametrize(
    "age,expectedCost", [
        (5, 0),
        (6, 25),
        (14, 25),
        (15, 35),
        (25, 35),
        (64, 35),
        (65, 27),
    ])
def test_works_for_all_ages(lift_pass_pricing_app, age, expectedCost):
    response = requests.get(lift_pass_pricing_app + "/prices", params={'type': '1jour', 'age': age})
    assert response.json() == {'cost': expectedCost}


@pytest.mark.parametrize(
    "age,expectedCost", [
        (5, 0),
        (6, 19),
        (25, 19),
        (64, 19),
        (65, 8),
    ])
def test_works_for_night_passes(lift_pass_pricing_app, age, expectedCost):
    response = requests.get(lift_pass_pricing_app + "/prices", params={'type': 'night', 'age': age})
    assert response.json() == {'cost': expectedCost}


@pytest.mark.parametrize(
    "age,expectedCost,ski_date", [
        (15, 35, datetime.fromisoformat('2019-02-22')),
        (15, 35, datetime.fromisoformat('2019-02-25')), # monday, holiday
        (15, 23, datetime.fromisoformat('2019-03-11')), # monday
        (65, 18, datetime.fromisoformat('2019-03-11')),  # monday
    ])
def test_works_for_monday_deals(lift_pass_pricing_app, age, expectedCost, ski_date):
    response = requests.get(lift_pass_pricing_app + "/prices", params={'type': '1jour', 'age': age, 'date': ski_date})
    assert response.json() == {'cost': expectedCost}
