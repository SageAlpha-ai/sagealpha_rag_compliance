"""
LangChain Orchestration Layer with Manual Hybrid Retrieval (BM25 + Chroma)

Replaces manual routing logic with LangChain-based orchestration.
Automatically decides between LLM-only, RAG-only, and RAG+LLM synthesis.
Uses manual hybrid retrieval (BM25 + Chroma) for improved accuracy.

Uses LangChain v1 LCEL (LangChain Expression Language) pattern.
"""

import logging
import os
import re
from typing import Dict, Any, List, Optional, Tuple

from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from rank_bm25 import BM25Okapi

from config.settings import get_config
from vectorstore.chroma_client import get_collection

logger = logging.getLogger(__name__)

# Optional LangSmith tracing (disabled by default)
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "rag-service")

if LANGCHAIN_TRACING_V2 and LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT
    logger.info("LangSmith tracing enabled")


def _load_all_documents_from_chroma(collection) -> Tuple[List[str], List[Dict]]:
    """
    Load all documents from Chroma collection for BM25 indexing.
    
    Returns:
        Tuple of (document_texts, metadatas)
    """
    try:
        # Get all documents from Chroma (using get() with no filters)
        all_data = collection.get(include=["documents", "metadatas"])
        
        documents = all_data.get("documents", [])
        metadatas = all_data.get("metadatas", [])
        
        logger.info(f"Loaded {len(documents)} documents from Chroma for BM25 indexing")
        return documents, metadatas
    except Exception as e:
        logger.error(f"Failed to load documents from Chroma: {e}")
        return [], []


def _detect_numeric_intent(query: str) -> bool:
    """
    Detect if query has numeric/exact intent.
    
    Returns True if query contains numeric indicators:
    digits, %, $, total, value, rate, exact, amount, revenue, number, count
    """
    query_lower = query.lower()
    
    numeric_patterns = [
        r'\d+',  # digits
        r'%',  # percentage
        r'\$',  # currency
        r'\btotal\b',
        r'\bexact\b',
        r'\brate\b',
        r'\bvalue\b',
        r'\brevenue\b',
        r'\bamount\b',
        r'\bnumber\b',
        r'\bcount\b'
    ]
    
    numeric_score = sum(1 for pattern in numeric_patterns if re.search(pattern, query_lower, re.IGNORECASE))
    return numeric_score >= 2


class BM25Index:
    """BM25 index using rank-bm25 library."""
    
    def __init__(self, documents: List[str], metadatas: List[Dict]):
        """
        Initialize BM25 index from documents.
        
        Args:
            documents: List of document text chunks
            metadatas: List of metadata dicts (one per document)
        """
        if not documents:
            self.index = None
            self.documents = []
            self.metadatas = []
            return
        
        # Tokenize documents for BM25
        tokenized_docs = [doc.lower().split() for doc in documents]
        self.index = BM25Okapi(tokenized_docs)
        self.documents = documents
        self.metadatas = metadatas
    
    def search(self, query: str, top_k: int = 5) -> Tuple[List[str], List[Dict]]:
        """
        Search BM25 index for query.
        
        Returns:
            Tuple of (documents, metadatas) sorted by relevance
        """
        if self.index is None or not self.documents:
            return [], []
        
        # Tokenize query
        tokenized_query = query.lower().split()
        
        # Get BM25 scores
        scores = self.index.get_scores(tokenized_query)
        
        # Get top-k indices
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        
        # Return documents and metadatas
        results_docs = [self.documents[i] for i in top_indices]
        results_metas = [self.metadatas[i] for i in top_indices]
        
        return results_docs, results_metas


def _deduplicate_documents(doc_list_1: List[str], meta_list_1: List[Dict],
                           doc_list_2: List[str], meta_list_2: List[Dict]) -> Tuple[List[str], List[Dict]]:
    """
    Merge and deduplicate documents from two retrieval sources.
    
    Deduplicates by exact text content.
    Preserves order: doc_list_1 first, then doc_list_2 (no duplicates).
    """
    seen_texts = set()
    merged_docs = []
    merged_metas = []
    
    # Add documents from first list
    for doc, meta in zip(doc_list_1, meta_list_1):
        doc_normalized = doc.strip().lower()
        if doc_normalized not in seen_texts:
            seen_texts.add(doc_normalized)
            merged_docs.append(doc)
            merged_metas.append(meta)
    
    # Add documents from second list (if not duplicate)
    for doc, meta in zip(doc_list_2, meta_list_2):
        doc_normalized = doc.strip().lower()
        if doc_normalized not in seen_texts:
            seen_texts.add(doc_normalized)
            merged_docs.append(doc)
            merged_metas.append(meta)
    
    return merged_docs, merged_metas


