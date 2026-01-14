"""
LangChain Orchestration Layer

Replaces manual routing logic with LangChain-based orchestration.
Automatically decides between LLM-only, RAG-only, and RAG+LLM synthesis.

Uses LangChain v1 LCEL (LangChain Expression Language) pattern.
"""

import logging
import os
from typing import Dict, Any, List, Optional

from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser

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


class LangChainOrchestrator:
    """
    LangChain-based orchestration for RAG + LLM routing.
    
    Uses LangChain v1 LCEL pattern (prompt | llm | parser).
    Automatically decides: LLM-only, RAG-only, or RAG+LLM synthesis.
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
        
        # Setup prompts and chains
        self._setup_chains()
    
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
        
        # RAG prompt (document-based answers only)
        self.rag_template = """You are a financial AI assistant. Answer the question using ONLY the provided context documents.

Context documents:
{context}

Question: {question}

Instructions:
- Answer using ONLY information from the context documents
- Include specific numbers, dates, and facts when available
- If information is not in documents, say "This information is not available in the provided documents"
- Cite sources when referencing specific data

Answer:"""
        
        self.rag_prompt = ChatPromptTemplate.from_template(self.rag_template)
        self.rag_chain = self.rag_prompt | self.llm | self.output_parser
        
        # RAG+LLM synthesis prompt (documents + reasoning)
        self.synthesis_template = """You are a financial AI assistant. Answer the question using the provided context documents AND your knowledge.

Context documents:
{context}

Question: {question}

Instructions:
- Use information from context documents as the primary source
- Supplement with your knowledge when context is incomplete
- Provide analysis and reasoning when requested
- Include specific numbers and facts from documents
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
    
    def _retrieve_documents(self, question: str, n_results: int = 5) -> tuple[List[str], List[Dict]]:
        """
        Retrieve documents from Chroma Cloud.
        Returns: (documents, metadatas)
        """
        try:
            results = self.collection.query(
                query_texts=[question],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            documents = results.get("documents", [[]])[0] if results.get("documents") else []
            metadatas = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
            
            return documents, metadatas
        except Exception as e:
            logger.error(f"Document retrieval failed: {e}")
            return [], []
    
    def _rag_only_chain(self, question: str) -> tuple[str, List[str]]:
        """
        RAG-only chain: answers from documents only.
        Returns: (answer, sources)
        """
        documents, metadatas = self._retrieve_documents(question)
        
        if not documents:
            logger.warning("No documents retrieved, falling back to LLM")
            answer = self._llm_only_chain(question)
            return answer, []
        
        # Grade documents for relevance
        if not self._grade_documents(question, documents):
            logger.info("Documents not relevant, falling back to LLM")
            answer = self._llm_only_chain(question)
            return answer, []
        
        # Build context from documents
        context_parts = []
        for i, (doc, meta) in enumerate(zip(documents, metadatas)):
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
        Returns: (answer, sources)
        """
        documents, metadatas = self._retrieve_documents(question, n_results=5)
        
        if not documents:
            logger.warning("No documents retrieved, using LLM only")
            answer = self._llm_only_chain(question)
            return answer, []
        
        # Build context from documents
        context_parts = []
        for i, (doc, meta) in enumerate(zip(documents, metadatas)):
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
            # Fallback to LLM-only on any error (guaranteed answer)
            try:
                answer = self._llm_only_chain(question)
                return {
                    "answer": answer,
                    "answer_type": "LLM",
                    "sources": None
                }
            except Exception as fallback_error:
                logger.error(f"Fallback LLM also failed: {fallback_error}")
                return {
                    "answer": "I apologize, but I'm unable to process your query at the moment. Please try again.",
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
    Uses LangChain orchestration instead of manual routing.
    
    This replaces the manual routing logic in rag/query_engine.py
    with LangChain-based decision making (LCEL pattern).
    """
    orchestrator = get_orchestrator()
    return orchestrator.answer_query(question)
