from elasticsearch import Elasticsearch
from typing import Dict, List, Optional, Tuple
from sentence_transformers import SentenceTransformer
import spacy
from dataclasses import dataclass
import logging
import re

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

class SmartEquipmentSearch:
    def __init__(self, host: str = "http://localhost:9200"):
        self.es = Elasticsearch([host])
        
        # Define indices
        self.tenant_indices = {
            "tenant1": "tenant1_equipment",
            "tenant2": "tenant2_equipment"
        }
        self.marketplace_index = "marketplace_equipment"
        
        # Initialize NLP models
        self.nlp = spacy.load("en_core_web_sm")
        self.embedding_model = SentenceTransformer('all-mpnet-base-v2')
        
        # Equipment taxonomy
        self.equipment_categories = {
            "pump": "pumps", "pumps": "pumps",
            "heat exchanger": "heat_exchangers", "heat exchangers": "heat_exchangers",
            "turbine": "turbines", "turbines": "turbines",
            "boiler": "boilers", "boilers": "boilers"
        }
        
        # Specification patterns
        self.spec_patterns = {
            "flow": r"(\d+(?:\.\d+)?)\s*(m3/hr?|m³/hr?|gpm|l/hr)",
            "pressure": r"(\d+(?:\.\d+)?)\s*(bar|psi|kPa)",
            "temperature": r"(\d+(?:\.\d+)?)\s*(°?C|°?F)",
            "power": r"(\d+(?:\.\d+)?)\s*(kW|MW|hp)"
        }

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
        
        # Extract specifications
        for spec_type, pattern in self.spec_patterns.items():
            matches = re.finditer(pattern, query.lower())
            for match in matches:
                value, unit = match.groups()
                intent.specs.append({
                    "type": spec_type,
                    "value": float(value),
                    "unit": unit
                })
        
        # Check for availability requirements
        if any(word in query.lower() for word in ["available", "immediate", "in stock"]):
            intent.availability_required = True
        
        # Extract locations
        for ent in doc.ents:
            if ent.label_ in ["GPE", "LOC"]:
                intent.locations.append(ent.text.lower())
        
        # Extract conditions
        conditions = ["new", "used", "refurbished"]
        intent.conditions = [word for word in conditions if word in query.lower()]
        
        return intent

    def build_elasticsearch_query(self, intent: SearchIntent) -> Dict:
        """Build Elasticsearch query from search intent"""
        must_clauses = []
        should_clauses = []
        filter_clauses = []
        
        # Category matching
        if intent.category:
            filter_clauses.append({"term": {"category": intent.category}})
        
        # Specification matching
        for spec in intent.specs:
            spec_query = {
                "nested": {
                    "path": "specifications",
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"specifications.parameter": spec["type"]}},
                                {
                                    "range": {
                                        "specifications.value": {
                                            "gte": spec["value"] * 0.8,  # 20% tolerance below
                                            "lte": spec["value"] * 1.2   # 20% tolerance above
                                        }
                                    }
                                }
                            ]
                        }
                    }
                }
            }
            filter_clauses.append(spec_query)

        # Location matching
        if intent.locations:
            location_query = {
                "nested": {
                    "path": "location",
                    "query": {
                        "terms": {"location.country": intent.locations}
                    }
                }
            }
            filter_clauses.append(location_query)

        # Availability matching
        if intent.availability_required:
            availability_query = {
                "nested": {
                    "path": "location",
                    "query": {
                        "term": {"location.availability": "immediate"}
                    }
                }
            }
            filter_clauses.append(availability_query)

        # Condition matching
        if intent.conditions:
            filter_clauses.append({"terms": {"condition": intent.conditions}})

        # Combine everything
        return {
            "bool": {
                "must": must_clauses,
                "should": should_clauses,
                "filter": filter_clauses,
                "minimum_should_match": 0
            }
        }

    def search_with_suggestions(self, tenant_id: str, query: str) -> Dict[str, List[Dict]]:
        """
        Smart search with marketplace suggestions when tenant inventory is insufficient
        """
        try:
            # Parse the natural language query
            intent = self.parse_natural_query(query)
            
            # Build Elasticsearch query
            es_query = self.build_elasticsearch_query(intent)
            
            # Search in tenant's own inventory
            tenant_results = self.es.search(
                index=self.tenant_indices[tenant_id],
                query=es_query,
                size=10
            )
            
            tenant_hits = [
                {
                    **hit["_source"],
                    "score": hit["_score"]
                }
                for hit in tenant_results["hits"]["hits"]
            ]
            
            suggestions = []
            
            # If tenant results are limited or missing key specifications,
            # search marketplace for suggestions
            if len(tenant_hits) < 3 or any(spec["type"] not in 
                [s["parameter"] for item in tenant_hits 
                 for s in item["specifications"]] for spec in intent.specs):
                
                marketplace_results = self.es.search(
                    index=self.marketplace_index,
                    query=es_query,
                    size=5
                )
                
                suggestions = [
                    {
                        **hit["_source"],
                        "score": hit["_score"],
                        "suggestion_type": "marketplace_alternative"
                    }
                    for hit in marketplace_results["hits"]["hits"]
                    if hit["_source"]["tenant_id"] != tenant_id
                ]

            # Generate helpful insights about the suggestions
            suggestion_insights = self._generate_suggestions_insight(
                tenant_hits, suggestions, intent)

            return {
                "tenant_inventory": tenant_hits,
                "marketplace_suggestions": suggestions,
                "insights": suggestion_insights
            }
            
        except Exception as e:
            logger.error(f"Error in search_with_suggestions: {e}")
            return {
                "tenant_inventory": [],
                "marketplace_suggestions": [],
                "insights": []
            }

    def _generate_suggestions_insight(
        self, tenant_hits: List[Dict], suggestions: List[Dict], intent: SearchIntent
    ) -> List[str]:
        """Generate insights about why certain suggestions are made"""
        insights = []

        if not tenant_hits and suggestions:
            insights.append(
                "No matching equipment found in your inventory. Here are some "
                "marketplace alternatives that match your requirements."
            )

        # Compare specifications
        if intent.specs:
            tenant_specs = set(
                s["parameter"] 
                for item in tenant_hits 
                for s in item["specifications"]
            )
            
            missing_specs = [
                spec["type"] for spec in intent.specs 
                if spec["type"] not in tenant_specs
            ]
            
            if missing_specs:
                insights.append(
                    f"Your inventory lacks equipment with specified "
                    f"{', '.join(missing_specs)}. Showing marketplace items that "
                    "match these specifications."
                )

        # Price comparison insights
        if suggestions and tenant_hits:
            avg_tenant_price = sum(
                float(item["price"]["value"]) 
                for item in tenant_hits 
                if "price" in item
            ) / len(tenant_hits)
            
            avg_suggestion_price = sum(
                float(item["price"]["value"]) 
                for item in suggestions 
                if "price" in item
            ) / len(suggestions)
            
            if avg_suggestion_price < avg_tenant_price * 0.9:
                insights.append(
                    "Some marketplace alternatives are available at lower prices "
                    "than your current inventory."
                )

        return insights

