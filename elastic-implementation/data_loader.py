from elasticsearch import Elasticsearch
import logging
from typing import List, Dict
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExtensiveEquipmentDataLoader:
    def __init__(self, host: str = "http://localhost:9200"):
        self.es = Elasticsearch([host])
        self.internal_index = "internal_equipment"
        self.partner_index = "partner_equipment"

    def get_internal_equipment(self) -> List[Dict]:
        """Generate extensive internal equipment data"""
        return [
            # Pumps
            {
                "name": "High-Flow Process Pump",
                "description": "High-capacity centrifugal pump for chemical processing with advanced seal system",
                "category": "pumps",
                "subcategory": "centrifugal_pumps",
                "manufacturer": "Flowserve",
                "model": "PVXM-5000",
                "specifications": [
                    {"parameter": "flow", "value": 5000, "unit": "m3/hr"},
                    {"parameter": "head", "value": 150, "unit": "m"},
                    {"parameter": "power", "value": 750, "unit": "kW"},
                    {"parameter": "efficiency", "value": 85, "unit": "percent"}
                ],
                "location": {"country": "USA", "city": "Houston", "availability": "immediate"},
                "price": {"value": 85000.00, "currency": "USD"},
                "condition": "new",
                "certification": ["ATEX", "API-610"],
                "warranty_period": 24
            },
            {
                "name": "Metering Pump Package",
                "description": "Precision chemical dosing pump with digital flow control",
                "category": "pumps",
                "subcategory": "metering_pumps",
                "manufacturer": "Milton Roy",
                "model": "mROY-A",
                "specifications": [
                    {"parameter": "flow", "value": 1.5, "unit": "m3/hr"},
                    {"parameter": "pressure", "value": 70, "unit": "bar"},
                    {"parameter": "power", "value": 2.2, "unit": "kW"}
                ],
                "location": {"country": "USA", "city": "Chicago", "availability": "1-week"},
                "price": {"value": 12000.00, "currency": "USD"},
                "condition": "new"
            },

            # Heat Exchangers
            {
                "name": "Large Plate Heat Exchanger",
                "description": "Gasketed plate heat exchanger for industrial process cooling",
                "category": "heat_exchangers",
                "subcategory": "plate_type",
                "manufacturer": "Alfa Laval",
                "model": "T50",
                "specifications": [
                    {"parameter": "heat_transfer_area", "value": 5000, "unit": "m2"},
                    {"parameter": "temperature", "value": 180, "unit": "C"},
                    {"parameter": "pressure", "value": 25, "unit": "bar"},
                    {"parameter": "flow_rate", "value": 1000, "unit": "m3/hr"}
                ],
                "location": {"country": "Germany", "city": "Hamburg", "availability": "immediate"},
                "price": {"value": 120000.00, "currency": "EUR"},
                "condition": "new"
            },

            # Compressors
            {
                "name": "Oil-Free Air Compressor",
                "description": "Class 0 oil-free rotary screw air compressor with integrated dryer",
                "category": "compressors",
                "subcategory": "rotary_screw",
                "manufacturer": "Atlas Copco",
                "model": "ZR-500-VSD+",
                "specifications": [
                    {"parameter": "flow", "value": 3000, "unit": "m3/hr"},
                    {"parameter": "pressure", "value": 8.5, "unit": "bar"},
                    {"parameter": "power", "value": 500, "unit": "kW"},
                    {"parameter": "noise_level", "value": 75, "unit": "dB"}
                ],
                "location": {"country": "USA", "city": "Cleveland", "availability": "2-weeks"},
                "price": {"value": 250000.00, "currency": "USD"},
                "condition": "new"
            },

            # Turbines
            {
                "name": "Industrial Steam Turbine",
                "description": "High-efficiency condensing steam turbine for power generation",
                "category": "turbines",
                "subcategory": "steam_turbines",
                "manufacturer": "General Electric",
                "model": "D650",
                "specifications": [
                    {"parameter": "power_output", "value": 100, "unit": "MW"},
                    {"parameter": "steam_pressure", "value": 140, "unit": "bar"},
                    {"parameter": "steam_temperature", "value": 565, "unit": "C"},
                    {"parameter": "efficiency", "value": 94, "unit": "percent"}
                ],
                "location": {"country": "USA", "city": "Schenectady", "availability": "12-weeks"},
                "price": {"value": 15000000.00, "currency": "USD"},
                "condition": "new"
            },

            # Valves
            {
                "name": "Control Valve Package",
                "description": "Digital positioner equipped control valve for precise flow control",
                "category": "valves",
                "subcategory": "control_valves",
                "manufacturer": "Fisher",
                "model": "GX-3000",
                "specifications": [
                    {"parameter": "size", "value": 12, "unit": "inch"},
                    {"parameter": "pressure_rating", "value": 300, "unit": "psi"},
                    {"parameter": "cv", "value": 1200, "unit": "gpm"},
                    {"parameter": "rangeability", "value": 50, "unit": "ratio"}
                ],
                "location": {"country": "USA", "city": "Houston", "availability": "immediate"},
                "price": {"value": 35000.00, "currency": "USD"},
                "condition": "new"
            }
        ]

    def get_partner_equipment(self) -> List[Dict]:
        """Generate extensive partner equipment data"""
        return [
            # Pumps
            {
                "name": "Multistage Process Pump",
                "description": "High-pressure multistage centrifugal pump for water injection",
                "category": "pumps",
                "subcategory": "multistage_pumps",
                "manufacturer": "Sulzer",
                "model": "MSD-RO",
                "specifications": [
                    {"parameter": "flow", "value": 800, "unit": "m3/hr"},
                    {"parameter": "head", "value": 1500, "unit": "m"},
                    {"parameter": "power", "value": 1200, "unit": "kW"},
                    {"parameter": "efficiency", "value": 83, "unit": "percent"}
                ],
                "location": {"country": "Switzerland", "city": "Winterthur", "availability": "3-weeks"},
                "price": {"value": 320000.00, "currency": "CHF"},
                "condition": "new"
            },

            # Heat Exchangers
            {
                "name": "Spiral Heat Exchanger",
                "description": "Self-cleaning spiral heat exchanger for fouling services",
                "category": "heat_exchangers",
                "subcategory": "spiral",
                "manufacturer": "Alfa Laval",
                "model": "SHE-25",
                "specifications": [
                    {"parameter": "heat_transfer_area", "value": 250, "unit": "m2"},
                    {"parameter": "temperature", "value": 200, "unit": "C"},
                    {"parameter": "pressure", "value": 15, "unit": "bar"}
                ],
                "location": {"country": "Sweden", "city": "Lund", "availability": "immediate"},
                "price": {"value": 95000.00, "currency": "EUR"},
                "condition": "new"
            },

            # Boilers
            {
                "name": "Industrial Steam Boiler",
                "description": "High-pressure water tube boiler for process steam generation",
                "category": "boilers",
                "subcategory": "water_tube",
                "manufacturer": "Babcock & Wilcox",
                "model": "FM-120",
                "specifications": [
                    {"parameter": "steam_output", "value": 120, "unit": "tons/hr"},
                    {"parameter": "pressure", "value": 85, "unit": "bar"},
                    {"parameter": "temperature", "value": 450, "unit": "C"},
                    {"parameter": "efficiency", "value": 92, "unit": "percent"}
                ],
                "location": {"country": "UK", "city": "Manchester", "availability": "6-weeks"},
                "price": {"value": 2200000.00, "currency": "GBP"},
                "condition": "new"
            },
            # Compressors
            {
                "name": "Centrifugal Air Compressor",
                "description": "High-speed centrifugal compressor with magnetic bearings",
                "category": "compressors",
                "subcategory": "centrifugal",
                "manufacturer": "Ingersoll Rand",
                "model": "C1000",
                "specifications": [
                    {"parameter": "flow", "value": 10000, "unit": "m3/hr"},
                    {"parameter": "pressure", "value": 8, "unit": "bar"},
                    {"parameter": "power", "value": 1000, "unit": "kW"}
                ],
                "location": {"country": "Italy", "city": "Milan", "availability": "immediate"},
                "price": {"value": 450000.00, "currency": "EUR"},
                "condition": "new"
            },

            # Process Equipment
            {
                "name": "Vacuum Distillation Column",
                "description": "Complete vacuum distillation system for chemical processing",
                "category": "process_equipment",
                "subcategory": "distillation",
                "manufacturer": "Koch-Glitsch",
                "model": "VDC-2000",
                "specifications": [
                    {"parameter": "diameter", "value": 2.5, "unit": "m"},
                    {"parameter": "height", "value": 25, "unit": "m"},
                    {"parameter": "vacuum", "value": 50, "unit": "mbar"},
                    {"parameter": "capacity", "value": 100, "unit": "tons/day"}
                ],
                "location": {"country": "Germany", "city": "Frankfurt", "availability": "16-weeks"},
                "price": {"value": 1800000.00, "currency": "EUR"},
                "condition": "new"
            },

            # Used Equipment
            {
                "name": "Refurbished Process Pump",
                "description": "Factory reconditioned API process pump",
                "category": "pumps",
                "subcategory": "centrifugal_pumps",
                "manufacturer": "Flowserve",
                "model": "DVSH",
                "specifications": [
                    {"parameter": "flow", "value": 350, "unit": "m3/hr"},
                    {"parameter": "head", "value": 200, "unit": "m"},
                    {"parameter": "power", "value": 250, "unit": "kW"}
                ],
                "location": {"country": "Netherlands", "city": "Rotterdam", "availability": "immediate"},
                "price": {"value": 45000.00, "currency": "EUR"},
                "condition": "refurbished",
                "refurbishment_date": "2024-01-15"
            }
        ]

    def load_sample_data(self):
        """Load all sample equipment data into Elasticsearch"""
        # Get equipment data
        internal_equipment = self.get_internal_equipment()
        partner_equipment = self.get_partner_equipment()

        # Load internal equipment
        for item in internal_equipment:
            try:
                item['timestamp'] = datetime.now().isoformat()
                self.es.index(index=self.internal_index, document=item)
                logger.info(f"Loaded internal equipment: {item['name']}")
            except Exception as e:
                logger.error(f"Error loading internal equipment {item['name']}: {e}")

        # Load partner equipment
        for item in partner_equipment:
            try:
                item['timestamp'] = datetime.now().isoformat()
                self.es.index(index=self.partner_index, document=item)
                logger.info(f"Loaded partner equipment: {item['name']}")
            except Exception as e:
                logger.error(f"Error loading partner equipment {item['name']}: {e}")

        # Refresh indices
        self.es.indices.refresh(index=self.internal_index)
        self.es.indices.refresh(index=self.partner_index)
        
        logger.info("Sample data loading completed")

if __name__ == "__main__":
    loader = ExtensiveEquipmentDataLoader()
    loader.load_sample_data()