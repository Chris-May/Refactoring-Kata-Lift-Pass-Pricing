import math
from datetime import datetime

from flask import Flask
from flask import request

from db import create_lift_pass_db_connection

app = Flask("lift-pass-pricing")

connection_options = {
    "host": 'localhost',
    "user": 'root',
    "database": 'lift_pass',
    "password": 'mysql'}

connection = None


class LiftPass:
    def __init__(self, type, age, date, base_price):
        self.type = type
        self.age = age
        self.date = datetime.fromisoformat(date) if date else None
        self.base_price = base_price

    @property
    def price(self):
        return -1


@app.route("/prices", methods=['GET'])
def prices():
    response = {}
    global connection
    if connection is None:
        connection = create_lift_pass_db_connection(connection_options)

    cursor = connection.cursor()
    cursor.execute(
        'SELECT cost FROM base_price '
        'WHERE type = ? ', (request.args['type'],)
    )
    row = cursor.fetchone()
    lift_pass = LiftPass(
        type=request.args.get('type'),
        age=request.args.get('age', type=int),
        date=request.args.get('date'),
        base_price=row[0],
    )
    if lift_pass.age and lift_pass.age < 6:
        response["cost"] = 0
    else:
        if lift_pass.type and lift_pass.type != "night":
            cursor = connection.cursor()
            cursor.execute('SELECT * FROM holidays')  # <-- this is where we left off
            is_holiday = False
            reduction = 0
            for row in cursor.fetchall():
                holiday = datetime.fromisoformat(row[0])
                if d := lift_pass.date:
                    if d.year == holiday.year and d.month == holiday.month and holiday.day == d.day:
                        is_holiday = True
            if not is_holiday and lift_pass.date and lift_pass.date.weekday() == 0:
                reduction = 35

            # TODO: apply reduction for others
            if lift_pass.age and lift_pass.age < 15:
                response['cost'] = math.ceil(lift_pass.base_price * .7)
            else:
                if not lift_pass.age:
                    cost = lift_pass.base_price * (1 - reduction / 100)
                    response['cost'] = math.ceil(cost)
                else:
                    if lift_pass.age and lift_pass.age > 64:
                        cost = lift_pass.base_price * .75 * (1 - reduction / 100)
                        response['cost'] = math.ceil(cost)
                    elif lift_pass.age:
                        cost = lift_pass.base_price * (1 - reduction / 100)
                        response['cost'] = math.ceil(cost)
        else:
            if lift_pass.age and lift_pass.age >= 6:
                if lift_pass.age > 64:
                    response['cost'] = math.ceil(lift_pass.base_price * .4)
                else:
                    response['cost'] = lift_pass.base_price
            else:
                response['cost'] = 0

    return response


@app.route("/prices", methods=['PUT'])
def put_price(connection):
    lift_pass_cost = request.args["cost"]
    lift_pass_type = request.args["type"]
    cursor = connection.cursor()
    cursor.execute('INSERT INTO `base_price` (type, cost) VALUES (?, ?) ' +
                   'ON DUPLICATE KEY UPDATE cost = ?', (lift_pass_type, lift_pass_cost, lift_pass_cost))
    return {}


if __name__ == "__main__":
    app.run(port=3005)
