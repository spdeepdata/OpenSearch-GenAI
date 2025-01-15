#multitenant_data_loader
from elasticsearch import Elasticsearch
import logging
from datetime import datetime
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiTenantDataLoader:
    def __init__(self, host: str = "http://localhost:9200"):
        self.es = Elasticsearch([host])
        self.tenant1_index = "tenant1_equipment"
        self.tenant2_index = "tenant2_equipment"
        self.marketplace_index = "marketplace_equipment"

    def create_indices(self):
        """Create indices with proper mappings"""
        mapping = {
            "mappings": {
                "properties": {
                    "tenant_id": {"type": "keyword"},
                    "name": {"type": "text"},
                    "description": {"type": "text"},
                    "category": {"type": "keyword"},
                    "subcategory": {"type": "keyword"},
                    "manufacturer": {"type": "keyword"},
                    "model": {"type": "keyword"},
                    "specifications": {
                        "type": "nested",
                        "properties": {
                            "parameter": {"type": "keyword"},
                            "value": {"type": "float"},
                            "unit": {"type": "keyword"}
                        }
                    },
                    "location": {
                        "type": "nested",
                        "properties": {
                            "country": {"type": "keyword"},
                            "city": {"type": "keyword"},
                            "availability": {"type": "keyword"}
                        }
                    },
                    "price": {
                        "type": "nested",
                        "properties": {
                            "value": {"type": "float"},
                            "currency": {"type": "keyword"}
                        }
                    },
                    "condition": {"type": "keyword"},
                    "timestamp": {"type": "date"}
                }
            }
        }

        for index in [self.tenant1_index, self.tenant2_index, self.marketplace_index]:
            if not self.es.indices.exists(index=index):
                self.es.indices.create(index=index, body=mapping)
                logger.info(f"Created index: {index}")

    def get_tenant1_data(self) -> List[Dict]:
        """Chemical processing company inventory"""
        return [
            {
                "tenant_id": "tenant1",
                "name": "Chemical Process Pump",
                "description": "High-capacity centrifugal pump for aggressive chemicals",
                "category": "pumps",
                "subcategory": "centrifugal_pumps",
                "manufacturer": "Flowserve",
                "model": "PVXM-2000",
                "specifications": [
                    {"parameter": "flow", "value": 2000, "unit": "m3/hr"},
                    {"parameter": "pressure", "value": 40, "unit": "bar"},
                    {"parameter": "power", "value": 450, "unit": "kW"}
                ],
                "location": {"country": "USA", "city": "Houston", "availability": "immediate"},
                "price": {"value": 75000.00, "currency": "USD"},
                "condition": "new"
            },
            {
                "tenant_id": "tenant1",
                "name": "Process Heat Exchanger",
                "description": "Shell and tube heat exchanger for chemical processing",
                "category": "heat_exchangers",
                "subcategory": "shell_and_tube",
                "manufacturer": "Alfa Laval",
                "model": "ST-500",
                "specifications": [
                    {"parameter": "heat_transfer_area", "value": 500, "unit": "m2"},
                    {"parameter": "temperature", "value": 200, "unit": "C"},
                    {"parameter": "pressure", "value": 25, "unit": "bar"}
                ],
                "location": {"country": "USA", "city": "Dallas", "availability": "2-weeks"},
                "price": {"value": 120000.00, "currency": "USD"},
                "condition": "new"
            }
        ]

    def get_tenant2_data(self) -> List[Dict]:
        """Power generation company inventory"""
        return [
            {
                "tenant_id": "tenant2",
                "name": "Steam Turbine System",
                "description": "Industrial steam turbine for power generation",
                "category": "turbines",
                "subcategory": "steam_turbines",
                "manufacturer": "Siemens",
                "model": "SST-600",
                "specifications": [
                    {"parameter": "power", "value": 60, "unit": "MW"},
                    {"parameter": "steam_pressure", "value": 120, "unit": "bar"},
                    {"parameter": "steam_temperature", "value": 540, "unit": "C"}
                ],
                "location": {"country": "Germany", "city": "Berlin", "availability": "12-weeks"},
                "price": {"value": 8500000.00, "currency": "EUR"},
                "condition": "new"
            },
            {
                "tenant_id": "tenant2",
                "name": "Industrial Boiler",
                "description": "High-pressure water tube boiler",
                "category": "boilers",
                "subcategory": "water_tube",
                "manufacturer": "Babcock & Wilcox",
                "model": "FM-100",
                "specifications": [
                    {"parameter": "steam_output", "value": 100, "unit": "tons/hr"},
                    {"parameter": "pressure", "value": 80, "unit": "bar"},
                    {"parameter": "temperature", "value": 450, "unit": "C"}
                ],
                "location": {"country": "UK", "city": "Manchester", "availability": "immediate"},
                "price": {"value": 1800000.00, "currency": "GBP"},
                "condition": "new"
            }
        ]

    def get_marketplace_data(self) -> List[Dict]:
        """Public marketplace listings"""
        return [
            {
                "tenant_id": "supplier1",
                "name": "Chemical Dosing Package",
                "description": "Complete chemical dosing system with tanks and controls",
                "category": "pumps",
                "subcategory": "metering_pumps",
                "manufacturer": "ProMinent",
                "model": "Sigma X",
                "specifications": [
                    {"parameter": "flow", "value": 120, "unit": "l/hr"},
                    {"parameter": "pressure", "value": 10, "unit": "bar"},
                    {"parameter": "power", "value": 1.5, "unit": "kW"}
                ],
                "location": {"country": "Germany", "city": "Frankfurt", "availability": "immediate"},
                "price": {"value": 15000.00, "currency": "EUR"},
                "condition": "new"
            },
            {
                "tenant_id": "supplier2",
                "name": "Plate Heat Exchanger",
                "description": "Gasketed plate heat exchanger for industrial cooling",
                "category": "heat_exchangers",
                "subcategory": "plate_type",
                "manufacturer": "GEA",
                "model": "NT-350",
                "specifications": [
                    {"parameter": "heat_transfer_area", "value": 350, "unit": "m2"},
                    {"parameter": "temperature", "value": 150, "unit": "C"},
                    {"parameter": "pressure", "value": 16, "unit": "bar"}
                ],
                "location": {"country": "Italy", "city": "Milan", "availability": "1-week"},
                "price": {"value": 85000.00, "currency": "EUR"},
                "condition": "new"
            },
            {
                "tenant_id": "supplier3",
                "name": "Gas Turbine Package",
                "description": "Complete gas turbine generator package",
                "category": "turbines",
                "subcategory": "gas_turbines",
                "manufacturer": "Solar Turbines",
                "model": "Titan 130",
                "specifications": [
                    {"parameter": "power", "value": 15, "unit": "MW"},
                    {"parameter": "efficiency", "value": 35, "unit": "percent"},
                    {"parameter": "exhaust_temp", "value": 490, "unit": "C"}
                ],
                "location": {"country": "USA", "city": "San Diego", "availability": "20-weeks"},
                "price": {"value": 12000000.00, "currency": "USD"},
                "condition": "new"
            }
        ]

    def load_sample_data(self):
        """Load all sample data into respective indices"""
        # Create indices first
        self.create_indices()

        # Load tenant1 data
        for item in self.get_tenant1_data():
            try:
                item['timestamp'] = datetime.now().isoformat()
                self.es.index(index=self.tenant1_index, document=item)
                logger.info(f"Loaded tenant1 equipment: {item['name']}")
            except Exception as e:
                logger.error(f"Error loading tenant1 equipment {item['name']}: {e}")

        # Load tenant2 data
        for item in self.get_tenant2_data():
            try:
                item['timestamp'] = datetime.now().isoformat()
                self.es.index(index=self.tenant2_index, document=item)
                logger.info(f"Loaded tenant2 equipment: {item['name']}")
            except Exception as e:
                logger.error(f"Error loading tenant2 equipment {item['name']}: {e}")

        # Load marketplace data
        for item in self.get_marketplace_data():
            try:
                item['timestamp'] = datetime.now().isoformat()
                self.es.index(index=self.marketplace_index, document=item)
                logger.info(f"Loaded marketplace equipment: {item['name']}")
            except Exception as e:
                logger.error(f"Error loading marketplace equipment {item['name']}: {e}")

        # Refresh indices
        for index in [self.tenant1_index, self.tenant2_index, self.marketplace_index]:
            self.es.indices.refresh(index=index)
        
        logger.info("Sample data loading completed")

if __name__ == "__main__":
    loader = MultiTenantDataLoader()
    loader.load_sample_data()