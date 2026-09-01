import chromadb
client = chromadb.PersistentClient(path="data/chroma")
collections = client.list_collections()
for c in collections:
    print(c.name)
