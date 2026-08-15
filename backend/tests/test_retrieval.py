import uuid
from backend.app.retrieval.vector_bm25 import retriever

def test_hybrid_retrieval_and_filtering():
    # 1. Seed some mock data in a test collection
    collection = "cases"
    uuid1 = str(uuid.uuid5(uuid.NAMESPACE_DNS, "c1"))
    uuid2 = str(uuid.uuid5(uuid.NAMESPACE_DNS, "c2"))
    uuid3 = str(uuid.uuid5(uuid.NAMESPACE_DNS, "c3"))
    
    chunks = [
        {
            "id": uuid1,
            "text": "Landlord must refund security deposit within 21 days according to California civil rules.",
            "metadata": {"doc_type": "case", "jurisdiction": "California", "filename": "case1.txt"}
        },
        {
            "id": uuid2,
            "text": "In New York, landlord security deposits are regulated under general obligations law.",
            "metadata": {"doc_type": "case", "jurisdiction": "New York", "filename": "case2.txt"}
        },
        {
            "id": uuid3,
            "text": "The contract clause outlines a 30-day timeline for return of security money.",
            "metadata": {"doc_type": "case", "jurisdiction": "California", "filename": "case3.txt"}
        }
    ]
    retriever.index_chunks(collection, chunks)
    
    # 2. Test semantic vector search
    vector_results = retriever.search_vector(collection, "security deposit", limit=3)
    assert len(vector_results) == 3

    # 3. Test metadata filtering
    filtered_results = retriever.search_vector(collection, "security deposit", limit=3, metadata_filter={"jurisdiction": "New York"})
    assert len(filtered_results) == 1
    assert filtered_results[0]["metadata"]["jurisdiction"] == "New York"
    assert "New York" in filtered_results[0]["text"]

    # 4. Test BM25 keyword search
    bm25_results = retriever.search_bm25(collection, "New York", limit=1)
    assert len(bm25_results) == 1
    assert "New York" in bm25_results[0]["text"]

    # 5. Test hybrid search (RRF)
    hybrid_results = retriever.search_hybrid(collection, "California rules", limit=2)
    assert len(hybrid_results) == 2
    assert hybrid_results[0]["retrieval_method"] == "hybrid"
