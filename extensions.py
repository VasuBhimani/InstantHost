# from flask_pymongo import PyMongo

# mongo = PyMongo()
from flask_pymongo import PyMongo
import certifi

mongo = PyMongo(tlsCAFile=certifi.where())
