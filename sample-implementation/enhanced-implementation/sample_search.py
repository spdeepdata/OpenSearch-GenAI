from opensearchpy import OpenSearch, RequestsHttpConnection
from sentence_transformers import SentenceTransformer
import numpy as np
from tabulate import tabulate
import time
import re
from typing import Dict, List, Union, Optional

class SpecParser:
    """Handles parsing and normalization of technical specifications"""
    
    @staticmethod
    def normalize_power(value: str) -> Optional[float]:
        """Convert power specifications to watts"""
        if not value:
            return None
        match = re.search(r'(\d+(?:\.\d+)?)\s*(W|KW|MW)?', value, re.IGNORECASE)
        if not match:
            return None
        
        number, unit = match.groups()
        number = float(number)
        
        if unit:
            unit = unit.upper()
            if unit == 'KW':
                number *= 1000
            elif unit == 'MW':
                number *= 1000000
        
        return number

    @staticmethod
    def normalize_voltage(value: str) -> Optional[float]:
        """Convert voltage specifications to volts"""
        if not value:
            return None
        match = re.search(r'(\d+(?:\.\d+)?)\s*(V|KV|MV)?', value, re.IGNORECASE)
        if not match:
            return None
        
        number, unit = match.groups()
        number = float(number)
        
        if unit:
            unit = unit.upper()
            if unit == 'KV':
                number *= 1000
            elif unit == 'MV':
                number *= 1000000
        
        return number

    @staticmethod
    def extract_price_constraint(query: str) -> Optional[Dict]:
        """Extract price constraints from query"""
        under_match = re.search(r'under\s*\$?\s*(\d+(?:\.\d+)?)', query, re.IGNORECASE)
        over_match = re.search(r'over\s*\$?\s*(\d+(?:\.\d+)?)', query, re.IGNORECASE)
        
        constraints = {}
        if under_match:
            constraints['lte'] = float(under_match.group(1))
        if over_match:
            constraints['gte'] = float(over_match.group(1))
            
        return constraints if constraints else None

    @staticmethod
    def normalize_dimensions(value: str) -> Optional[float]:
        """Convert dimensions to millimeters"""
        if not value:
            return None
        match = re.search(r'(\d+(?:\.\d+)?)\s*(mm|cm|m|in)?', value, re.IGNORECASE)
        if not match:
            return None
        
        number, unit = match.groups()
        number = float(number)
        
        if unit:
            unit = unit.lower()
            if unit == 'cm':
                number *= 10
            elif unit == 'm':
                number *= 1000
            elif unit == 'in':
                number *= 25.4
        
        return number

class InventoryAnalyzer:
    """Handles inventory status analysis"""
    
    @staticmethod
    def calculate_stock_status(part: Dict) -> str:
        """Calculate stock status based on current level and reorder point"""
        if part['stock_level'] <= part['reorder_point']:
            return 'critical'
        elif part['stock_level'] <= 2 * part['reorder_point']:
            return 'low'
        elif part['stock_level'] >= 5 * part['reorder_point']:
            return 'excess'
        else:
            return 'optimal'

    @staticmethod
    def enrich_inventory_data(part: Dict) -> Dict:
        """Add inventory analysis to part data"""
        stock_status = InventoryAnalyzer.calculate_stock_status(part)
        
        enriched = part.copy()
        enriched['inventory_metrics'] = {
            'stock_status': stock_status,
            'stock_to_reorder_ratio': part['stock_level'] / part['reorder_point'],
            'units_above_reorder': part['stock_level'] - part['reorder_point']
        }
        
        return enriched

