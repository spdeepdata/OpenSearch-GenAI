from elasticsearch import Elasticsearch
from typing import Dict, List, Optional, Tuple
from sentence_transformers import SentenceTransformer
import spacy
import numpy as np
from dataclasses import dataclass
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SearchIntent:
    category: Optional[str]
    specs: List[Dict[str, str]]
    conditions: List[str]
    locations: List[str]
    availability_required: bool
    price_range: Optional[Dict[str, float]]

class NLPEquipmentSearch:
    def __init__(self, host: str = "http://localhost:9200"):
        self.es = Elasticsearch([host])
        self.internal_index = "internal_equipment"
        self.partner_index = "partner_equipment"
        
        # Initialize NLP models
        self.nlp = spacy.load("en_core_web_sm")
        self.embedding_model = SentenceTransformer('all-mpnet-base-v2')
        
        # Equipment taxonomy with variations
        self.equipment_categories = {
            "pump": "pumps",
            "pumps": "pumps",
            "compressor": "compressors",
            "compressors": "compressors",
            "turbine": "turbines",
            "turbines": "turbines",
            "valve": "valves",
            "valves": "valves",
            "heat exchanger": "heat_exchangers",
            "heat exchangers": "heat_exchangers",
            "boiler": "boilers",
            "boilers": "boilers",
            "filter": "filtration",
            "filters": "filtration",
            "mill": "mills",
            "mills": "mills",
            "reactor": "reactors",
            "reactors": "reactors",
            "dryer": "dryers",
            "dryers": "dryers"
        }
        
        # Specification patterns with variations
        self.spec_patterns = {
            "flow": r"(\d+(?:\.\d+)?)\s*(m3/hr?|m³/hr?|gpm)",
            "pressure": r"(\d+(?:\.\d+)?)\s*(bar|psi|kPa)",
            "temperature": r"(\d+(?:\.\d+)?)\s*(°?C|°?F|celsius|fahrenheit)",
            "power": r"(\d+(?:\.\d+)?)\s*(kW|hp|MW)",
            "capacity": r"(\d+(?:\.\d+)?)\s*(tons?/hr|kg/hr|t/hr)"
        }

    def _create_indices_if_not_exist(self):
        """Create indices with proper mappings if they don't exist"""
        mapping = {
            "mappings": {
                "properties": {
                    "name": {"type": "text"},
                    "description": {"type": "text"},
                    "category": {"type": "keyword"},
                    "manufacturer": {"type": "keyword"},
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
                    "condition": {"type": "keyword"}
                }
            }
        }

        for index in [self.internal_index, self.partner_index]:
            if not self.es.indices.exists(index=index):
                self.es.indices.create(index=index, body=mapping)
                logger.info(f"Created index: {index}")

    def parse_natural_query(self, query: str) -> SearchIntent:
        """Parse natural language query into structured search intent"""
        doc = self.nlp(query.lower())
        
        intent = SearchIntent(
            category=None,
            specs=[],
            conditions=[],
            locations=[],
            availability_required=False,
            price_range=None
        )
        
        # Extract equipment category
        words = query.lower().split()
        for i in range(len(words)):
            for j in range(i + 1, len(words) + 1):
                phrase = " ".join(words[i:j])
                if phrase in self.equipment_categories:
                    intent.category = self.equipment_categories[phrase]
                    break
        
        # Extract specifications with better error handling
        for spec_type, pattern in self.spec_patterns.items():
            try:
                matches = re.finditer(pattern, query.lower())
                for match in matches:
                    value, unit = match.groups()
                    intent.specs.append({
                        "type": spec_type,
                        "value": float(value),
                        "unit": unit
                    })
            except Exception as e:
                logger.warning(f"Error parsing specification {spec_type}: {e}")
        
        # Check for availability requirements
        availability_keywords = ["available", "in stock", "immediate", "ready"]
        if any(keyword in query.lower() for keyword in availability_keywords):
            intent.availability_required = True
        
        # Extract locations with better entity recognition
        for ent in doc.ents:
            if ent.label_ in ["GPE", "LOC"]:
                intent.locations.append(ent.text.lower())
        
        # Extract conditions
        condition_keywords = ["new", "used", "refurbished", "reconditioned"]
        intent.conditions = [word for word in condition_keywords 
                           if word in query.lower()]
        
        # Extract price information with better pattern matching
        price_patterns = [
            r"(?:under|less than|max|maximum|up to)\s*[\$€£]?\s*(\d+(?:\.\d+)?[k,m]?)",
            r"[\$€£]\s*(\d+(?:\.\d+)?[k,m]?)",
            r"(\d+(?:\.\d+)?[k,m]?)\s*(?:dollars|euros|pounds)"
        ]
        
        for pattern in price_patterns:
            price_match = re.search(pattern, query.lower())
            if price_match:
                price_str = price_match.group(1)
                multiplier = 1000 if 'k' in price_str else 1000000 if 'm' in price_str else 1
                base_price = float(re.sub('[km]', '', price_str))
                intent.price_range = {"max": base_price * multiplier}
                break
        
        return intent

    def build_elasticsearch_query(self, intent: SearchIntent) -> Dict:
        """Build Elasticsearch query from search intent"""
        query = {
            "bool": {
                "must": [
                    {
                        "match_all": {}
                    }
                ],
                "filter": []
            }
        }

        # Add category filter
        if intent.category:
            query["bool"]["filter"].append({
                "term": {"category": intent.category}
            })

        # Add specification filters
        for spec in intent.specs:
            spec_filter = {
                "nested": {
                    "path": "specifications",
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"specifications.parameter": spec["type"]}},
                                {
                                    "range": {
                                        "specifications.value": {
                                            "gte": spec["value"] * 0.8,
                                            "lte": spec["value"] * 1.2
                                        }
                                    }
                                }
                            ]
                        }
                    }
                }
            }
            query["bool"]["filter"].append(spec_filter)

        # Add availability filter
        if intent.availability_required:
            query["bool"]["filter"].append({
                "nested": {
                    "path": "location",
                    "query": {
                        "term": {"location.availability": "immediate"}
                    }
                }
            })

        # Add location filter
        if intent.locations:
            query["bool"]["filter"].append({
                "nested": {
                    "path": "location",
                    "query": {
                        "terms": {"location.country": intent.locations}
                    }
                }
            })

        # Add price filter
        if intent.price_range:
            query["bool"]["filter"].append({
                "nested": {
                    "path": "price",
                    "query": {
                        "range": {
                            "price.value": {
                                "lte": intent.price_range.get("max")
                            }
                        }
                    }
                }
            })

        # Add condition filter
        if intent.conditions:
            query["bool"]["filter"].append({
                "terms": {"condition": intent.conditions}
            })

        return query

    def search_equipment(self, query: str) -> Dict[str, List[Dict]]:
        """
        Perform equipment search using natural language query
        """
        try:
            # Ensure indices exist
            self._create_indices_if_not_exist()
            
            # Parse query intent
            intent = self.parse_natural_query(query)
            
            # Build and execute query
            es_query = self.build_elasticsearch_query(intent)
            return self._execute_search(es_query)
            
        except Exception as e:
            logger.error(f"Error in search_equipment: {e}")
            return {"internal": [], "partner": []}

    def _execute_search(self, query: Dict) -> Dict[str, List[Dict]]:
        """Execute search across both indices with better error handling"""
        results = {"internal": [], "partner": []}
        
        for source, index in [("internal", self.internal_index), 
                            ("partner", self.partner_index)]:
            try:
                search_results = self.es.search(
                    index=index,
                    query=query,
                    size=20
                )
                
                results[source] = [
                    {
                        **hit["_source"],
                        "score": hit["_score"]
                    }
                    for hit in search_results["hits"]["hits"]
                ]
            except Exception as e:
                logger.error(f"Error searching {source} inventory: {e}")
                results[source] = []
                
        return results

    def explain_search(self, query: str) -> Tuple[SearchIntent, Dict[str, List[Dict]]]:
        """
        Perform search and return both results and explanation of how the query was understood
        """
        intent = self.parse_natural_query(query)
        results = self.search_equipment(query)
        return intent, results

