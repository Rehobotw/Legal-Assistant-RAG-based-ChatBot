from app.services.rag.retriever import retrieve_cases
import app.services.rag.retriever as retriever


class FakeStore:
    def similarity_search_with_relevance_scores(self, _query, k):
        assert k == 6
        return [
            (FakeDocument("matching chunk", {"case_number": "130665", "chunk_index": 1}), 0.92),
            (FakeDocument("duplicate", {"case_number": "130665", "chunk_index": 2}), 0.80),
            (FakeDocument("other match", {"case_number": "119446", "chunk_index": 0}), 0.75),
        ]

    def get(self, *, where, include):
        assert include == ["documents", "metadatas"]
        documents = {
            "130665": ["later case text", "opening case text"],
            "119446": ["whole other case"],
        }[where["case_number"]]
        metadata = {
            "130665": [{"chunk_index": 1}, {"chunk_index": 0}],
            "119446": [{"chunk_index": 0}],
        }[where["case_number"]]
        return {"documents": documents, "metadatas": metadata}


class FakeDocument:
    def __init__(self, page_content, metadata):
        self.page_content = page_content
        self.metadata = metadata


def test_retrieval_deduplicates_cases_and_reconstructs_source_record(monkeypatch) -> None:
    monkeypatch.setattr(retriever, "get_ready_vector_store", FakeStore)

    cases = retrieve_cases("termination", limit=2)

    assert [case.metadata["case_number"] for case in cases] == ["130665", "119446"]
    assert cases[0].content == "opening case text\n\nlater case text"
    assert cases[0].score == 0.92
