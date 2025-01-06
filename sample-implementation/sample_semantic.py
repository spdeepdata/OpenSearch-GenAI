from opensearchpy import OpenSearch, helpers, ConnectionTimeout, RequestError, TransportError, NotFoundError
from opensearchpy.connection import RequestsHttpConnection
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import time
import spacy
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import cachetools

class OptimizedInventorySearch:
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 9200,
        index_name: str = 'inventory',
        http_auth: tuple = None,
        timeout: int = 30
    ):
        try:
            self.client = OpenSearch(
                hosts=[{'host': host, 'port': port}],
                http_auth=http_auth,
                use_ssl=False,
                verify_certs=False,
                ssl_show_warn=False,
                scheme="http",
                timeout=timeout,
                max_retries=3,
                retry_on_timeout=True,
                connection_class=RequestsHttpConnection
            )
            
            self.client.info()
            print("Successfully connected to OpenSearch")
            
        except ConnectionError as e:
            print(f"Failed to connect to OpenSearch: {e}")
            raise
        
        self.index_name = index_name
        self.nlp = spacy.load("en_core_web_lg", disable=['parser', 'textcat'])
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=10000,
            stop_words='english'
        )
        
        self._ensure_index_exists()

    def _ensure_index_exists(self):
        """Ensure index exists with proper settings"""
        try:
            if not self.client.indices.exists(index=self.index_name):
                settings = {
                    "settings": {
                        "index": {
                            "number_of_shards": 3,
                            "number_of_replicas": 1,
                            "refresh_interval": "5s",
                            "analysis": {
                                "analyzer": {
                                    "custom_analyzer": {
                                        "type": "custom",
                                        "tokenizer": "standard",
                                        "filter": [
                                            "lowercase",
                                            "stop",
                                            "snowball",
                                            "word_delimiter"
                                        ]
                                    }
                                }
                            }
                        }
                    },
                    "mappings": {
                        "properties": {
                            "name": {
                                "type": "text",
                                "analyzer": "custom_analyzer",
                                "fields": {
                                    "keyword": {"type": "keyword"}
                                }
                            },
                            "description": {
                                "type": "text",
                                "analyzer": "custom_analyzer"
                            },
                            "category": {
                                "type": "keyword",
                                "fields": {
                                    "text": {"type": "text"}
                                }
                            },
                            "manufacturer": {
                                "properties": {
                                    "name": {
                                        "type": "text",
                                        "fields": {
                                            "keyword": {"type": "keyword"}
                                        }
                                    }
                                }
                            },
                            "unit_price": {"type": "float"},
                            "quantity": {"type": "integer"},
                            "minimum_stock": {"type": "integer"},
                            "tokens": {"type": "text"},
                            "last_updated": {"type": "date"}
                        }
                    }
                }
                
                self.client.indices.create(
                    index=self.index_name,
                    body=settings
                )
                print(f"Created index: {self.index_name}")
                
        except Exception as e:
            print(f"Error ensuring index exists: {e}")
            raise

    def index_item(self, item: Dict) -> Dict:
        """Index a single inventory item"""
        try:
            # Generate tokens and process text
            text_to_analyze = f"{item['name']} {item.get('description', '')}"
            doc = self.nlp(text_to_analyze)
            
            # Extract key terms and lemmas
            tokens = [token.lemma_.lower() for token in doc 
                     if not token.is_stop and not token.is_punct]
            
            # Add processed data
            indexed_item = {
                **item,
                'tokens': ' '.join(tokens),
                'last_updated': datetime.now().isoformat()
            }
            
            response = self.client.index(
                index=self.index_name,
                body=indexed_item,
                id=item['sku'],
                refresh=True
            )
            print(f"Successfully indexed item {item['sku']}")
            return response
            
        except Exception as e:
            print(f"Error indexing item {item.get('sku', 'unknown')}: {e}")
            return {"error": str(e)}

    def search_inventory(
        self,
        query: str,
        use_semantic: bool = True,
        size: int = 10
    ) -> Dict[str, Any]:
        """Search inventory items"""
        try:
            # Process query
            doc = self.nlp(query)
            tokens = [token.lemma_.lower() for token in doc 
                     if not token.is_stop and not token.is_punct]
            processed_query = ' '.join(tokens)
            
            # Build search query
            search_body = {
                "size": size,
                "query": {
                    "bool": {
                        "should": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": [
                                        "name^3",
                                        "description^2",
                                        "category",
                                        "manufacturer.name"
                                    ],
                                    "type": "best_fields",
                                    "fuzziness": "AUTO",
                                    "boost": 2.0
                                }
                            },
                            {
                                "match": {
                                    "tokens": {
                                        "query": processed_query,
                                        "boost": use_semantic and 1.5 or 0.5
                                    }
                                }
                            }
                        ],
                        "minimum_should_match": 1
                    }
                },
                "highlight": {
                    "fields": {
                        "name": {},
                        "description": {},
                        "tokens": {}
                    }
                }
            }
            
            # Execute search
            response = self.client.search(
                index=self.index_name,
                body=search_body,
                request_timeout=30
            )
            
            # Process results
            results = {
                "total": response["hits"]["total"]["value"],
                "items": []
            }
            
            for hit in response["hits"]["hits"]:
                item = hit["_source"]
                item["_score"] = hit["_score"]
                item["highlights"] = hit.get("highlight", {})
                results["items"].append(item)
            
            return results
            
        except Exception as e:
            print(f"Search error: {str(e)}")
            return {"error": str(e), "total": 0, "items": []}

