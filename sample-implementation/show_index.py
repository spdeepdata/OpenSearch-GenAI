from opensearchpy import OpenSearch
import json

# Initialize the client
client = OpenSearch(
    hosts=[{'host': 'localhost', 'port': 9200}],
    use_ssl=False,
    verify_certs=False,
    ssl_show_warn=False,
    scheme="http"
)

# Get all documents in the inventory index
search_query = {
    "query": {
        "match_all": {}
    },
    "size": 100
}

response = client.search(
    body=search_query,
    index='inventory'
)

print("All Documents in Index:")
print(json.dumps(response['hits']['hits'], indent=2))

# Check the mapping of the index
mapping = client.indices.get_mapping(index='inventory')
print("\nIndex Mapping:")
print(json.dumps(mapping, indent=2))