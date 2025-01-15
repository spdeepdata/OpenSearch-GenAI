from elasticsearch import Elasticsearch
import logging
from typing import Dict, List, Optional
import spacy
from sentence_transformers import SentenceTransformer
import hashlib
import re
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SearchIntent:
    category: Optional[str]
    specifications: List[Dict]
    conditions: List[str]
    locations: List[str]
    availability_required: bool

class ShardedSearchUtility:
    def __init__(self, host: str = "http://localhost:9200"):
        self.es = Elasticsearch([host])
        self.equipment_index = "sharded_equipment"
        self.tenant_index = "tenant_metadata"
        
        # Initialize NLP components
        self.nlp = spacy.load("en_core_web_sm")
        self.embedding_model = SentenceTransformer('all-mpnet-base-v2')
        
        # Equipment categories mapping
        self.categories = {
            "pump": "pumps",
            "pumps": "pumps",
            "turbine": "turbines",
            "turbines": "turbines",
            "heat exchanger": "heat_exchangers",
            "boiler": "boilers"
        }
        
        # Specification patterns
        self.spec_patterns = {
            "flow": r"(\d+(?:\.\d+)?)\s*(m3/hr?|gpm)",
            "pressure": r"(\d+(?:\.\d+)?)\s*(bar|psi)",
            "power": r"(\d+(?:\.\d+)?)\s*(kW|MW)"
        }

    def _get_tenant_routing(self, tenant_id: str) -> str:
        """Get routing key for tenant"""
        try:
            result = self.es.get(
                index=self.tenant_index,
                id=tenant_id
            )
            return result["_source"]["routing_key"]
        except Exception as e:
            logger.error(f"Error getting tenant routing: {e}")
            return None

    def parse_query(self, query_text: str) -> SearchIntent:
        """Parse natural language query into structured intent"""
        doc = self.nlp(query_text.lower())
        
        intent = SearchIntent(
            category=None,
            specifications=[],
            conditions=[],
            locations=[],
            availability_required=False
        )
        
        # Extract category
        words = query_text.lower().split()
        for i in range(len(words)):
            for j in range(i + 1, len(words) + 1):
                phrase = " ".join(words[i:j])
                if phrase in self.categories:
                    intent.category = self.categories[phrase]
                    break
        
        # Extract specifications
        for spec_type, pattern in self.spec_patterns.items():
            matches = re.finditer(pattern, query_text.lower())
            for match in matches:
                value, unit = match.groups()
                intent.specifications.append({
                    "type": spec_type,
                    "value": float(value),
                    "unit": unit
                })
        
        # Extract locations
        for ent in doc.ents:
            if ent.label_ in ["GPE", "LOC"]:
                intent.locations.append(ent.text.lower())
        
        # Check availability requirement
        availability_terms = ["available", "immediate", "in stock"]
        intent.availability_required = any(term in query_text.lower() 
                                        for term in availability_terms)
        
        return intent

    def build_query(self, intent: SearchIntent) -> Dict:
        """Build Elasticsearch query from intent"""
        must_clauses = []
        filter_clauses = []
        
        # Category filter
        if intent.category:
            filter_clauses.append({"term": {"category": intent.category}})
        
        # Specifications
        for spec in intent.specifications:
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
            filter_clauses.append(spec_query)
        
        # Location filter
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
        
        # Availability filter
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
        
        return {
            "bool": {
                "must": must_clauses,
                "filter": filter_clauses
            }
        }

    def search(self, tenant_id: str, query_text: str, 
               include_marketplace: bool = True) -> Dict[str, List[Dict]]:
        """
        Perform sharded search with marketplace integration
        """
        try:
            # Get tenant's routing key
            routing_key = self._get_tenant_routing(tenant_id)
            if not routing_key:
                raise ValueError(f"Tenant not found: {tenant_id}")
            
            # Parse query
            intent = self.parse_query(query_text)
            es_query = self.build_query(intent)
            
            # Search tenant's own inventory
            tenant_results = self.es.search(
                index=self.equipment_index,
                query=es_query,
                routing=routing_key,  # Use routing for better performance
                size=10
            )
            
            results = {
                "tenant_inventory": [
                    hit["_source"] for hit in tenant_results["hits"]["hits"]
                ],
                "marketplace_suggestions": []
            }
            
            # Search marketplace listings if enabled
            if include_marketplace:
                # Add marketplace filter
                marketplace_query = {
                    "bool": {
                        "must": es_query["bool"]["must"],
                        "filter": [
                            *es_query["bool"]["filter"],
                            {"term": {"marketplace_listing": True}},
                            {"bool": {"must_not": {"term": {"tenant_id": tenant_id}}}}
                        ]
                    }
                }
                
                # Search across all shards for marketplace items
                marketplace_results = self.es.search(
                    index=self.equipment_index,
                    query=marketplace_query,
                    size=5,
                    # Don't use routing for marketplace search
                    # to search across all shards
                )
                
                results["marketplace_suggestions"] = [
                    hit["_source"] for hit in marketplace_results["hits"]["hits"]
                ]
            
            # Generate insights
            results["insights"] = self._generate_insights(
                results["tenant_inventory"],
                results["marketplace_suggestions"],
                intent
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error in search: {e}")
            return {
                "tenant_inventory": [],
                "marketplace_suggestions": [],
                "insights": []
            }

    def _generate_insights(
        self, 
        tenant_results: List[Dict], 
        marketplace_results: List[Dict], 
        intent: SearchIntent
    ) -> List[str]:
        """Generate search insights and recommendations"""
        insights = []
        
        # No results insight
        if not tenant_results and marketplace_results:
            insights.append(
                "No matching equipment found in your inventory. Here are some "
                "marketplace alternatives that match your requirements."
            )
        
        # Specification comparison
        if tenant_results and marketplace_results:
            # Compare average specifications
            tenant_specs = {}
            marketplace_specs = {}
            
            # Collect average specifications
            for result in tenant_results:
                for spec in result.get("specifications", []):
                    if spec["parameter"] not in tenant_specs:
                        tenant_specs[spec["parameter"]] = []
                    tenant_specs[spec["parameter"]].append(spec["value"])
            
            for result in marketplace_results:
                for spec in result.get("specifications", []):
                    if spec["parameter"] not in marketplace_specs:
                        marketplace_specs[spec["parameter"]] = []
                    marketplace_specs[spec["parameter"]].append(spec["value"])
            
            # Calculate averages
            tenant_avg = {
                param: sum(values) / len(values)
                for param, values in tenant_specs.items()
            }
            
            marketplace_avg = {
                param: sum(values) / len(values)
                for param, values in marketplace_specs.items()
            }
            
            # Compare and generate insights
            for param in set(tenant_avg.keys()) | set(marketplace_avg.keys()):
                if param in tenant_avg and param in marketplace_avg:
                    diff_percent = ((marketplace_avg[param] - tenant_avg[param]) 
                                  / tenant_avg[param] * 100)
                    if abs(diff_percent) > 20:  # Significant difference
                        insights.append(
                            f"Marketplace alternatives offer {abs(diff_percent):.0f}% "
                            f"{'higher' if diff_percent > 0 else 'lower'} "
                            f"{param} on average."
                        )
        
        # Price insights
        if tenant_results and marketplace_results:
            try:
                # Calculate average prices (converting to USD for comparison)
                def get_usd_price(item):
                    price = item.get("price", {})
                    value = price.get("value", 0)
                    currency = price.get("currency", "USD")
                    # Simple conversion rates for demo
                    rates = {"EUR": 1.1, "GBP": 1.3, "USD": 1.0}
                    return value * rates.get(currency, 1.0)
                
                tenant_avg_price = sum(get_usd_price(r) for r in tenant_results) / len(tenant_results)
                market_avg_price = sum(get_usd_price(r) for r in marketplace_results) / len(marketplace_results)
                
                price_diff_percent = ((market_avg_price - tenant_avg_price) 
                                    / tenant_avg_price * 100)
                
                if abs(price_diff_percent) > 15:  # Significant price difference
                    insights.append(
                        f"Marketplace alternatives are {abs(price_diff_percent):.0f}% "
                        f"{'more expensive' if price_diff_percent > 0 else 'cheaper'} "
                        f"on average."
                    )
            except Exception as e:
                logger.warning(f"Error generating price insights: {e}")
        
        return insights


# Example usage and testing
if __name__ == "__main__":
    search_utility = ShardedSearchUtility()
    
    # Test queries
    test_queries = [
        # Tenant1 queries
        ("tenant1", "looking for a pump with flow rate 2000 m3/hr"),
        ("tenant1", "need an immediate availability heat exchanger"),
        ("tenant1", "high pressure pump available in Germany"),
        
        # Tenant2 queries
        ("tenant2", "steam turbine with power output 60MW"),
        ("tenant2", "industrial boiler with immediate availability"),
        ("tenant2", "need a gas turbine with high efficiency")
    ]
    
    for tenant_id, query in test_queries:
        print(f"\nProcessing search for {tenant_id}")
        print(f"Query: {query}")
        
        results = search_utility.search(tenant_id, query)
        
        print("\nTenant Inventory Results:")
        for item in results["tenant_inventory"]:
            print(f"- {item['name']} ({item['manufacturer']} {item['model']})")
            print(f"  Specifications: {item['specifications']}")
            if "price" in item:
                print(f"  Price: {item['price']['currency']} {item['price']['value']:,.2f}")
            
        if results["marketplace_suggestions"]:
            print("\nMarketplace Suggestions:")
            for item in results["marketplace_suggestions"]:
                print(f"- {item['name']} ({item['manufacturer']} {item['model']})")
                print(f"  Specifications: {item['specifications']}")
                if "price" in item:
                    print(f"  Price: {item['price']['currency']} {item['price']['value']:,.2f}")
        
        if results["insights"]:
            print("\nInsights:")
            for insight in results["insights"]:
                print(f"* {insight}")
        
        print("\n" + "="*80)