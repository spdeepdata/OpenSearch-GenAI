from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class Manufacturer:
    name: str
    country: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None

@dataclass
class InventoryItem:
    sku: str
    name: str
    manufacturer: Manufacturer
    quantity: int
    unit_price: float
    category: str
    location: str
    last_updated: datetime
    minimum_stock: int = 0
    description: Optional[str] = None

# OpenSearch index mapping
INVENTORY_INDEX_MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 1,
        "analysis": {
            "analyzer": {
                "inventory_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "stop", "snowball"]
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "sku": {"type": "keyword"},
            "name": {
                "type": "text",
                "analyzer": "inventory_analyzer",
                "fields": {
                    "keyword": {"type": "keyword"}
                }
            },
            "manufacturer": {
                "properties": {
                    "name": {
                        "type": "text",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "country": {"type": "keyword"},
                    "contact_email": {"type": "keyword"},
                    "contact_phone": {"type": "keyword"}
                }
            },
            "quantity": {"type": "integer"},
            "unit_price": {"type": "float"},
            "category": {"type": "keyword"},
            "location": {"type": "keyword"},
            "last_updated": {"type": "date"},
            "minimum_stock": {"type": "integer"},
            "description": {"type": "text"},
            "entities": {
                "properties": {
                    "text": {"type": "keyword"},
                    "label": {"type": "keyword"},
                    "start": {"type": "integer"},
                    "end": {"type": "integer"}
                }
            }
        }
    }
}

# Sample inventory data
SAMPLE_INVENTORY = [
    {
        "sku": "LP-2023-001",
        "name": "ThinkPad X1 Carbon Gen 9",
        "manufacturer": {
            "name": "Lenovo",
            "country": "China",
            "contact_email": "support@lenovo.com",
            "contact_phone": "+1-555-0123"
        },
        "quantity": 25,
        "unit_price": 1499.99,
        "category": "Laptops",
        "location": "Warehouse A",
        "minimum_stock": 10,
        "description": "14-inch business laptop with Intel Core i7 processor"
    },
    {
        "sku": "AP-2023-002",
        "name": "iPhone 14 Pro",
        "manufacturer": {
            "name": "Apple Inc.",
            "country": "United States",
            "contact_email": "enterprise@apple.com",
            "contact_phone": "+1-555-0124"
        },
        "quantity": 50,
        "unit_price": 999.99,
        "category": "Smartphones",
        "location": "Warehouse B",
        "minimum_stock": 15,
        "description": "6.1-inch smartphone with A16 Bionic chip"
    },
    {
        "sku": "SS-2023-003",
        "name": "Samsung QN90B QLED TV",
        "manufacturer": {
            "name": "Samsung Electronics",
            "country": "South Korea",
            "contact_email": "b2b@samsung.com",
            "contact_phone": "+1-555-0125"
        },
        "quantity": 15,
        "unit_price": 2499.99,
        "category": "TVs",
        "location": "Warehouse A",
        "minimum_stock": 5,
        "description": "65-inch 4K QLED Smart TV with Neural Quantum Processor"
    }
]