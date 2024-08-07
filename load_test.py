from locust import between

from mongo_user import MongoUser, mongodb_task
from settings import DEFAULTS
from datetime import datetime

import pymongo
import random

# number of cache entries for queries
NAMES_TO_CACHE = 1000


class MongoSampleUser(MongoUser):
    """
    Generic sample mongodb workload generator
    """
    # no delays between operations
    wait_time = between(0.0, 0.0)

    def __init__(self, environment):
        super().__init__(environment)
        self.name_cache = []

    def generate_new_document(self):
        """
        Generate a new sample document
        """
        document = {
            # Omit id, since it is generated by Mongo
            'ts': datetime.now(),
            'vehicleid': self.faker.pyint(min_value=0, max_value=99_999),
            'temperature': self.faker.pyfloat(min_value=-20, max_value=50, right_digits=1),
            'operatingtime': self.faker.pyint(min_value=0, max_value=100_000),
            'fuelusage': self.faker.pydecimal(min_value=0, max_value=50, right_digits=2),
            'front_linkage_position': self.faker.pyint(min_value=0, max_value=360),
            'drivingspeed': self.faker.pyint(min_value=0, max_value=80),
            'enginestate': self.faker.pyint(min_value=0, max_value=1),
            'autopilot_system_state': self.faker.pyint(min_value=0, max_value=1),
            'engine_load': self.faker.pydecimal(min_value=0, max_value=100, right_digits=1),
            'position': self.faker.location_on_land(coords_only='true'),
            'altitude': self.faker.pyfloat(min_value=-414, max_value=8849, right_digits=1),
            'engine_rotation': self.faker.pydecimal(min_value=0, max_value=3000, right_digits=2),
            'front_pme_shaft': self.faker.pydecimal(min_value=0, max_value=50, right_digits=2),
            'rear_linkage_position': self.faker.pyint(min_value=0, max_value=360),
            'four_wheel_driving_state': self.faker.random_element(elements=['enabled', 'disabled']),
            'fuel_tank_level': self.faker.pyint(min_value=0, max_value=2000),
            'last_error_msg': self.faker.sentence(),
            'engine_temperature': self.faker.pyfloat(min_value=-40, max_value=300, right_digits=1),
            'connection_state': self.faker.random_element(elements=['online', 'offline']),
            'lte_connection_level': self.faker.pydecimal(min_value=0, max_value=100, right_digits=2),
            'mode': self.faker.random_element(
                elements=['Light Speed', 'Ridiculous Speed', 'Ludicrous Speed', 'Plaid Speed'])
        }
        return document

    @mongodb_task(weight=int(DEFAULTS['AGG_PIPE_WEIGHT']))
    def run_aggregation_pipeline(self):
        """
        Run an aggregation pipeline on a secondary node
        """

        set_columns = {'$set': {'location': {'type': 'Point', 'coordinates': [{'$toDouble': {'$arrayElemAt': ['$position', 1]}}, {'$toDouble': {'$arrayElemAt': ['$position', 0]}}]}}}
        unset_columns = {'$unset': ['position']}

        pipeline = [set_columns, unset_columns]

        # make sure we fetch everything by explicitly casting to list
        # use self.collection instead of self.collection_secondary to run the pipeline on the primary
        return list(self.collection_secondary.aggregate(pipeline))

    def on_start(self):
        """
        Executed every time a new test is started - place init code here
        """
        # prepare the collection
        index_vehicleid = pymongo.IndexModel([('vehicleid', pymongo.ASCENDING)], name="idx_vehicleid")
        index_ts = pymongo.IndexModel([('ts', pymongo.ASCENDING)], name="idx_ts")
        index_location = pymongo.IndexModel([('location', '2dsphere')], name="idx_location_2dsphere")
        index_ts_vehicleid = pymongo.IndexModel([('ts', pymongo.ASCENDING), ('vehicleid')], name="idx_ts_vehicle")
        index_vehicleid_enginestate = pymongo.IndexModel([('vehicleid'), ('enginestate')], name="idx_vehicle_status")
        self.collection, self.collection_secondary = self.ensure_collection(DEFAULTS['COLLECTION_NAME'],
                                                                            [index_vehicleid, index_ts, index_location, index_ts_vehicleid, index_vehicleid_enginestate])

        self.name_cache = []

    @mongodb_task(weight=int(DEFAULTS['INSERT_WEIGHT']))
    def insert_single_document(self):
        document = self.generate_new_document()

        # cache the first_name, last_name tuple for queries
        cached_names = (document['first_name'], document['last_name'])
        if len(self.name_cache) < NAMES_TO_CACHE:
            self.name_cache.append(cached_names)
        else:
            if random.randint(0, 9) == 0:
                self.name_cache[random.randint(0, len(self.name_cache) - 1)] = cached_names

        self.collection.insert_one(document)

    @mongodb_task(weight=int(DEFAULTS['FIND_WEIGHT']))
    def find_document(self):
        # at least one insert needs to happen
        if not self.name_cache:
            return

        # find a random document using an index
        cached_names = random.choice(self.name_cache)
        self.collection.find_one({'first_name': cached_names[0], 'last_name': cached_names[1]})

    @mongodb_task(weight=int(DEFAULTS['BULK_INSERT_WEIGHT']), batch_size=int(DEFAULTS['DOCS_PER_BATCH']))
    def insert_documents_bulk(self):
        self.collection.insert_many(
            [self.generate_new_document() for _ in
             range(int(DEFAULTS['DOCS_PER_BATCH']))], ordered=False)
