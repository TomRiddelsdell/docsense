"""Test data loader for local development mode."""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class TestDataLoader:
    """Loads test documents for development mode.
    
    Loads sample documents from data/test_documents/ directory
    for the test user to enable immediate testing without manual uploads.
    
    See ADR-023 for development authentication bypass architecture.
    """
    
    def __init__(self):
        self.test_docs_dir = Path("data/test_documents")
        self.loaded_marker_file = Path(".dev_test_data_loaded")
    
    async def ensure_test_data_loaded(
        self,
        user_kerberos_id: str,
        max_documents: int = 10
    ) -> None:
        """
        Load test documents for the test user if not already present.
        
        Args:
            user_kerberos_id: Kerberos ID of the test user
            max_documents: Maximum number of test documents to load
        """
        # Check if already loaded (marker file exists)
        if self.loaded_marker_file.exists():
            logger.info(
                f"Test data already loaded for {user_kerberos_id} "
                "(marker file exists, skipping)"
            )
            return
        
        # Check if test documents directory exists
        if not self.test_docs_dir.exists():
            logger.warning(
                f"Test documents directory '{self.test_docs_dir}' not found. "
                "Skipping test data loading. Create test documents or "
                "run generate_test_documents.py to populate."
            )
            return
        
        logger.info(
            f"Loading test documents for {user_kerberos_id} "
            f"from {self.test_docs_dir}..."
        )
        
        # Find JSON test document files
        json_files = sorted(self.test_docs_dir.glob("doc_*.json"))
        
        if not json_files:
            logger.warning(
                f"No test document JSON files found in {self.test_docs_dir}. "
                "Expected files matching pattern: doc_*.json"
            )
            return
        
        # Load sample documents (limited to max_documents)
        loaded_count = 0
        for json_file in json_files[:max_documents]:
            try:
                await self._load_test_document(
                    json_file=json_file,
                    user_kerberos_id=user_kerberos_id,
                    document_number=loaded_count + 1
                )
                loaded_count += 1
            except Exception as e:
                logger.error(
                    f"Failed to load test document {json_file.name}: {e}",
                    exc_info=True
                )
        
        if loaded_count > 0:
            logger.info(
                f"✅ Loaded {loaded_count} test documents for {user_kerberos_id}"
            )
            
            # Create marker file to avoid re-loading
            self.loaded_marker_file.write_text(
                f"Test data loaded for {user_kerberos_id}\n"
                f"Documents: {loaded_count}\n"
            )
        else:
            logger.warning("No test documents were loaded successfully")
    
    async def _load_test_document(
        self,
        json_file: Path,
        user_kerberos_id: str,
        document_number: int
    ) -> None:
        """
        Load a single test document.
        
        Args:
            json_file: Path to test document JSON file
            user_kerberos_id: Kerberos ID of the test user
            document_number: Sequential number for this document
        """
        # Read JSON document data
        with open(json_file, 'r', encoding='utf-8') as f:
            doc_data = json.load(f)
        
        # Extract document metadata
        title = doc_data.get('title', f'Test Document {document_number}')
        description = doc_data.get('description', 'Test document for development')
        
        logger.debug(
            f"Loading test document {document_number}: {title} "
            f"from {json_file.name}"
        )
        
        # TODO: Integrate with actual document upload command/handler
        # For now, just log what would be uploaded
        # In full implementation, this would call:
        # - UploadDocumentCommand with user context
        # - Store document with metadata: {"dev_test_data": True}
        
        logger.debug(
            f"  Title: {title}\n"
            f"  Description: {description}\n"
            f"  Owner: {user_kerberos_id}\n"
            f"  Source: {json_file.name}"
        )
        
        # Mark document as test data in metadata
        metadata = {
            "dev_test_data": True,
            "source_file": json_file.name,
            "test_document_number": document_number
        }
        
        # Note: Actual implementation would use DocumentRepository
        # and UploadDocumentHandler to create the document properly
        # following the event-sourced architecture
    
    def clear_marker(self) -> None:
        """Clear the test data loaded marker file.
        
        Use this to force re-loading test data on next startup.
        """
        if self.loaded_marker_file.exists():
            self.loaded_marker_file.unlink()
            logger.info("Test data marker cleared - will reload on next startup")
    
    def get_test_document_metadata(self) -> List[Dict[str, Any]]:
        """
        Get metadata about available test documents.
        
        Returns:
            List of test document metadata dictionaries
        """
        test_docs = []
        
        if not self.test_docs_dir.exists():
            return test_docs
        
        for json_file in sorted(self.test_docs_dir.glob("doc_*.json")):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    doc_data = json.load(f)
                
                test_docs.append({
                    "filename": json_file.name,
                    "title": doc_data.get('title', 'Untitled'),
                    "description": doc_data.get('description', ''),
                    "issues_count": len(doc_data.get('issues', [])),
                    "path": str(json_file)
                })
            except Exception as e:
                logger.warning(f"Could not read metadata from {json_file.name}: {e}")
        
        return test_docs