# Sample test data
SAMPLE_INVENTORY = [
    {
        "sku": "LAP001",
        "name": "ThinkPad X1 Carbon",
        "description": "14-inch business laptop with Intel Core i7, 16GB RAM, 512GB SSD",
        "category": "Laptop",
        "manufacturer": {"name": "Lenovo"},
        "unit_price": 1499.99,
        "quantity": 25,
        "minimum_stock": 10
    },
    {
        "sku": "PHN001",
        "name": "iPhone 13 Pro",
        "description": "5G smartphone with A15 Bionic chip, 256GB storage",
        "category": "Smartphone",
        "manufacturer": {"name": "Apple"},
        "unit_price": 999.99,
        "quantity": 50,
        "minimum_stock": 20
    },
    {
        "sku": "LAP002",
        "name": "MacBook Pro 16",
        "description": "16-inch laptop with M1 Pro chip, 32GB RAM, 1TB SSD",
        "category": "Laptop",
        "manufacturer": {"name": "Apple"},
        "unit_price": 2499.99,
        "quantity": 15,
        "minimum_stock": 5
    }
]

def test_search_system():
    """Test the search system"""
    try:
        print("Initializing search system...")
        search_system = OptimizedInventorySearch(timeout=30)
        
        print("\nIndexing sample data...")
        for item in SAMPLE_INVENTORY:
            result = search_system.index_item(item)
            if "error" in result:
                print(f"Failed to index {item['sku']}: {result['error']}")
        
        # Wait for indexing to complete
        time.sleep(2)
        
        print("\nRunning test queries...")
        test_queries = [
            "ThinkPad laptop",
            "Apple high performance computer",
            "business laptop with good processor",
            "smartphone with large storage",
            "laptop with 16GB RAM"
        ]
        
        for query in test_queries:
            print(f"\nTesting query: {query}")
            
            # Test without semantic search
            print("Standard search:")
            results = search_system.search_inventory(query, use_semantic=False)
            if "error" in results:
                print(f"Error: {results['error']}")
            else:
                print(f"Found {results['total']} results:")
                for item in results['items']:
                    print(f"- {item['name']} (Score: {item.get('_score', 'N/A')})")
                    if 'highlights' in item:
                        print("  Matches:", item['highlights'])
            
            # Test with semantic search
            print("\nSemantic search:")
            results = search_system.search_inventory(query, use_semantic=True)
            if "error" in results:
                print(f"Error: {results['error']}")
            else:
                print(f"Found {results['total']} results:")
                for item in results['items']:
                    print(f"- {item['name']} (Score: {item.get('_score', 'N/A')})")
                    if 'highlights' in item:
                        print("  Matches:", item['highlights'])
                
    except Exception as e:
        print(f"Test failed: {str(e)}")
        raise

if __name__ == "__main__":
    test_search_system()