class LangChainOrchestrator:
    """
    LangChain-based orchestration for RAG + LLM routing with manual hybrid retrieval.
    
    Uses LangChain v1 LCEL pattern (prompt | llm | parser).
    Automatically decides: LLM-only, RAG-only, or RAG+LLM synthesis.
    Uses manual hybrid retrieval (BM25 + Chroma) for improved accuracy.
    """
    
    def __init__(self):
        """Initialize LangChain components."""
        config = get_config()
        
        # Azure OpenAI LLM (for chat/completion)
        self.llm = AzureChatOpenAI(
            azure_endpoint=config.azure_openai.endpoint,
            azure_deployment=config.azure_openai.chat_deployment,
            api_key=config.azure_openai.api_key,
            api_version=config.azure_openai.api_version,
            temperature=0.0,  # Deterministic for finance
        )
        
        # Output parser for LCEL chains
        self.output_parser = StrOutputParser()
        
        # Get Chroma collection (reuses existing connection)
        self.collection = get_collection(create_if_missing=False)
        
        # Initialize hybrid retrieval (BM25 + Chroma)
        self._setup_retrievers()
        
        # Setup prompts and chains
        self._setup_chains()
    
    def _setup_retrievers(self):
        """Setup BM25 index from Chroma documents."""
        try:
            # Load all documents from Chroma for BM25 indexing
            logger.info("Loading documents from Chroma for BM25 indexing...")
            all_documents, all_metadatas = _load_all_documents_from_chroma(self.collection)
            
            if not all_documents:
                logger.warning("No documents loaded from Chroma. BM25 will be disabled.")
                self.bm25_index = None
                return
            
            # Create BM25 index
            logger.info(f"Initializing BM25 index with {len(all_documents)} documents...")
            self.bm25_index = BM25Index(all_documents, all_metadatas)
            
            logger.info("BM25 index initialized successfully")
        except Exception as e:
            logger.error(f"Failed to setup BM25 index: {e}", exc_info=True)
            self.bm25_index = None
    
    def _setup_chains(self):
        """Setup LangChain prompts and LCEL chains."""
        
        # Router prompt: LLM decides which strategy to use
        self.router_template = """You are an expert financial AI assistant router.

Given a user question, decide which response strategy to use:

1. LLM_ONLY: Use for general knowledge questions, conversational queries, or questions that don't require specific document data.
2. RAG_ONLY: Use for questions asking for specific facts, numbers, financial data, or information that should be in documents.
3. RAG_LLM: Use for questions that need both document facts AND analysis/reasoning.

Question: {question}

Provide ONLY the strategy name (LLM_ONLY, RAG_ONLY, or RAG_LLM):"""
        
        self.router_prompt = ChatPromptTemplate.from_template(self.router_template)
        self.router_chain = self.router_prompt | self.llm | self.output_parser
        
        # Document relevance grader
        self.grader_template = """You are a document relevance grader for financial queries.

Given a user question and retrieved documents, grade if the documents are relevant.

Question: {question}
Documents: {documents}

If documents contain specific financial data, numbers, or facts related to the question, grade as RELEVANT.
If documents are generic, unrelated, or don't contain answer facts, grade as IRRELEVANT.

Provide ONLY the grade (RELEVANT or IRRELEVANT):"""
        
        self.grader_prompt = ChatPromptTemplate.from_template(self.grader_template)
        self.grader_chain = self.grader_prompt | self.llm | self.output_parser
        
        # RAG prompt (document-based answers only) - STRICT about exact numbers
        self.rag_template = """You are a financial AI assistant. Answer the question using ONLY the provided context documents.

Context documents:
{context}

Question: {question}

STRICT INSTRUCTIONS:
- Answer using ONLY information from the context documents
- Include specific numbers, dates, and facts EXACTLY as they appear in the context
- Preserve exact numeric values (integers, floats, percentages, currency)
- If an exact number is not found in the context, say: "The exact value is not available in the documents."
- NEVER estimate, approximate, or hallucinate numbers
- NEVER answer without retrieved context
- Cite sources when referencing specific data

Answer:"""
        
        self.rag_prompt = ChatPromptTemplate.from_template(self.rag_template)
        self.rag_chain = self.rag_prompt | self.llm | self.output_parser
        
        # RAG+LLM synthesis prompt (documents + reasoning) - STRICT about exact numbers
        self.synthesis_template = """You are a financial AI assistant. Answer the question using the provided context documents AND your knowledge.

Context documents:
{context}

Question: {question}

STRICT INSTRUCTIONS:
- Use information from context documents as the primary source
- Include specific numbers and facts EXACTLY as they appear in the context
- Preserve exact numeric values (integers, floats, percentages, currency)
- If an exact number is not found in the context, say: "The exact value is not available in the documents."
- NEVER estimate or hallucinate numbers from context
- Supplement with your knowledge only for general explanations (not numbers)
- Provide analysis and reasoning when requested
- Cite sources when referencing document data

Answer:"""
        
        self.synthesis_prompt = ChatPromptTemplate.from_template(self.synthesis_template)
        self.synthesis_chain = self.synthesis_prompt | self.llm | self.output_parser
        
        # LLM-only prompt (general knowledge)
        self.llm_only_template = """You are a financial AI assistant. Answer the question using your knowledge.

Question: {question}

Answer the question helpfully and accurately. For financial queries, be precise with numbers and dates when you have that information.

Answer:"""
        
        self.llm_only_prompt = ChatPromptTemplate.from_template(self.llm_only_template)
        self.llm_only_chain = self.llm_only_prompt | self.llm | self.output_parser
    
    def _route_query(self, question: str) -> str:
        """
        Route query using LangChain router (LLM-based decision).
        Returns: "LLM_ONLY", "RAG_ONLY", or "RAG_LLM"
        """
        try:
            result = self.router_chain.invoke({"question": question})
            
            # Parse result
            result_upper = result.strip().upper()
            if "RAG_LLM" in result_upper or "RAG+LLM" in result_upper:
                return "RAG_LLM"
            elif "RAG_ONLY" in result_upper or "RAG" in result_upper:
                return "RAG_ONLY"
            else:
                return "LLM_ONLY"
        except Exception as e:
            logger.error(f"Routing failed: {e}, defaulting to RAG_ONLY")
            return "RAG_ONLY"
    
    def _grade_documents(self, question: str, documents: List[str]) -> bool:
        """
        Grade document relevance using LLM grader.
        Returns True if documents are relevant, False otherwise.
        """
        try:
            docs_text = "\n\n".join(documents[:5])  # Grade top 5
            result = self.grader_chain.invoke({
                "question": question,
                "documents": docs_text[:2000]  # Limit for grader
            })
            is_relevant = "RELEVANT" in result.upper()
            logger.info(f"Document grader: {result.strip()} (relevant={is_relevant})")
            return is_relevant
        except Exception as e:
            logger.error(f"Document grading failed: {e}")
            return True  # Default to relevant if grading fails
    
    def _retrieve_documents_hybrid(self, question: str) -> Tuple[List[str], List[Dict]]:
        """
        Retrieve documents using manual hybrid retrieval (BM25 + Chroma).
        Returns: (documents, metadatas)
        """
        try:
            # Always query Chroma for semantic relevance
            chroma_results = self.collection.query(
                query_texts=[question],
                n_results=5,
                include=["documents", "metadatas"]
            )
            
            chroma_docs = chroma_results.get("documents", [[]])[0] if chroma_results.get("documents") else []
            chroma_metas = chroma_results.get("metadatas", [[]])[0] if chroma_results.get("metadatas") else []
            
            # If numeric intent detected and BM25 is available, also query BM25
            bm25_docs = []
            bm25_metas = []
            if _detect_numeric_intent(question) and self.bm25_index is not None:
                bm25_docs, bm25_metas = self.bm25_index.search(question, top_k=5)
                logger.info(f"BM25 retrieval returned {len(bm25_docs)} documents")
            
            # Merge and deduplicate results
            merged_docs, merged_metas = _deduplicate_documents(
                chroma_docs, chroma_metas,
                bm25_docs, bm25_metas
            )
            
            logger.info(f"Hybrid retrieval returned {len(merged_docs)} unique documents")
            return merged_docs, merged_metas
        except Exception as e:
            logger.error(f"Hybrid document retrieval failed: {e}")
            return [], []
    
    def _rag_only_chain(self, question: str) -> tuple[str, List[str]]:
        """
        RAG-only chain: answers from documents only.
        Uses manual hybrid retrieval (BM25 + Chroma).
        Returns: (answer, sources)
        """
        documents, metadatas = self._retrieve_documents_hybrid(question)
        
        if not documents:
            # STRICT: Never answer without context
            logger.warning("No documents retrieved - cannot answer without context")
            return "The exact value is not available in the documents.", []
        
        # Grade documents for relevance
        if not self._grade_documents(question, documents):
            # STRICT: Never answer without relevant context
            logger.info("Documents not relevant - cannot answer without context")
            return "The exact value is not available in the documents.", []
        
        # Build context from documents
        context_parts = []
        for doc, meta in zip(documents, metadatas):
            meta_info = ""
            if meta.get("source"):
                meta_info = f"Source: {meta.get('source')}"
            if meta.get("fiscal_year"):
                meta_info += f", FY: {meta.get('fiscal_year')}"
            if meta_info:
                context_parts.append(f"[{meta_info}]\n{doc}")
            else:
                context_parts.append(doc)
        
        context = "\n\n---\n\n".join(context_parts)
        
        # Generate answer using RAG chain (LCEL)
        answer = self.rag_chain.invoke({"question": question, "context": context})
        
        # Extract sources
        sources = [
            meta.get("source", meta.get("filename", "unknown"))
            for meta in metadatas
        ]
        
        return answer, sources
    
    def _rag_llm_chain(self, question: str) -> tuple[str, List[str]]:
        """
        RAG+LLM synthesis chain: combines documents with LLM reasoning.
        Uses manual hybrid retrieval (BM25 + Chroma).
        Returns: (answer, sources)
        """
        documents, metadatas = self._retrieve_documents_hybrid(question)
        
        if not documents:
            # STRICT: Never answer without context
            logger.warning("No documents retrieved - cannot answer without context")
            return "The exact value is not available in the documents.", []
        
        # Build context from documents
        context_parts = []
        for doc, meta in zip(documents, metadatas):
            meta_info = ""
            if meta.get("source"):
                meta_info = f"Source: {meta.get('source')}"
            if meta.get("fiscal_year"):
                meta_info += f", FY: {meta.get('fiscal_year')}"
            if meta_info:
                context_parts.append(f"[{meta_info}]\n{doc}")
            else:
                context_parts.append(doc)
        
        context = "\n\n---\n\n".join(context_parts)
        
        # Generate answer using synthesis chain (LCEL)
        answer = self.synthesis_chain.invoke({"question": question, "context": context})
        
        # Extract sources
        sources = [
            meta.get("source", meta.get("filename", "unknown"))
            for meta in metadatas
        ]
        
        return answer, sources
    
    def _llm_only_chain(self, question: str) -> str:
        """
        LLM-only chain: answers from LLM knowledge only.
        Returns: answer
        """
        answer = self.llm_only_chain.invoke({"question": question})
        return answer
    
    def answer_query(self, question: str) -> Dict[str, Any]:
        """
        Main orchestration method.
        
        Uses LangChain routing to decide between LLM-only, RAG-only, or RAG+LLM.
        Uses manual hybrid retrieval (BM25 + Chroma) for RAG queries.
        Returns response in format compatible with existing API.
        """
        try:
            # Route query using LangChain router
            route = self._route_query(question)
            logger.info(f"LangChain router decision: {route}")
            
            # Execute based on route
            if route == "RAG_ONLY":
                answer, sources = self._rag_only_chain(question)
                answer_type = "RAG"
            elif route == "RAG_LLM":
                answer, sources = self._rag_llm_chain(question)
                answer_type = "RAG+LLM"
            else:  # LLM_ONLY
                answer = self._llm_only_chain(question)
                answer_type = "LLM"
                sources = None
            
            return {
                "answer": answer,
                "answer_type": answer_type,
                "sources": sources
            }
        except Exception as e:
            logger.error(f"LangChain orchestration failed: {e}", exc_info=True)
            # Fallback: return error message (no GPT-only fallback per requirements)
            return {
                "answer": "I apologize, but I encountered an error while processing your query. Please try again.",
                "answer_type": "LLM",
                "sources": None
            }


# Singleton instance
_orchestrator: Optional[LangChainOrchestrator] = None


def get_orchestrator() -> LangChainOrchestrator:
    """Get singleton orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = LangChainOrchestrator()
    return _orchestrator


def answer_query_simple(question: str) -> Dict[str, Any]:
    """
    Simplified interface for API.
    Uses LangChain orchestration with manual hybrid retrieval (BM25 + Chroma).
    
    This replaces the manual routing logic in rag/query_engine.py
    with LangChain-based decision making (LCEL pattern) and manual hybrid retrieval.
    """
    orchestrator = get_orchestrator()
    return orchestrator.answer_query(question)
