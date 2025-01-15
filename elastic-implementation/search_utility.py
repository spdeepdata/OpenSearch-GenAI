from elasticsearch import Elasticsearch
from typing import Dict, List, Optional
import json

class EquipmentSearch:
    def __init__(self, host: str = "http://localhost:9200"):
        self.es = Elasticsearch([host])
        self.internal_index = "internal_equipment"
        self.partner_index = "partner_equipment"

    def search_equipment(self,
                        query: str,
                        category: Optional[str] = None,
                        min_year: Optional[int] = None,
                        condition: Optional[str] = None,
                        available_within_days: Optional[int] = None,
                        location_country: Optional[str] = None) -> Dict[str, List[Dict]]:
        """
        Search for equipment, prioritizing internal inventory over partner inventory
        """
        def build_query(query_text: str) -> Dict:
            """Build the elasticsearch query with filters"""
            search_query = {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query_text,
                                "fields": [
                                    "name^3",
                                    "description^2",
                                    "manufacturer",
                                    "model",
                                    "category.text"
                                ]
                            }
                        }
                    ],
                    "filter": []
                }
            }

            if category:
                search_query["bool"]["filter"].append(
                    {"term": {"category": category}}
                )

            if min_year:
                search_query["bool"]["filter"].append(
                    {"range": {"year_manufactured": {"gte": min_year}}}
                )

            if condition:
                search_query["bool"]["filter"].append(
                    {"term": {"condition": condition}}
                )

            if available_within_days:
                availability_filter = {
                    "nested": {
                        "path": "location",
                        "query": {
                            "terms": {
                                "location.availability": [
                                    "immediate",
                                    "1-week",
                                    "2-weeks"
                                ][:available_within_days // 7 + 1]
                            }
                        }
                    }
                }
                search_query["bool"]["filter"].append(availability_filter)

            if location_country:
                location_filter = {
                    "nested": {
                        "path": "location",
                        "query": {
                            "term": {"location.country": location_country}
                        }
                    }
                }
                search_query["bool"]["filter"].append(location_filter)

            return search_query

        results = {}
        
        # Search in both indices
        for source in ["internal", "partner"]:
            index = self.internal_index if source == "internal" else self.partner_index
            
            try:
                search_results = self.es.search(
                    index=index,
                    query=build_query(query),
                    size=20,
                    sort=[
                        {"_score": {"order": "desc"}},
                        {"last_updated": {"order": "desc"}}
                    ]
                )
                
                results[source] = [
                    {
                        **hit["_source"],
                        "relevance_score": hit["_score"]
                    }
                    for hit in search_results["hits"]["hits"]
                ]
            except Exception as e:
                print(f"Error searching {source} inventory: {e}")
                results[source] = []

        return results

def print_results(results: Dict[str, List[Dict]]):
    """Helper function to print search results in a readable format"""
    for source in ["internal", "partner"]:
        print(f"\n{source.upper()} RESULTS:")
        if not results[source]:
            print("No results found")
            continue
            
        for item in results[source]:
            print("\n---")
            print(f"Name: {item['name']}")
            print(f"Category: {item['category']} / {item['subcategory']}")
            print(f"Manufacturer: {item['manufacturer']}")
            print(f"Location: {item['location']['city']}, {item['location']['country']}")
            print(f"Availability: {item['location']['availability']}")
            print(f"Price: {item['price']['currency']} {item['price']['value']:,.2f}")
            print(f"Stock: {item['stock']['quantity']} units")
            print(f"Score: {item['relevance_score']:.2f}")

if __name__ == "__main__":
    # Initialize search
    search = EquipmentSearch()
    
    # Example 1: Search for turbines
    print("\nSearch Example 1: Turbines")
    print("-------------------------")
    results = search.search_equipment(
        query="turbine power generation",
        category="turbines",
        available_within_days=7
    )
    print_results(results)
    
    # Example 2: Search for pumps in USA
    print("\nSearch Example 2: Pumps in USA")
    print("-------------------------")
    results = search.search_equipment(
        query="pump",
        category="pumps",
        location_country="USA"
    )
    print_results(results)
    
    # Example 3: Search for cooling equipment
    print("\nSearch Example 3: Cooling Equipment")
    print("-------------------------")
    results = search.search_equipment(
        query="cooling",
        condition="new"
    )
    print_results(results)
    
    # Example 4: Search for all equipment in Germany
    print("\nSearch Example 4: Equipment in Germany")
    print("-------------------------")
    results = search.search_equipment(
        query="*",
        location_country="Germany"
    )
    print_results(results)