class EnhancedSparePartsSearch:
    def __init__(self, host='localhost', port=9200, index_name='spare_parts'):
        self.client = OpenSearch(
            hosts=[{'host': host, 'port': port}],
            http_auth=None,
            use_ssl=False,
            verify_certs=False,
            ssl_show_warn=False,
            scheme="http",
            timeout=30,
            max_retries=3,
            retry_on_timeout=True,
            connection_class=RequestsHttpConnection
        )
        self.index_name = index_name
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.spec_parser = SpecParser()
        self.inventory_analyzer = InventoryAnalyzer()
        self._create_index()

    def _create_index(self):
        """Create index with enhanced mappings"""
        if self.client.indices.exists(index=self.index_name):
            self.client.indices.delete(index=self.index_name)
            
        mappings = {
            "mappings": {
                "properties": {
                    "part_number": {"type": "keyword"},
                    "name": {"type": "text"},
                    "description": {"type": "text"},
                    "technical_specs": {
                        "properties": {
                            "raw": {"type": "object"},
                            "normalized": {
                                "properties": {
                                    "power_w": {"type": "float"},
                                    "voltage_v": {"type": "float"},
                                    "dimensions_mm": {"type": "float"}
                                }
                            }
                        }
                    },
                    "compatibility": {"type": "keyword"},
                    "supplier_codes": {"type": "keyword"},
                    "inventory_metrics": {
                        "properties": {
                            "stock_status": {"type": "keyword"},
                            "stock_to_reorder_ratio": {"type": "float"},
                            "units_above_reorder": {"type": "integer"}
                        }
                    },
                    "min_order_qty": {"type": "integer"},
                    "unit_cost": {"type": "float"},
                    "retail_price": {"type": "float"},
                    "stock_level": {"type": "integer"},
                    "category": {"type": "keyword"},
                    "embedding": {"type": "float"}
                }
            }
        }
        
        self.client.indices.create(index=self.index_name, body=mappings)

    def _normalize_specs(self, specs: Dict) -> Dict:
        """Normalize technical specifications to standard units"""
        normalized = {}
        
        if 'power' in specs:
            normalized['power_w'] = self.spec_parser.normalize_power(specs['power'])
        if 'voltage' in specs:
            normalized['voltage_v'] = self.spec_parser.normalize_voltage(specs['voltage'])
        
        # Handle dimensions
        for dim in ['length', 'width', 'height', 'diameter']:
            if dim in specs:
                normalized[f'{dim}_mm'] = self.spec_parser.normalize_dimensions(specs[dim])
        
        return normalized

    def index_parts(self, parts: List[Dict]):
        """Index parts with enhanced data"""
        for part in parts:
            # Normalize technical specs
            part['technical_specs'] = {
                'raw': part['technical_specs'],
                'normalized': self._normalize_specs(part['technical_specs'])
            }
            
            # Add inventory analysis
            part = self.inventory_analyzer.enrich_inventory_data(part)
            
            # Create rich text for embedding
            specs_text = ' '.join([f"{k}: {v}" for k, v in part['technical_specs']['raw'].items()])
            compatibility_text = ' '.join(part['compatibility'])
            inventory_text = f"Stock status: {part['inventory_metrics']['stock_status']}"
            
            text_to_embed = f"{part['name']} {part['description']} {specs_text} {compatibility_text} {inventory_text} {part['category']}"
            embedding = self.model.encode(text_to_embed)
            
            doc = part.copy()
            doc['embedding'] = embedding.tolist()
            
            self.client.index(
                index=self.index_name,
                body=doc,
                id=part['part_number'],
                refresh=True
            )

    def semantic_search(self, query: str, size: int = 5):
        """Enhanced semantic search with technical and inventory awareness"""
        # Extract price constraints
        price_constraints = self.spec_parser.extract_price_constraint(query)
        
        # Generate embedding for semantic search
        query_embedding = self.model.encode(query)
        
        # Build search query
        body = {
            "query": {
                "bool": {
                    "must": [{"match_all": {}}]
                }
            },
            "_source": True,
            "size": 100
        }
        
        # Add price filter if present
        if price_constraints:
            body["query"]["bool"]["filter"] = [
                {"range": {"retail_price": price_constraints}}
            ]
        
        # Execute search
        response = self.client.search(index=self.index_name, body=body)
        hits = response['hits']['hits']
        
        # Score results using embeddings and boost based on inventory status
        scored_hits = []
        for hit in hits:
            doc = hit['_source']
            
            # Calculate semantic similarity
            similarity = np.dot(query_embedding, doc['embedding'])
            
            # Apply inventory status boost
            inventory_boost = 1.0
            if 'stock' in query.lower() or 'inventory' in query.lower():
                status = doc['inventory_metrics']['stock_status']
                if status == 'optimal':
                    inventory_boost = 1.2
                elif status == 'excess':
                    inventory_boost = 0.8
                elif status == 'critical':
                    inventory_boost = 0.6
            
            # Calculate final score
            hit['_score'] = float(similarity * inventory_boost)
            scored_hits.append(hit)
        
        # Sort by score and return top results
        scored_hits.sort(key=lambda x: x['_score'], reverse=True)
        return scored_hits[:size]

    def compare_searches(self, query: str, explanation: str):
        """Compare standard and semantic search results with enhanced metrics"""
        print(f"\n{'='*100}")
        print(f"Use Case: {explanation}")
        print(f"Query: '{query}'")
        print(f"{'='*100}")
        
        semantic_results = self.semantic_search(query)
        
        # Enhanced results format with inventory status
        def format_results(results):
            rows = []
            for i, hit in enumerate(results, 1):
                source = hit['_source']
                score = hit['_score']
                rows.append([
                    i,
                    source['part_number'],
                    source['name'],
                    f"${source['retail_price']:,.2f}",
                    source['stock_level'],
                    source['inventory_metrics']['stock_status'],
                    f"{score:.2f}"
                ])
            
            print("\nEnhanced Search Results:")
            print(tabulate(
                rows,
                headers=['Rank', 'Part #', 'Name', 'Price', 'Stock', 'Status', 'Score'],
                tablefmt='grid'
            ))
        
        format_results(semantic_results)
    def standard_search(self, query: str, size: int = 5):
        """Standard keyword-based search with fuzzy matching"""
        body = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": [
                                    "name^3",
                                    "description^2",
                                    "technical_specs.raw.*",
                                    "category",
                                    "compatibility"
                                ],
                                "fuzziness": "AUTO",
                                "operator": "or"
                            }
                        },
                        {
                            "match_phrase": {
                                "part_number": {
                                    "query": query,
                                    "boost": 4
                                }
                            }
                        }
                    ]
                }
            }
        }
        
        response = self.client.search(index=self.index_name, body=body, size=size)
        return response['hits']['hits']

    def compare_searches(self, query: str, explanation: str):
        """Compare standard and semantic search results with enhanced metrics"""
        print(f"\n{'='*100}")
        print(f"Use Case: {explanation}")
        print(f"Query: '{query}'")
        print(f"{'='*100}")
        
        standard_results = self.standard_search(query)
        semantic_results = self.semantic_search(query)
        
        def format_results(results, search_type):
            rows = []
            for i, hit in enumerate(results, 1):
                source = hit['_source']
                score = hit['_score']
                status = source.get('inventory_metrics', {}).get('stock_status', 'unknown')
                rows.append([
                    i,
                    source['part_number'],
                    source['name'],
                    f"${source['retail_price']:,.2f}",
                    source['stock_level'],
                    status,
                    f"{score:.2f}"
                ])
            
            print(f"\n{search_type} Search Results:")
            print(tabulate(
                rows,
                headers=['Rank', 'Part #', 'Name', 'Price', 'Stock', 'Status', 'Score'],
                tablefmt='grid'
            ))
        
        format_results(standard_results, "Standard")
        format_results(semantic_results, "Semantic")
        
        # Add analysis of differences
        print("\nKey Differences Analysis:")
        std_part_numbers = [hit['_source']['part_number'] for hit in standard_results]
        sem_part_numbers = [hit['_source']['part_number'] for hit in semantic_results]
        
        # Find unique parts in each search
        unique_to_standard = set(std_part_numbers) - set(sem_part_numbers)
        unique_to_semantic = set(sem_part_numbers) - set(std_part_numbers)
        
        if unique_to_standard:
            print(f"Parts found only by Standard search: {', '.join(unique_to_standard)}")
        if unique_to_semantic:
            print(f"Parts found only by Semantic search: {', '.join(unique_to_semantic)}")

