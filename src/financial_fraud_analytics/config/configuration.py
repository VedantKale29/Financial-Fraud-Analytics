from financial_fraud_analytics.constants.constants import *
from financial_fraud_analytics.utils.utils import read_yaml


class ConfigurationManager:

    def __init__(self):

        self.config = read_yaml(CONFIG_FILE_PATH)
        self.schema = read_yaml(SCHEMA_FILE_PATH)

    def get_config(self):

        return self.config

    def get_schema(self):

        return self.schema