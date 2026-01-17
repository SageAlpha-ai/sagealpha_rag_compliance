"""
LangChain Orchestration Layer - OpenAI-Style Answerability Validation

Follows OpenAI's approach:
1. ALWAYS retrieves documents first
2. Validates answerability (entity, year, metric matching)
3. Only generates RAG answer if documents are answerable
4. Returns RAG_NO_ANSWER if data doesn't match requirements
5. Falls back to LLM only when retrieval fails completely

Uses LangChain v1 LCEL (LangChain Expression Language) pattern.
"""

import logging
import os
import re
from typing import Dict, Any, List, Optional, Tuple

from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
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
    """Load all documents from Chroma collection for BM25 indexing."""
    try:
        all_data = collection.get(include=["documents", "metadatas"])
        documents = all_data.get("documents", [])
        metadatas = all_data.get("metadatas", [])
        logger.info(f"Loaded {len(documents)} documents from Chroma for BM25 indexing")
        return documents, metadatas
    except Exception as e:
        logger.error(f"Failed to load documents from Chroma: {e}")
        return [], []


def _extract_fiscal_year(query: str) -> Optional[str]:
    """Extracts fiscal year from query. Returns normalized FYxxxx format."""
    patterns = [
        r'FY\s*(\d{4})',
        r'fiscal\s+year\s+(\d{4})',
        r'\b(20\d{2})\b',
        r'\b(19\d{2})\b',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            year = match.group(1)
            return f"FY{year}"
    
    return None


def _extract_entity_from_query(query: str) -> Optional[str]:
    """Extracts company/entity from query."""
    query_lower = query.lower()
    
    entity_mappings = {
        "oracle financial services": "Oracle Financial Services Software Ltd",
        "oracle financial": "Oracle Financial Services Software Ltd",
        "ofss": "Oracle Financial Services Software Ltd",
    }
    
    for key, value in entity_mappings.items():
        if key in query_lower:
            return value
    
    return None


def _extract_metrics_from_query(query: str) -> List[str]:
    """Extracts requested financial metrics from query."""
    metrics = []
    query_lower = query.lower()
    
    metric_mapping = {
        'revenue': ['revenue', 'sales', 'turnover'],
        'net_income': ['net income', 'net profit', 'profit', 'earnings', 'pat'],
        'ebitda': ['ebitda'],
        'gross_profit': ['gross profit'],
        'operating_income': ['operating income', 'operating profit', 'ebit'],
        'assets': ['assets', 'total assets'],
        'equity': ['equity', 'total equity'],
    }
    
    for metric_key, keywords in metric_mapping.items():
        if any(kw in query_lower for kw in keywords):
            metrics.append(metric_key)
    
    return metrics


def _validate_answerability(
    query: str,
    documents: List[str],
    metadatas: List[Dict]
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    OpenAI-style answerability validation.
    
    Validates if retrieved documents can answer the query by checking:
    1. Entity match (if entity specified in query)
    2. Fiscal year match (if year specified in query)
    3. Metric match (if metric specified in query)
    
    Returns:
        (is_answerable, reason, validation_details)
    """
    if not documents:
        return False, "No documents retrieved", {}
    
    requested_year = _extract_fiscal_year(query)
    requested_entity = _extract_entity_from_query(query)
    requested_metrics = _extract_metrics_from_query(query)
    
    validation_details = {
        "requested_year": requested_year,
        "requested_entity": requested_entity,
        "requested_metrics": requested_metrics,
        "entity_matches": 0,
        "year_matches": 0,
        "metric_matches": 0,
        "strong_matches": 0
    }
    
    # Check each document for matches
    for doc, meta in zip(documents, metadatas):
        doc_lower = doc.lower()
        doc_year = meta.get("fiscal_year", "")
        doc_entity = meta.get("company", "")
        
        # Entity match
        entity_match = False
        if requested_entity:
            if doc_entity and requested_entity.lower() in doc_entity.lower():
                validation_details["entity_matches"] += 1
                entity_match = True
        else:
            # No entity specified, consider it a match
            entity_match = True
        
        # Year match (CRITICAL for financial queries)
        year_match = False
        if requested_year:
            if doc_year and requested_year.lower() == doc_year.lower():
                validation_details["year_matches"] += 1
                year_match = True
        else:
            # No year specified, consider it a match
            year_match = True
        
        # Metric match
        metric_match = False
        if requested_metrics:
            for metric in requested_metrics:
                if metric == "revenue" and "revenue" in doc_lower:
                    validation_details["metric_matches"] += 1
                    metric_match = True
                    break
                elif metric == "net_income" and ("net income" in doc_lower or "net profit" in doc_lower):
                    validation_details["metric_matches"] += 1
                    metric_match = True
                    break
                elif metric in doc_lower:
                    validation_details["metric_matches"] += 1
                    metric_match = True
                    break
        else:
            # No specific metric, consider it a match
            metric_match = True
        
        # Strong match = all requirements met
        if entity_match and year_match and metric_match:
            validation_details["strong_matches"] += 1
    
    # Determine answerability
    is_answerable = False
    reason = ""
    
    if requested_year and validation_details["year_matches"] == 0:
        is_answerable = False
        reason = f"Query requires FY{requested_year[2:]} data, but retrieved documents contain different fiscal years"
    elif requested_entity and validation_details["entity_matches"] == 0:
        is_answerable = False
        reason = f"Query requires {requested_entity} data, but retrieved documents are for different entities"
    elif requested_metrics and validation_details["metric_matches"] == 0:
        is_answerable = False
        reason = f"Query requires {', '.join(requested_metrics)} data, but retrieved documents don't contain this metric"
    elif validation_details["strong_matches"] > 0:
        is_answerable = True
        reason = f"Found {validation_details['strong_matches']} document(s) matching all requirements"
    elif not requested_year and not requested_entity and not requested_metrics:
        # General query, no specific requirements
        is_answerable = True
        reason = "General query with no specific requirements - documents are relevant"
    else:
        is_answerable = False
        reason = "Retrieved documents don't match query requirements"
    
    logger.info(f"[VALIDATE] Answerability check: {is_answerable}")
    logger.info(f"[VALIDATE] Reason: {reason}")
    logger.info(f"[VALIDATE] Details: entity_matches={validation_details['entity_matches']}, "
                f"year_matches={validation_details['year_matches']}, "
                f"metric_matches={validation_details['metric_matches']}, "
                f"strong_matches={validation_details['strong_matches']}")
    
    return is_answerable, reason, validation_details


def _detect_numeric_intent(query: str) -> bool:
    """Detect if query has numeric/exact intent."""
    query_lower = query.lower()
    numeric_patterns = [
        r'\d+', r'%', r'\$', r'\btotal\b', r'\bexact\b', r'\brate\b',
        r'\bvalue\b', r'\brevenue\b', r'\bamount\b', r'\bnumber\b', r'\bcount\b'
    ]
    numeric_score = sum(1 for pattern in numeric_patterns if re.search(pattern, query_lower, re.IGNORECASE))
    return numeric_score >= 2


class BM25Index:
    """BM25 index using rank-bm25 library."""
    
    def __init__(self, documents: List[str], metadatas: List[Dict]):
        if not documents:
            self.index = None
            self.documents = []
            self.metadatas = []
            return
        
        tokenized_docs = [doc.lower().split() for doc in documents]
        self.index = BM25Okapi(tokenized_docs)
        self.documents = documents
        self.metadatas = metadatas
    
    def search(self, query: str, top_k: int = 5) -> Tuple[List[str], List[Dict]]:
        if self.index is None or not self.documents:
            return [], []
        
        tokenized_query = query.lower().split()
        scores = self.index.get_scores(tokenized_query)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        
        results_docs = [self.documents[i] for i in top_indices]
        results_metas = [self.metadatas[i] for i in top_indices]
        
        return results_docs, results_metas


def _deduplicate_documents(doc_list_1: List[str], meta_list_1: List[Dict],
                           doc_list_2: List[str], meta_list_2: List[Dict]) -> Tuple[List[str], List[Dict]]:
    """Merge and deduplicate documents from two retrieval sources."""
    seen_texts = set()
    merged_docs = []
    merged_metas = []
    
    for doc, meta in zip(doc_list_1, meta_list_1):
        doc_normalized = doc.strip().lower()
        if doc_normalized not in seen_texts:
            seen_texts.add(doc_normalized)
            merged_docs.append(doc)
            merged_metas.append(meta)
    
    for doc, meta in zip(doc_list_2, meta_list_2):
        doc_normalized = doc.strip().lower()
        if doc_normalized not in seen_texts:
            seen_texts.add(doc_normalized)
            merged_docs.append(doc)
            merged_metas.append(meta)
    
    return merged_docs, merged_metas


class LangChainOrchestrator:
    """
    LangChain-based orchestration with OpenAI-style answerability validation.
    
    Flow:
    1. ALWAYS retrieve documents first
    2. Validate answerability (entity, year, metric matching)
    3. If answerable → RAG generation
    4. If not answerable → RAG_NO_ANSWER (no LLM generation)
    5. If retrieval fails → LLM fallback
    """
    
    def __init__(self):
        """Initialize LangChain components and verify ChromaDB is not empty."""
        config = get_config()
        
        # Azure OpenAI LLM
        self.llm = AzureChatOpenAI(
            azure_endpoint=config.azure_openai.endpoint,
            azure_deployment=config.azure_openai.chat_deployment,
            api_key=config.azure_openai.api_key,
            api_version=config.azure_openai.api_version,
            temperature=0.0,
        )
        
        # Azure OpenAI Embeddings (MUST match ingestion model)
        # For text-embedding-3-large, don't pass model parameter (deployment name is sufficient)
        embedding_kwargs = {
            "azure_endpoint": config.azure_openai.endpoint,
            "azure_deployment": config.azure_openai.embeddings_deployment,
            "api_key": config.azure_openai.api_key,
            "api_version": config.azure_openai.api_version,
        }
        
        # Only add model parameter for older models if needed
        if "text-embedding-ada-002" in config.azure_openai.embeddings_deployment.lower():
            embedding_kwargs["model"] = "text-embedding-ada-002"
        
        self.embeddings = AzureOpenAIEmbeddings(**embedding_kwargs)
        
        self.output_parser = StrOutputParser()
        
        # Get Chroma collection
        self.collection = get_collection(create_if_missing=False)
        
        # VERIFY ChromaDB is not empty (FAIL LOUDLY if empty)
        doc_count = self.collection.count()
        logger.info("=" * 60)
        logger.info("CHROMADB COLLECTION STATUS")
        logger.info("=" * 60)
        logger.info(f"Collection name: {self.collection.name}")
        logger.info(f"Total embeddings: {doc_count}")
        
        if doc_count == 0:
            error_msg = (
                "FATAL ERROR: ChromaDB collection is EMPTY. "
                "No documents have been ingested. "
                "Please run: python ingest.py --fresh"
            )
            logger.error("=" * 60)
            logger.error(error_msg)
            logger.error("=" * 60)
            raise RuntimeError(error_msg)
        
        logger.info("=" * 60)
        
        # Initialize hybrid retrieval
        self._setup_retrievers()
        
        # Setup prompts and chains
        self._setup_chains()
    
    def _setup_retrievers(self):
        """Setup BM25 index from Chroma documents."""
        try:
            logger.info("Loading documents from Chroma for BM25 indexing...")
            all_documents, all_metadatas = _load_all_documents_from_chroma(self.collection)
            
            if not all_documents:
                logger.warning("No documents loaded from Chroma. BM25 will be disabled.")
                self.bm25_index = None
                return
            
            logger.info(f"Initializing BM25 index with {len(all_documents)} documents...")
            self.bm25_index = BM25Index(all_documents, all_metadatas)
            logger.info("BM25 index initialized successfully")
        except Exception as e:
            logger.error(f"Failed to setup BM25 index: {e}", exc_info=True)
            self.bm25_index = None
    
    def _setup_chains(self):
        """Setup LangChain prompts and LCEL chains."""
        
        # RAG prompt (strict document-based answers)
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
- Cite sources when referencing specific data

Answer:"""
        
        self.rag_prompt = ChatPromptTemplate.from_template(self.rag_template)
        self.rag_chain = self.rag_prompt | self.llm | self.output_parser
        
        # LLM-only prompt (general knowledge)
        self.llm_only_template = """You are a financial AI assistant. Answer the question using your knowledge.

Question: {question}

Answer the question helpfully and accurately. For financial queries, be precise with numbers and dates when you have that information.

Answer:"""
        
        self.llm_only_prompt = ChatPromptTemplate.from_template(self.llm_only_template)
        self.llm_only_chain = self.llm_only_prompt | self.llm | self.output_parser
    
    def _retrieve_documents_hybrid(self, question: str) -> Tuple[List[str], List[Dict]]:
        """
        STRICT retrieval: ALWAYS attempts to retrieve documents from ChromaDB.
        
        Uses SAME embedding model as ingestion (must match deployment name).
        Supports fiscal year filtering when query specifies a year.
        """
        try:
            config = get_config()
            logger.info("[RETRIEVER] Embedding query using Azure OpenAI")
            logger.info(f"[RETRIEVER] Embedding model: {config.azure_openai.embeddings_deployment}")
            
            # Extract fiscal year from query
            requested_year = _extract_fiscal_year(question)
            if requested_year:
                logger.info(f"[RETRIEVER] Detected fiscal year in query: {requested_year}")
            
            # Generate embeddings using SAME model as ingestion
            query_embedding = self.embeddings.embed_query(question)
            logger.info(f"[RETRIEVER] Query embedding generated (dimension: {len(query_embedding)})")
            
            logger.info("[RETRIEVER] Searching ChromaDB using cosine similarity")
            
            # If fiscal year specified, try year-filtered retrieval first
            year_docs = []
            year_metas = []
            if requested_year:
                try:
                    logger.info(f"[RETRIEVER] Attempting year-filtered retrieval for {requested_year}")
                    year_results = self.collection.query(
                        query_embeddings=[query_embedding],
                        n_results=5,
                        where={"fiscal_year": requested_year},
                        include=["documents", "metadatas", "distances"]
                    )
                    year_docs = year_results.get("documents", [[]])[0] if year_results.get("documents") else []
                    year_metas = year_results.get("metadatas", [[]])[0] if year_results.get("metadatas") else []
                    logger.info(f"[RETRIEVER] Year-filtered retrieval found {len(year_docs)} documents for {requested_year}")
                except Exception as e:
                    logger.warning(f"[RETRIEVER] Year-filtered retrieval failed: {e}, falling back to general retrieval")
            
            # Always perform general retrieval
            chroma_results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=5,
                include=["documents", "metadatas", "distances"]
            )
            
            chroma_docs = chroma_results.get("documents", [[]])[0] if chroma_results.get("documents") else []
            chroma_metas = chroma_results.get("metadatas", [[]])[0] if chroma_results.get("metadatas") else []
            chroma_distances = chroma_results.get("distances", [[]])[0] if chroma_results.get("distances") else []
            
            if chroma_distances:
                logger.info(f"[RETRIEVER] ChromaDB similarity scores: {chroma_distances[:3]}")
            
            logger.info(f"[RETRIEVER] General ChromaDB retrieval found {len(chroma_docs)} documents")
            
            # Combine results: year-specific first, then general (deduplicated)
            if year_docs:
                seen_texts = {doc.strip().lower() for doc in year_docs}
                additional_docs = []
                additional_metas = []
                for doc, meta in zip(chroma_docs, chroma_metas):
                    if doc.strip().lower() not in seen_texts:
                        additional_docs.append(doc)
                        additional_metas.append(meta)
                
                chroma_docs = year_docs + additional_docs[:3]
                chroma_metas = year_metas + additional_metas[:3]
                logger.info(f"[RETRIEVER] Combined retrieval: {len(year_docs)} year-specific + {len(additional_docs[:3])} general = {len(chroma_docs)} total")
            
            # BM25 retrieval if numeric intent detected
            bm25_docs = []
            bm25_metas = []
            if _detect_numeric_intent(question) and self.bm25_index is not None:
                bm25_docs, bm25_metas = self.bm25_index.search(question, top_k=5)
                logger.info(f"[RETRIEVER] BM25 retrieved {len(bm25_docs)} documents")
            
            # Merge and deduplicate results
            merged_docs, merged_metas = _deduplicate_documents(
                chroma_docs, chroma_metas,
                bm25_docs, bm25_metas
            )
            
            logger.info(f"[RETRIEVER] Total documents retrieved: {len(merged_docs)}")
            
            # Log first document preview if available
            if merged_docs:
                first_doc_preview = merged_docs[0][:500]
                logger.info(f"[RETRIEVER] First document preview: {first_doc_preview}...")
            
            return merged_docs, merged_metas
        except Exception as e:
            logger.error(f"[RETRIEVER] Hybrid document retrieval failed: {e}", exc_info=True)
            return [], []
    
    def answer_query(self, question: str) -> Dict[str, Any]:
        """
        OpenAI-style orchestration with answerability validation.
        
        Flow:
        1. ALWAYS retrieve documents first
        2. Validate answerability (entity, year, metric matching)
        3. If answerable → RAG generation
        4. If not answerable → RAG_NO_ANSWER (no LLM generation)
        5. If retrieval fails → LLM fallback
        """
        try:
            logger.info("[QUERY] Processing query")
            logger.info(f"[QUERY] Query text: {question}")
            
            # STEP 1: ALWAYS perform retrieval first (NO EXCEPTIONS)
            logger.info("[RETRIEVER] Starting retrieval...")
            documents, metadatas = self._retrieve_documents_hybrid(question)
            
            logger.info(f"[DEBUG] Retrieved docs count: {len(documents)}")
            
            # STEP 2: Check if retrieval succeeded
            if not documents:
                # No documents retrieved → LLM fallback
                logger.warning("[ROUTER] No documents retrieved → LLM fallback")
                logger.info("[RAG] Sending query to LLM (no context)")
                answer = self.llm_only_chain.invoke({"question": question})
                logger.info("[RAG] Answer generated")
                answer_type = "LLM"
                sources = []
                logger.info(f"[RESPONSE] answer_type={answer_type}")
                logger.info("[RESPONSE] Returning answer to user")
                
                return {
                    "answer": answer,
                    "answer_type": answer_type,
                    "sources": sources
                }
            
            # STEP 3: Validate answerability (OpenAI-style)
            logger.info("[VALIDATE] Starting answerability validation...")
            is_answerable, reason, validation_details = _validate_answerability(question, documents, metadatas)
            
            if not is_answerable:
                # Documents retrieved but don't match requirements → RAG_NO_ANSWER
                logger.warning(f"[ROUTER] Documents not answerable → RAG_NO_ANSWER")
                logger.info(f"[ROUTER] Reason: {reason}")
                
                # Build informative answer explaining why data is not available
                requested_year = validation_details.get("requested_year")
                requested_entity = validation_details.get("requested_entity")
                
                answer_parts = []
                if requested_year:
                    answer_parts.append(f"FY{requested_year[2:]} data")
                if requested_entity:
                    answer_parts.append(f"{requested_entity} data")
                
                if answer_parts:
                    answer = f"The requested {', '.join(answer_parts)} is not available in the documents."
                else:
                    answer = "The requested information is not available in the documents."
                
                # Extract sources from retrieved docs (even though not answerable)
                sources = []
                for meta in metadatas:
                    source_info = meta.get("source", meta.get("filename", "unknown"))
                    if meta.get("page"):
                        source_info += f" (page {meta.get('page')})"
                    if meta.get("fiscal_year"):
                        source_info += f" (FY: {meta.get('fiscal_year')})"
                    sources.append(source_info)
                
                answer_type = "RAG_NO_ANSWER"
                logger.info(f"[RESPONSE] answer_type={answer_type}")
                logger.info("[RESPONSE] Returning answer to user")
                
                return {
                    "answer": answer,
                    "answer_type": answer_type,
                    "sources": sources
                }
            
            # STEP 4: Documents are answerable → RAG generation
            logger.info("[ROUTER] Documents are answerable → RAG path")
            
            # Build context from documents
            context_parts = []
            for doc, meta in zip(documents, metadatas):
                meta_info = ""
                if meta.get("source"):
                    meta_info = f"Source: {meta.get('source')}"
                if meta.get("fiscal_year"):
                    meta_info += f", FY: {meta.get('fiscal_year')}"
                if meta.get("page"):
                    meta_info += f", Page: {meta.get('page')}"
                if meta_info:
                    context_parts.append(f"[{meta_info}]\n{doc}")
                else:
                    context_parts.append(doc)
            
            context = "\n\n---\n\n".join(context_parts)
            
            # Generate answer using RAG chain
            logger.info("[RAG] Sending context + query to LLM")
            answer = self.rag_chain.invoke({"question": question, "context": context})
            logger.info("[RAG] Answer generated")
            
            # Extract sources
            sources = []
            for meta in metadatas:
                source_info = meta.get("source", meta.get("filename", "unknown"))
                if meta.get("page"):
                    source_info += f" (page {meta.get('page')})"
                if meta.get("fiscal_year"):
                    source_info += f" (FY: {meta.get('fiscal_year')})"
                sources.append(source_info)
            
            answer_type = "RAG"
            logger.info(f"[RESPONSE] answer_type={answer_type}")
            logger.info("[RESPONSE] Returning answer to user")
            
            return {
                "answer": answer,
                "answer_type": answer_type,
                "sources": sources
            }
            
        except Exception as e:
            logger.error(f"LangChain orchestration failed: {e}", exc_info=True)
            return {
                "answer": "I apologize, but I encountered an error while processing your query. Please try again.",
                "answer_type": "LLM",
                "sources": []
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
    
    Uses OpenAI-style answerability validation with automatic LLM fallback.
    """
    orchestrator = get_orchestrator()
    return orchestrator.answer_query(question)