test_data = [
        {
            "part_number": "BAT-400-PRO",
            "name": "Lithium Battery Pack Pro",
            "description": "48V lithium battery pack with integrated BMS. 5-year warranty.",
            "technical_specs": {
                "voltage": "48V",
                "capacity": "400Ah",
                "weight": "12kg",
                "dimensions": "300x200x150mm",
                "lifecycle": "2000 cycles",
                "charge_time": "4h"
            },
            "compatibility": ["Pro Series 2021+", "Industrial Series"],
            "supplier_codes": ["SUP456", "ALT789"],
            "min_order_qty": 1,
            "unit_cost": 799.99,
            "retail_price": 1299.99,
            "stock_level": 20,
            "reorder_point": 5,
            "category": "Electrical Systems",
            "alternatives": ["BAT-350-STD", "BAT-500-IND"]
        },
        {
            "part_number": "BAT-350-STD",
            "name": "Lithium Battery Pack Standard",
            "description": "36V lithium battery for standard applications. 3-year warranty.",
            "technical_specs": {
                "voltage": "36V",
                "capacity": "350Ah",
                "weight": "10kg",
                "dimensions": "280x180x130mm",
                "lifecycle": "1500 cycles",
                "charge_time": "3.5h"
            },
            "compatibility": ["Standard Series", "Light Industrial"],
            "supplier_codes": ["SUP456"],
            "min_order_qty": 1,
            "unit_cost": 599.99,
            "retail_price": 899.99,
            "stock_level": 5,
            "reorder_point": 8,
            "category": "Electrical Systems",
            "alternatives": ["BAT-400-PRO"]
        },
        {
            "part_number": "MOT-550-X",
            "name": "High-Efficiency Motor X Series",
            "description": "550W brushless motor with integrated controller. IP65 rated.",
            "technical_specs": {
                "power": "550W",
                "voltage": "36V",
                "rpm": "3000",
                "efficiency": "94%",
                "protection": "IP65",
                "torque": "2.5Nm"
            },
            "compatibility": ["X Series", "Pro Series", "Industrial Line"],
            "supplier_codes": ["SUP567", "MOT789"],
            "min_order_qty": 1,
            "unit_cost": 249.99,
            "retail_price": 449.99,
            "stock_level": 30,
            "reorder_point": 8,
            "category": "Motors",
            "alternatives": ["MOT-500-S"]
        },
        {
            "part_number": "CTR-100-DIG",
            "name": "Digital Motor Controller",
            "description": "Advanced digital controller with CAN bus interface. Supports regenerative braking.",
            "technical_specs": {
                "voltage_range": "24-60V",
                "max_current": "100A",
                "interface": "CAN bus",
                "protection": "IP54",
                "dimensions": "150x100x40mm"
            },
            "compatibility": ["All Motor Series", "Industrial Line"],
            "supplier_codes": ["SUP123"],
            "min_order_qty": 1,
            "unit_cost": 179.99,
            "retail_price": 299.99,
            "stock_level": 15,
            "reorder_point": 10,
            "category": "Controllers",
            "alternatives": ["CTR-80-DIG"]
        },
        {
            "part_number": "SNS-TPM-200",
            "name": "Temperature Sensor Premium",
            "description": "High-precision digital temperature sensor. -40°C to +200°C range.",
            "technical_specs": {
                "range": "-40°C to 200°C",
                "accuracy": "±0.1°C",
                "response_time": "0.5s",
                "output": "4-20mA",
                "protection": "IP67"
            },
            "compatibility": ["All Series"],
            "supplier_codes": ["SUP789"],
            "min_order_qty": 5,
            "unit_cost": 45.99,
            "retail_price": 89.99,
            "stock_level": 100,
            "reorder_point": 25,
            "category": "Sensors",
            "alternatives": ["SNS-TPM-100"]
        },
        {
            "part_number": "BRK-200-HYD",
            "name": "Hydraulic Brake Assembly",
            "description": "Heavy-duty hydraulic brake with ceramic pads. DOT 5.1 compatible.",
            "technical_specs": {
                "fluid": "DOT 5.1",
                "pad_material": "ceramic",
                "max_pressure": "2000psi",
                "weight": "1.8kg",
                "pad_thickness": "4mm"
            },
            "compatibility": ["Heavy Duty Series", "Industrial Line"],
            "supplier_codes": ["SUP234", "BRK567"],
            "min_order_qty": 2,
            "unit_cost": 159.99,
            "retail_price": 299.99,
            "stock_level": 3,
            "reorder_point": 6,
            "category": "Brakes",
            "alternatives": ["BRK-180-HYD"]
        },
        {
            "part_number": "CAB-SHD-100",
            "name": "Shielded Power Cable",
            "description": "High-flexibility shielded power cable. Double insulated.",
            "technical_specs": {
                "gauge": "8 AWG",
                "length": "100m",
                "voltage_rating": "600V",
                "shield_type": "braided copper",
                "temperature_rating": "105°C"
            },
            "compatibility": ["All Series"],
            "supplier_codes": ["SUP345"],
            "min_order_qty": 1,
            "unit_cost": 89.99,
            "retail_price": 149.99,
            "stock_level": 50,
            "reorder_point": 10,
            "category": "Cables",
            "alternatives": ["CAB-SHD-50"]
        },
        {
            "part_number": "FAN-120-HF",
            "name": "High-Flow Cooling Fan",
            "description": "120mm high-flow cooling fan with PWM control. Low noise design.",
            "technical_specs": {
                "size": "120mm",
                "airflow": "95CFM",
                "noise": "28dB",
                "voltage": "12V",
                "power": "4.8W"
            },
            "compatibility": ["Cooling Series", "Standard Line"],
            "supplier_codes": ["SUP678"],
            "min_order_qty": 4,
            "unit_cost": 18.99,
            "retail_price": 34.99,
            "stock_level": 200,
            "reorder_point": 50,
            "category": "Cooling",
            "alternatives": ["FAN-120-STD"]
        },
        {
            "part_number": "PWR-500-DC",
            "name": "DC Power Supply",
            "description": "500W DC power supply with active PFC. 90% efficiency.",
            "technical_specs": {
                "power": "500W",
                "input_voltage": "110-240V AC",
                "output_voltage": "48V DC",
                "efficiency": "90%",
                "protection": "OVP, OCP, SCP"
            },
            "compatibility": ["Power Series", "Industrial Line"],
            "supplier_codes": ["SUP901"],
            "min_order_qty": 1,
            "unit_cost": 129.99,
            "retail_price": 219.99,
            "stock_level": 8,
            "reorder_point": 5,
            "category": "Power Supplies",
            "alternatives": ["PWR-600-DC"]
        },
        {
            "part_number": "CNT-CAN-ISO",
            "name": "Isolated CAN Converter",
            "description": "Galvanically isolated CAN bus converter with status LEDs.",
            "technical_specs": {
                "isolation": "2500V",
                "protocols": "CAN 2.0A/B",
                "baud_rate": "1Mbps",
                "power_supply": "5V DC",
                "protection": "ESD, surge"
            },
            "compatibility": ["All CAN Series"],
            "supplier_codes": ["SUP234"],
            "min_order_qty": 1,
            "unit_cost": 45.99,
            "retail_price": 79.99,
            "stock_level": 25,
            "reorder_point": 10,
            "category": "Communication",
            "alternatives": ["CNT-CAN-STD"]
        }
    ]