# Example usage
if __name__ == "__main__":
    search = NLPEquipmentSearch()
    
    # Example natural language queries
    example_queries = [
        "I need a high capacity pump with flow rate over 1000 m3/hr",
        "Show me available heat exchangers in Germany under $100k",
        "Looking for new compressors with power rating 250kW",
        "Find me industrial boilers with steam capacity 15 tons/hr in UK",
        "Show me pumps under €50k",
        "Need immediate availability turbines in USA"
    ]
    
    for query in example_queries:
        print(f"\nProcessing query: {query}")
        intent, results = search.explain_search(query)
        
        print("\nUnderstood Search Intent:")
        print(f"Category: {intent.category}")
        print(f"Specifications: {intent.specs}")
        print(f"Conditions: {intent.conditions}")
        print(f"Locations: {intent.locations}")
        print(f"Availability Required: {intent.availability_required}")
        print(f"Price Range: {intent.price_range}")
        
        print("\nSearch Results:")
        for source in ["internal", "partner"]:
            print(f"\n{source.upper()} RESULTS:")
            for item in results[source]:
                print(f"- {item.get('name', 'Unnamed')} "
                      f"({item.get('manufacturer', 'Unknown')} {item.get('model', 'Unknown')})")
                if 'price' in item:
                    print(f"  Price: {item['price'].get('currency', 'USD')} "
                          f"{item['price'].get('value', 0):,.2f}")
                if 'location' in item:
                    print(f"  Location: {item['location'].get('country', 'Unknown')}")
                    print(f"  Availability: {item['location'].get('availability', 'Unknown')}")