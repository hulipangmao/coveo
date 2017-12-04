from coveo_code_challenge import app
import unittest
from pymongo import MongoClient

class FlaskTestCase(unittest.TestCase):

    def test_index(self):
        tester = app.test_client(self)
        response = tester.get('/suggestions?q={"name":"Montr"}', content_type='html/text')
        self.assertEqual(response.status_code, 200)

    def test_suggestions(self):
        city_names = self.get_city_names()
        tester = app.test_client(self)
        for name in city_names:
            # request = "/suggestions?q={\"name\":\"%s\"}" % (name['name'])
            request = "/suggestions?q={\"name\":\"%s\",\"lat\":\"%s\",\"long\":\"%s\"}" %(name['name'], name['lat'], name['long'])
            response = tester.get(request, content_type='html/text')
            is_true = self.assertIn(str(name['name']), response.data)
            if not is_true:
                print name['name']
                continue

    def get_city_names(self):
        client = MongoClient('mongodb://heroku_h4rdb774:rv94dp8svpjg2butkq3avh876s@ds123976.mlab.com:23976/heroku_h4rdb774')
        db = client.heroku_h4rdb774
        collection = db.cities
        data = collection.find({}, {"name":1,"lat":1,"long":1,"_id":0})
        return data


if __name__ == '__main__':
    unittest.main()
