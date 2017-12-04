import re
import os
import csv
import json

from flask import Flask, request, jsonify
from pymongo import MongoClient
from vincenty import vincenty


app = Flask(__name__)

@app.route('/')
def index():

    """
        home page

        :return: content
        :rtype: str

    """
    return '<h2>Hello There!</h2>'


@app.route('/suggestions')
def suggestions(methods=['GET']):

    """
        /suggestions page

        :param: only get request can be accepted
        :return: the list of suggestions or input format
        :rtype: json message
        :raises ValueError: if the required parameter 'name' is not found in get request

    """
    data = request.args.get('q')
    if not data:
        return "<h3>Input format:</h3><b><br /></b><h4>'/suggestions?q={\"name\":\"city_name\"}'</h4><br / ><h4>or</h4><br /><h4>'/suggestions?q={\"name\":\"city_name\",\"lat\":\"latitude_number\",\"long\":\"longitude_number\"}'</h4>"

    name = get_required_parameter('name', data)
    latitude = get_optional_parameter('lat', data, default_value=False)
    longitude = get_optional_parameter('long', data, default_value=False)
    regex = fuzzy_matching(name)
    raw_suggestions = read_data(regex)

    if latitude != False and longitude != False:
        raw_suggestions = read_data(regex, input_latitude=latitude, input_longitude=longitude)

    suggested_cities = proportion_of_input_string_in_suggested_city_name(name, raw_suggestions)

    return return_message(suggested_cities)

def return_message(three_suggested_cities):

    """
        sort the return message by descending score and retrun the json format

        :param: dictionary of three top suggested cities
        :return: the json message of top suggested cities (max 3)
        :rtype: json message

    """
    raw_cities_data = []
    for key in three_suggested_cities:
        raw_cities_data.append(three_suggested_cities[key])
    cities_data = sorted(raw_cities_data, key=lambda k: k['score'], reverse=True)

    message = {"suggestions": cities_data}
    return jsonify(message)

def fuzzy_matching(input_string):

    """
        matching example: ".*?".join("Mon") ==> 'M.*?o.*?n'
        :param: partial city name(str) from get request
        :return the regex
        :rtype: regex_object

    """
    pattern = '.*?'.join(input_string.title())
    return re.compile(pattern)


def read_data(input_regex, input_latitude=False, input_longitude=False):

    """
        get top suggested city data dictionary
        if latitiude and longitude is provided ==> return the nearest matched cities.
        if latitiude and longitude is not provided ==> return the matched cities with large population
        :param: regex pattern of the input (partial) city name from get request
        :param: float of latitude
        :param: float of longitude
        :return: dictionary of suggested cities (max 3)
        :rtype: dict
    """

    client = MongoClient('mongodb://heroku_h4rdb774:rv94dp8svpjg2butkq3avh876s@ds123976.mlab.com:23976/heroku_h4rdb774')
    db = client.heroku_h4rdb774
    collection = db.cities

    if input_latitude and input_longitude:
        data = collection.find({"name":input_regex}, {"name":1, "lat":1, "long":1, "_id":0})
        return calculate_the_nearest_3_cities(input_latitude, input_longitude, data)
    else:
        data = collection.find({"name":input_regex}, {"name":1, "lat":1, "long":1, "population":1, "_id":0})
        return calculate_3_biggest_cities(data)


def calculate_3_biggest_cities(suggested_data):

    """
        get most suggested cities based on population of the potiential matched cities

        :param: suggested_data list of dictionary of the matched cities info
        :return the dictionary of dictionary of cities with the largest population (3 max)
        :rtype: dict of dict

    """

    biggest_cities = [float("-inf"), float("-inf"), float("-inf")]
    ret_dict = {}
    for d in suggested_data:
        if d['population'] > biggest_cities[0]:
            biggest_cities = [d['population'], biggest_cities[0], biggest_cities[1]]
            ret_dict['top'] = {'name': d['name'], 'latitude': d['lat'], 'longitude': d['long'], 'score': 1}
        elif d['population'] > biggest_cities[1]:
            biggest_cities = [biggest_cities[0],d['population'], biggest_cities[1]]
            ret_dict['second'] = {'name': d['name'], 'latitude': d['lat'], 'longitude': d['long'], 'score': 0.9}
        elif d['population'] > biggest_cities[2]:
            biggest_cities = [biggest_cities[0],biggest_cities[1], d['population']]
            ret_dict['third'] = {'name': d['name'], 'latitude': d['lat'], 'longitude': d['long'], 'score': 0.8}

    return ret_dict


def calculate_the_nearest_3_cities(input_latitude, input_longitude, suggested_data):

    """
        get most suggested cities based on vincenty distance of the potiential matched cities

        :param: suggested_data list of dictionary of the matched cities info
        :return the dictionary of dictionary of cities with the smallest distance
        :rtype: dict of dict

    """


    nearest_3_cities = [float("-inf"), float("-inf"), float("-inf")]
    ret_dict = {}
    input_city = (input_latitude, input_longitude)
    for d in suggested_data:
        suggested_city = (d['lat'], d['long'])
        distance = vincenty(suggested_city, input_city)
        if distance > nearest_3_cities[0]:
            nearest_3_cities = [distance, nearest_3_cities[0], nearest_3_cities[1]]
            ret_dict['top'] = {'name': d['name'], 'latitude': d['lat'], 'longitude': d['long'], 'score': 1}
        elif distance > nearest_3_cities[1]:
            nearest_3_cities = [nearest_3_cities[0], distance, nearest_3_cities[1]]
            ret_dict['second'] = {'name': d['name'], 'latitude': d['lat'], 'longitude': d['long'], 'score': 0.9}
        elif distance > nearest_3_cities[2]:
            nearest_3_cities = [nearest_3_cities[0], nearest_3_cities[1], distance]
            ret_dict['third'] = {'name': d['name'], 'latitude': d['lat'], 'longitude':d['long'], 'score': 0.8}

    return ret_dict

def proportion_of_input_string_in_suggested_city_name(input_string, three_suggested_data):

    """
        calculate the proportion of the number of character in partial input city nameand matched city name.
        recalulte the score
        :param: input city name
        :param: dictionary of dictionary of suggested citt info
        :return: dict of dict

    """

    for key in three_suggested_data:
        suggested_city_name = three_suggested_data[key]['name']
        suggested_ratio = float(len(input_string))/float(len(suggested_city_name))
        raw_score = three_suggested_data[key]['score'] * suggested_ratio
        score_4_decimal = "{0:.4f}".format(raw_score)
        three_suggested_data[key]['score'] = score_4_decimal

    return three_suggested_data


def get_required_parameter(param_name, data):

    """
        :param: string of parameter's name
        :param: data from get request
        :return: input partial city name
        :rtype: unicode

    """

    raw_data = json.loads(data)
    if param_name not in raw_data:
        raise Exception('Error, Parameter \'%s\' is required for this call!' % (param_name))

    value = raw_data[param_name]

    if value == '':
        raise Exception('Error, Parameter \'%s\' is required for this call!' % (param_name))


    return unicode(value)

def get_optional_parameter(param_name, data, default_value=False):

    """
        :param: string of parameter's name
        :param: data from get request
        :retrun: input lattitue value and longtitude value or default value
        :rtype: float

    """
    raw_data = json.loads(data)
    value = default_value
    if param_name in raw_data:
        value = float(raw_data[param_name])

    return value


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0',port=port)
    # app.run(debug=True)

