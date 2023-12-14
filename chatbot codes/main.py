from flask import Flask, jsonify, render_template, request, after_this_request
import requests
from functions.flight.flight_sentiment import start_sentiment
import datetime
import csv
from datetime import datetime, date, timedelta
import boto3
import random
import string

app = Flask(__name__)

### -------------- AIRLINE PROJECT ---------------- ######

# ---- CREATE NEW CUSTOMER

aws_key = 'enter_key_id'
aws_secret = 'enter_secret_key'


@app.route('/airline/new_customer', methods=['POST'])
def post_airline_put_new_customer():

    if request.method == 'POST':
        data1 = request.get_json()
        aws_access_key_id = aws_key
        aws_secret_access_key = aws_secret
        region_name = 'ca-central-1'

        dynamo_client = boto3.client('dynamodb', region_name=region_name,
                                     aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
        table_name = 'customers'

        current_time = datetime.now()

        response = dynamo_client.scan(TableName=table_name)
        data = response['Items']

        while 'LastEvaluatedKey' in response:
            response = dynamo_client.scan(
                TableName=table_name, ExclusiveStartKey=response['LastEvaluatedKey'])
            data.extend(response['Items'])

        characters = string.digits + string.ascii_uppercase

        random_id = ''.join(random.choice(characters)for _ in range(5))
        item = {
            "customer_id": {'S': str(random_id)},
            "email": {'S': data1["email"]},
            "name": {'S': data1["name"]},
            "timestamp": {'S': str(current_time)},
        }

        response_1 = dynamo_client.put_item(
            TableName=table_name, Item=item)

        customer_resp = [response_1["ResponseMetadata"]["HTTPStatusCode"],
                         item["customer_id"], data1["fnumber"], data1["fcost"], data1["ticket_id"]]

        # ------> New Transaction
        def post_airline_put_new_trans(customer_id, flight_id, fcost, ticket_num):
            try:

                table_name2 = 'transactions'
                current_time = datetime.now()
                response = dynamo_client.scan(TableName=table_name)
                data = response['Items']

                while 'LastEvaluatedKey' in response:
                    response = dynamo_client.scan(
                        TableName=table_name2, ExclusiveStartKey=response['LastEvaluatedKey'])
                    data.extend(response['Items'])

                characters1 = string.digits + string.ascii_uppercase
                random_id1 = ''.join(random.choice(characters1)
                                     for _ in range(5))

                if 'cancelled' in data1:
                    cancelled = "yes"
                else:
                    cancelled = "no"

                item = {
                    "trans_id": {'S': str(random_id1)},
                    'customer_id': {'S': str(customer_id['S'])},
                    'flight_id': {'S': str(flight_id)},
                    "timestamp": {'S': str(current_time)},
                    "cost": {'S': str(fcost)},
                    "cancelled": {'S': cancelled},
                    "ticket_num": {'S': ticket_num},
                }

                # Use put_item to add the new user to the table
                response_2 = dynamo_client.put_item(
                    TableName=table_name2, Item=item)

                return int(response_2["ResponseMetadata"]["HTTPStatusCode"])

            except Exception as e:
                return {"error": "Failed to upload TRANSACTION" + str(e)}, 500
        try:
            if int(customer_resp[0]) == 200:
                trans_resp = post_airline_put_new_trans(
                    customer_resp[1], customer_resp[2], customer_resp[3], customer_resp[4])
                return {"res": trans_resp}
            else:
                return {"err": "Customer Responce NOT 200"}

        except Exception as e:
            return {"error": "Customer Responce NOT 200-- EXCEPT" + str(e)}, 500


# ----  CREATE NEW SENTIMENT / STORE REVIEWS

@app.route('/airline/sentiment', methods=['POST'])
def post_airline_sentiments():

    if request.method == 'POST':
        data1 = request.get_json()
        input_email = data1["email"]
        ticket = data1["ticket"]
        review = data1["review"]
        plan = data1["plan"]
        aws_access_key_id = aws_key
        aws_secret_access_key = aws_secret
        region_name = 'ca-central-1'

        dynamo_client = boto3.client('dynamodb', region_name=region_name,
                                     aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

        table_name = 'customers'
        current_time = datetime.now()

        response = dynamo_client.get_item(
            TableName=table_name,
            Key={'email': {'S': str(input_email)}}
        )

        email_list = []

        if 'Item' in response:
            email_attribute = response['Item'].get('email')

            if email_attribute:
                email_value = email_attribute.get('S')
                if email_value and email_value.strip().lower() == str(input_email).strip().lower():
                    customer_id_attribute = response['Item'].get('customer_id')
                    if customer_id_attribute:
                        customer_id = customer_id_attribute.get('S')
                        email_list.append(customer_id)
            if plan == 0:
                # ----->> Transaction
                response_scan_info = dynamo_client.scan(TableName="transactions",
                                                        FilterExpression='#customer_id = :customer_id and #ticket_num = :ticket',
                                                        ExpressionAttributeNames={
                                                            '#customer_id': 'customer_id',
                                                            '#ticket_num': 'ticket_num'
                                                        },
                                                        ExpressionAttributeValues={
                                                            ':customer_id': {'S': customer_id},
                                                            ':ticket': {'S': ticket}
                                                        }
                                                        )

                if 'Items' in response_scan_info:
                    if plan == 0:

                        senitment = start_sentiment(review)

                        review_response = dynamo_client.scan(
                            TableName="reviews")
                        review_id = int(review_response["Count"]) + 1
                        item = {
                            "review": {'S': str(review)},
                            'customer_id': {'S': str(customer_id)},
                            'timestamp': {'S': str(current_time)},
                            "sentiment": {'S': str(senitment)},
                            "review_id": {'S': str(review_id)}
                        }

                        # Use put_item to add the new user to the table
                        response_2 = dynamo_client.put_item(
                            TableName="reviews", Item=item)

                        return jsonify([int(response_2["ResponseMetadata"]["HTTPStatusCode"])])

                    else:
                        return jsonify(["yes"])
                else:
                    return jsonify(["Only valid customers may leave a review,please check your email and/or your ticket number."])
            else:
                return jsonify(["yes"])
        else:
            return jsonify(["Only valid customers may leave a review,please check your email"])

# ----  GET FLIGHTS INFORMATION


@app.route('/airline/pull_flights', methods=['POST'])
def post_airline_pull_flghts():
    if request.method == 'POST':
        try:

            data1 = request.get_json()
            aws_access_key_id = aws_key
            aws_secret_access_key = aws_secret
            region_name = 'ca-central-1'

            dynamo_client = boto3.client('dynamodb', region_name=region_name,
                                         aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

            table_name = 'flights'

            response = dynamo_client.scan(TableName=table_name)
            data = response['Items']

            while 'LastEvaluatedKey' in response:
                response = dynamo_client.scan(
                    TableName=table_name, ExclusiveStartKey=response['LastEvaluatedKey'])
                data.extend(response['Items'])

            arrival = data1["arrival"]
            depart = data1["depart"]
            aTime = data1["aTime"]
            dTime = data1["dTime"]

            filtered_data = []

            for item in data:
                if (
                    item["arrival"]["S"].strip() == arrival.strip()
                    and item["depart"]["S"].strip() == depart.strip()
                    and item["aTime"]["S"].strip() == aTime.strip()
                    and item["dTime"]["S"].strip() == dTime.strip()
                ):
                    filtered_data.append(item)

            return {"res": filtered_data}

        except Exception as e:
            return {"error": "try/except failed to get user: " + str(e)}, 500

    else:
        return {
            'statusCode': 400,
            'body': 'Method not 0'
        }

# ---------> CHECK FLIGHT DATES


@app.route('/airline/check_dates', methods=['POST'])
def get_check_dates():
    if request.method == 'POST':
        info = request.get_json()
        start_date = str(info["start"])
        end_date = str(info["end"])
        start_date_final = datetime.strptime(start_date, '%Y/%m/%d')
        end_date_final = datetime.strptime(end_date, '%Y/%m/%d')

        if start_date_final > end_date_final:
            return jsonify(100)
        else:
            return jsonify(200)

# ---------> CHECK FLIGHT TIMES


@app.route('/flight_times', methods=['POST'])
def get_flight_times():
    if request.method == 'POST':

        info = request.get_json()
        flight_data = []

        with open('./data/Flight_details.csv', newline='') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                flight_data.append(row)

        arrival = str(info["arrival"]).strip().lower()
        depart = str(info["depart"]).strip().lower()

        matching_flights = []

        for flight in flight_data:
            if arrival == str(flight["Arrival_city"]).strip().lower() and depart == str(flight["Departing_city"]).strip().lower():
                matching_flights.append({
                    "dTime": flight["Departure_time"],
                    "aTime": flight["Arrival_time"],
                    "arrival": arrival,
                    "depart": depart,
                    "airline": flight["Airline"]
                })

        if matching_flights:
            return jsonify(matching_flights), 200
        else:
            return jsonify(["No available flights for the specified locations. Please re-check."]), 404


# ----> GET FLIGHT NUMBERS

@app.route('/fnumber', methods=['POST'])
def get_flight_fnumber():
    if request.method == 'POST':
        info = request.get_json()

        arrival = str(info["arrival"]).strip().lower()
        depart = str(info["depart"]).strip().lower()
        dtime_input = str(info["dtime"]).strip().lower()
        atime_input = str(info["atime"]).strip().lower()

        flight_data = []
        with open('./data/Flight_details.csv', newline='') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                flight_data.append(row)

        matching_fNumbers = []

        for flight in flight_data:
            if str(flight["Departing_city"]).lower().strip() == depart and str(flight["Arrival_city"]).lower().strip() == arrival:
                dTime_csv = str(flight["Departure_time"]).strip().lower()
                aTime_csv = str(flight["Arrival_time"]).strip().lower()

                if dtime_input == dTime_csv and atime_input == aTime_csv:

                    matching_fNumbers.append(flight["Flight_number"])
                    matching_fNumbers.append(flight["Cost"])

        if matching_fNumbers:
            return jsonify(matching_fNumbers)
        else:
            return jsonify(["No matching flights found"]), 404


# ----Get Users Information


def read_flight(flight_id, finish):
    flight_data = []
    final_obj = []
    with open('./data/Flight_details.csv', newline='') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            flight_data.append(row)

    for flight in flight_data:
        if str(flight["Flight_number"]).strip() == str(flight_id).strip():

            final_obj.append(finish[0])
            final_obj.append(flight["Arrival_city"])
            final_obj.append(flight["Departing_city"])
            final_obj.append(flight["Flight_number"])
            final_obj.append(flight["Arrival_time"])
            final_obj.append(flight["Departure_time"])
            final_obj.append(flight["Cost"])
            final_obj.append(200)
    return final_obj
    # return final_obj


@app.route('/airline/get_customer', methods=['POST'])
def post_airline_get_customer():
    if request.method == 'POST':
        #
        try:
            data = request.get_json()
            aws_access_key_id = aws_key
            aws_secret_access_key = aws_secret
            region_name = 'ca-central-1'

            dynamo_client = boto3.client('dynamodb', region_name=region_name,
                                         aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

            finish = []

            table_name = 'customers'
            user_email = data['email']
            ticket = data['ticket']

            response = dynamo_client.get_item(
                TableName=table_name,
                Key={'email': {'S': str(user_email)}}
            )

            if 'Item' in response:
                item = response['Item']

                name_val = item["name"]["S"]
                customer_id = item["customer_id"]["S"]
                finish.append(str(name_val))

            #     # ----->> Transaction
                response_scan_info = dynamo_client.scan(TableName="transactions",
                                                        FilterExpression='#customer_id = :customer_id and #ticket_num = :ticket',
                                                        ExpressionAttributeNames={
                                                            '#customer_id': 'customer_id',
                                                            '#ticket_num': 'ticket_num'
                                                        },
                                                        ExpressionAttributeValues={
                                                            ':customer_id': {'S': customer_id},
                                                            ':ticket': {'S': ticket}
                                                        }
                                                        )

                if 'Items' in response_scan_info:

                    items_dict = {str(index): item for index, item in enumerate(
                        response_scan_info['Items'])}
                    first_item = items_dict.get("0", {})
                    flight_id = first_item.get("flight_id", {}).get("S")

                    val = read_flight(str(flight_id), finish)

                    responding = val
                else:
                    responding = [
                        "Unable to get your flight information. Please check your email and/or your ticket number."]

                return jsonify(responding)
            else:
                return jsonify(["Unable to get your flight information. Please check your email and/or your ticket number."])

        except Exception as e:
            return jsonify(["try/except failed to get user: " + str(e), 500])

    else:
        return {
            'statusCode': 400,
            'body': 'Method not 0'
        }


# -----PASSPORT IMAGE UPLOAD
@app.route('/airline/passport_image', methods=['POST'])
def upload_pass_image():
    if request.method == 'POST':
        # --- Level 1 ---
        try:

            passport_res = request.get_json()
            url = passport_res["url"]
            hash = passport_res["email"]
            image_data = requests.get(url)
        except Exception as e:
            return {"error": "Failed to retrieve image data from the URL."}, 500

        # --- Level 2 ---
        try:
            headers = {
                'Content-Type': 'image/*',
            }
            s3_url = f"https://980twspdh8.execute-api.ca-central-1.amazonaws.com/production/passport-image-rm/img_{hash}.jpg"
            s3_response = requests.put(
                s3_url, data=image_data.content, headers=headers)

            if s3_response.status_code == 200:
                final = 1
                return {"res": final}
            else:
                return {"error": f"Failed to upload image to S3. Status code: {s3_response.status_code}"}, 500
        except Exception as e:
            return {"error": "Failed to upload image to S3: " + str(e)}, 500
    else:
        return "POST request ONLY"


# ------- ticket number generator
@app.route('/airline/ticket_num', methods=['GET'])
def get_ticket_num():
    if request.method == 'GET':
        # --- Level 1 ---
        try:
            import random
            import string

            # printing letters
            letters = string.ascii_uppercase
            val = ''.join(random.choice(letters) for i in range(10))
            return [val]
        except Exception as e:
            return {"error": "Failed to create ticket number " + str(e)}, 500
    else:
        return "POST request ONLY"


# ------- Cancel Flight
@app.route('/airline/cancel_flight', methods=['POST'])
def cancel_flight():
    if request.method == 'POST':

        data = request.get_json()
        cancel_ticket = str(data["ticket"]).strip()
        aws_access_key_id = aws_key
        aws_secret_access_key = aws_secret
        region_name = 'ca-central-1'

        dynamo_client = boto3.client('dynamodb', region_name=region_name,
                                     aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

        response_scan = dynamo_client.scan(
            TableName="transactions",
            FilterExpression='ticket_num = :ticket and cancelled = :status',
            ExpressionAttributeValues={
                ':ticket': {'S': cancel_ticket},
                ':status': {'S': 'no'}
            }
        )

        if 'Items' in response_scan:
            items = response_scan.get('Items', [])
            if items:
                timestamp_str = items[0].get('timestamp', {}).get('S', '')
                if timestamp_str:
                    timestamp = datetime.strptime(
                        timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
                    current_time = datetime.now()

                    time_difference = current_time - timestamp

                    if time_difference > timedelta(minutes=3):
                        responding = "More than 24 Hours have passed. You do not qualify for a refund"
                    else:
                        if items:
                            trans_id_value = items[0].get(
                                'trans_id', {}).get('S', '')

                            response_update = dynamo_client.update_item(
                                TableName="transactions",
                                Key={
                                    "trans_id": {'S': str(trans_id_value)}
                                },
                                UpdateExpression='SET cancelled = :val',
                                ConditionExpression='ticket_num = :ticket',
                                ExpressionAttributeValues={
                                    ':val': {'S': 'yes'},
                                    ':ticket': {'S': cancel_ticket}
                                })

                            responding = 200
                        else:
                            responding = "Unable to cancel your ticket. Either ticket not found or already cancelled. Please check ticket number. "

                        if response_update['ResponseMetadata']['HTTPStatusCode'] == 200:

                            responding = 200
                        else:
                            responding = "failed to Cancel ticket"

                    return jsonify([responding])
                else:
                    return jsonify(["no timestamp"])
            else:
                return jsonify(["Unable to cancel your ticket. Either ticket not found or already cancelled. Please check ticket number. "])
        else:
            return jsonify(["Unable to cancel your ticket. Either ticket not found or already cancelled. Please check ticket number. "])
    else:
        return jsonify(["No matching flights found."])


#  ------ Real Time Maps
@app.route('/get_plane_data', methods=['POST'])
def plane_data_style():
    if request.method == 'POST':

        element = request.get_json()
        user_ticket = str(element["ticket"]).strip()
        plan = element["plan"]

        aws_access_key_id = aws_key
        aws_secret_access_key = aws_secret
        region_name = 'ca-central-1'

        dynamo_client = boto3.client('dynamodb', region_name=region_name,
                                     aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

        response_scan = dynamo_client.scan(
            TableName="transactions",
            FilterExpression='ticket_num = :ticket',
            ExpressionAttributeValues={
                ':ticket': {'S': str(user_ticket)}
            }
        )

        if 'Items' in response_scan:

            if plan == 0:
                items = response_scan['Items'][0]['flight_id']['S']
                if items:

                    def find_flight_info(csv_file, fnumber):
                        with open(csv_file, 'r') as file:
                            reader = csv.DictReader(file)
                            for row in reader:
                                if row['Flight_number'] == fnumber:
                                    return {'depart': row['Departing_city'], 'arrival': row['Arrival_city']}
                        return None

                    csv_file_path = "./data/Flight_details.csv"
                    given_fnumber = items

                    result = find_flight_info(csv_file_path, given_fnumber)

                    if result:
                        if result['depart'] == "Los Angeles" and result['arrival'] == "New York":
                            return ["https://automations-368019.nn.r.appspot.com/lax_ny"]
                        elif result['depart'] == "Los Angeles" and result['arrival'] == "Miami":
                            return ["https://automations-368019.nn.r.appspot.com/lax_miami"]
                        elif result['depart'] == "Los Angeles" and result['arrival'] == "London":
                            return ["https://automations-368019.nn.r.appspot.com/lax_ldn"]

                        elif result['depart'] == "New York" and result['arrival'] == "Los Angeles":
                            return ["https://automations-368019.nn.r.appspot.com/ny_lax"]
                        elif result['depart'] == "New York" and result['arrival'] == "Miami":
                            return ["https://automations-368019.nn.r.appspot.com/ny_miami"]
                        elif result['depart'] == "New York" and result['arrival'] == "London":
                            return ["https://automations-368019.nn.r.appspot.com/ny_ldn"]

                        elif result['depart'] == "Miami" and result['arrival'] == "Los Angeles":
                            return ["https://automations-368019.nn.r.appspot.com/miami_lax"]
                        elif result['depart'] == "Miami" and result['arrival'] == "New York":
                            return ["https://automations-368019.nn.r.appspot.com/miami_ny"]
                        elif result['depart'] == "Miami" and result['arrival'] == "London":
                            return ["https://automations-368019.nn.r.appspot.com/miami_ldn"]

                        elif result['depart'] == "London" and result['arrival'] == "Los Angeles":
                            return ["https://automations-368019.nn.r.appspot.com/ldn_lax"]
                        elif result['depart'] == "London" and result['arrival'] == "New York":
                            return ["https://automations-368019.nn.r.appspot.com/ldn_ny"]
                        elif result['depart'] == "London" and result['arrival'] == "Miami":
                            return ["https://automations-368019.nn.r.appspot.com/ldn_miami"]
                    else:
                        return ["Flight not found."]
                else:
                    return ["No ticket"]
            if plan == 1:
                return ["yes"]
        else:
            return ["NOT 200"]


@app.route('/miami_lax')
def index11():
    return render_template('miami_lax.html')


@app.route('/miami_ny')
def index12():
    return render_template('miami_ny.html')


@app.route('/miami_ldn')
def index13():
    return render_template('miami_london.html')


@app.route('/lax_ny')
def index51():
    return render_template('lax_ny.html')


@app.route('/lax_miami')
def index52():
    return render_template('lax_miami.html')


@app.route('/lax_ldn')
def index53():
    return render_template('lax_london.html')


@app.route('/ny_lax')
def index54():
    return render_template('ny_lax.html')


@app.route('/ny_miami')
def index55():
    return render_template('ny_miami.html')


@app.route('/ny_ldn')
def index56():
    return render_template('ny_london.html')


@app.route('/ldn_lax')
def index57():
    return render_template('london_lax.html')


@app.route('/ldn_miami')
def index58():
    return render_template('london_miami.html')


@app.route('/ldn_ny')
def index59():
    return render_template('london_ny.html')


if __name__ == '__main__':
    app.run()
