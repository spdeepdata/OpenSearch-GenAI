from elasticsearch import Elasticsearch
import logging
from datetime import datetime
from typing import Dict, List
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ShardedMultiTenantLoader:
    def __init__(self, host: str = "http://localhost:9200"):
        self.es = Elasticsearch([host])
        self.equipment_index = "sharded_equipment"
        self.tenant_index = "tenant_metadata"
        self.num_shards = 5  # Number of primary shards
        
    def _get_shard_routing(self, tenant_id: str) -> str:
        """Calculate shard routing key based on tenant_id"""
        return hashlib.md5(tenant_id.encode()).hexdigest()
    
    def create_indices(self):
        """Create indices with sharding configuration"""
        equipment_mapping = {
            "settings": {
                "number_of_shards": self.num_shards,
                "number_of_replicas": 1
            },
            "mappings": {
                "properties": {
                    "tenant_id": {"type": "keyword"},
                    "name": {"type": "text"},
                    "description": {"type": "text"},
                    "category": {"type": "keyword"},
                    "subcategory": {"type": "keyword"},
                    "manufacturer": {"type": "keyword"},
                    "model": {"type": "keyword"},
                    "marketplace_listing": {"type": "boolean"},  # Flag for marketplace visibility
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
                    "timestamp": {"type": "date"},
                    "routing_key": {"type": "keyword"}  # Store routing key for reference
                }
            }
        }

        # Tenant metadata mapping
        tenant_mapping = {
            "settings": {
                "number_of_shards": 1  # Single shard for tenant metadata
            },
            "mappings": {
                "properties": {
                    "tenant_id": {"type": "keyword"},
                    "name": {"type": "text"},
                    "industry": {"type": "keyword"},
                    "routing_key": {"type": "keyword"},
                    "created_at": {"type": "date"},
                    "marketplace_access": {"type": "boolean"}
                }
            }
        }

        # Create indices if they don't exist
        for index, mapping in [
            (self.equipment_index, equipment_mapping),
            (self.tenant_index, tenant_mapping)
        ]:
            if not self.es.indices.exists(index=index):
                self.es.indices.create(index=index, body=mapping)
                logger.info(f"Created index: {index}")

    def register_tenant(self, tenant_id: str, name: str, industry: str):
        """Register a new tenant with metadata"""
        routing_key = self._get_shard_routing(tenant_id)
        
        tenant_doc = {
            "tenant_id": tenant_id,
            "name": name,
            "industry": industry,
            "routing_key": routing_key,
            "created_at": datetime.now().isoformat(),
            "marketplace_access": True
        }
        
        try:
            self.es.index(
                index=self.tenant_index,
                document=tenant_doc,
                id=tenant_id
            )
            logger.info(f"Registered tenant: {name} with ID: {tenant_id}")
            return routing_key
        except Exception as e:
            logger.error(f"Error registering tenant: {e}")
            raise

    def load_equipment_data(self, tenant_id: str, equipment_list: List[Dict]):
        """Load equipment data with proper sharding"""
        routing_key = self._get_shard_routing(tenant_id)
        timestamp = datetime.now().isoformat()
        
        for item in equipment_list:
            try:
                # Prepare document with routing information
                doc = {
                    **item,
                    "tenant_id": tenant_id,
                    "routing_key": routing_key,
                    "timestamp": timestamp,
                    "marketplace_listing": item.get("marketplace_listing", False)
                }
                
                # Index with routing
                self.es.index(
                    index=self.equipment_index,
                    document=doc,
                    routing=routing_key
                )
                logger.info(f"Indexed equipment for tenant {tenant_id}: {item['name']}")
                
            except Exception as e:
                logger.error(f"Error indexing equipment: {e}")

    def load_sample_data(self):
        """Load sample data with sharding"""
        self.create_indices()
        
        # Register and load tenant1 data
        self.register_tenant(
            "tenant1",
            "ChemCorp Industries",
            "chemical_processing"
        )
        tenant1_data = [
            {
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
                "condition": "new",
                "marketplace_listing": True
            }
        ]
        self.load_equipment_data("tenant1", tenant1_data)
        
        # Register and load tenant2 data
        self.register_tenant(
            "tenant2",
            "PowerGen Solutions",
            "power_generation"
        )
        tenant2_data = [
            {
                "name": "Steam Turbine System",
                "description": "Industrial steam turbine for power generation",
                "category": "turbines",
                "subcategory": "steam_turbines",
                "manufacturer": "Siemens",
                "model": "SST-600",
                "specifications": [
                    {"parameter": "power", "value": 60, "unit": "MW"},
                    {"parameter": "steam_pressure", "value": 120, "unit": "bar"}
                ],
                "location": {"country": "Germany", "city": "Berlin", "availability": "12-weeks"},
                "price": {"value": 8500000.00, "currency": "EUR"},
                "condition": "new",
                "marketplace_listing": True
            }
        ]
        self.load_equipment_data("tenant2", tenant2_data)
        
        # Refresh indices
        self.es.indices.refresh(index=self.equipment_index)
        self.es.indices.refresh(index=self.tenant_index)
        
        logger.info("Sample data loading completed with sharding")

# Example usage
if __name__ == "__main__":
    loader = ShardedMultiTenantLoader()
    loader.load_sample_data()