# Example usage
if __name__ == "__main__":
    search = SmartEquipmentSearch()
    
    # Example queries showing different scenarios
    example_queries = [
        # Tenant1 (Chemical Processing Company) Queries
        ("tenant1", "looking for a pump with flow rate 2000 m3/hr"),
        ("tenant1", "need an immediate availability heat exchanger"),
        ("tenant1", "high pressure pump available in Germany"),
        
        # Tenant2 (Power Generation Company) Queries
        ("tenant2", "steam turbine with power output 60MW"),
        ("tenant2", "industrial boiler with immediate availability"),
        ("tenant2", "need a gas turbine with high efficiency")
    ]
    
    for tenant_id, query in example_queries:
        print(f"\nProcessing query for {tenant_id}: {query}")
        results = search.search_with_suggestions(tenant_id, query)
        
        print("\nTenant Inventory Results:")
        for item in results["tenant_inventory"]:
            print(f"- {item['name']} ({item['manufacturer']} {item['model']})")
            print(f"  Specifications: {item['specifications']}")
            
        if results["marketplace_suggestions"]:
            print("\nMarketplace Suggestions:")
            for item in results["marketplace_suggestions"]:
                print(f"- {item['name']} ({item['manufacturer']} {item['model']})")
                print(f"  Specifications: {item['specifications']}")
        
        if results["insights"]:
            print("\nInsights:")
            for insight in results["insights"]:
                print(f"* {insight}")