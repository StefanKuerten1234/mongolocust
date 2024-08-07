import os

DEFAULTS = {'DB_NAME': 'loadtest',
            'COLLECTION_NAME': 'measurements_ts',
            'CLUSTER_URL': f'mongodb+srv://stefan:xxx@atlascluster.am7mj2q.mongodb.net/?w=1',
            'DOCS_PER_BATCH': 50,
            'INSERT_WEIGHT': 0,
            'FIND_WEIGHT': 0,
            'BULK_INSERT_WEIGHT': 100,
            'AGG_PIPE_WEIGHT': 0}


def init_defaults_from_env():
    for key in DEFAULTS.keys():
        value = os.environ.get(key)
        if value:
            DEFAULTS[key] = value


# get the settings from the environment variables
init_defaults_from_env()