def run_enhanced_demo(example_queries):
    # Initialize search
    search = EnhancedSparePartsSearch()
    print("Indexing enhanced spare parts...")
    search.index_parts(test_data)
    time.sleep(1)
    
    # Run test queries
    for query, explanation in example_queries:
        search.compare_searches(query, explanation)
        time.sleep(0.5)

def run_comparison_demo(example_queries):
    search = EnhancedSparePartsSearch()
    print("Indexing spare parts...")
    search.index_parts(test_data)
    time.sleep(1)
    
    for query, explanation in example_queries:
        search.compare_searches(query, explanation)
        time.sleep(0.5)
# Example usage
if __name__ == "__main__":
    # Enhanced test data with more technical specifications
    # Previous classes (SpecParser, InventoryAnalyzer, EnhancedSparePartsSearch) remain the same
    # Adding comprehensive test data:
    # Example queries to demonstrate various scenarios
    example_queries = [
        (
            "48V battery alternatives with similar capacity",
            "Cross-reference search with technical matching"
        ),
        (
            "replacement controller compatible with brushless motors under $300",
            "Compatibility search with price constraint"
        ),
        (
            "high precision temperature sensors with good stock",
            "Technical specification + inventory status"
        ),
        (
            "power supplies with efficiency over 85% and critical stock",
            "Technical threshold + inventory status"
        ),
        (
            "shielded cables rated for at least 500V",
            "Technical specification threshold"
        ),
        (
            "cooling solution for power systems with low noise",
            "Application-based search with performance criteria"
        ),
        (
            "CAN interface components with isolation",
            "Technical feature search"
        ),
        (
            "heavy duty brakes with ceramic pads low stock alert",
            "Product type + specific feature + inventory status"
        )
    ]

    run_comparison_demo(example_queries)