"""Exceptions for DocumentGroup aggregate."""


class DocumentGroupException(Exception):
    """Base exception for document group errors."""
    
    pass


class DocumentGroupNotFound(DocumentGroupException):
    """Document group not found."""
    
    def __init__(self, group_id):
        super().__init__(f"Document group {group_id} not found")
        self.group_id = group_id


class InvalidGroupOperation(DocumentGroupException):
    """Invalid operation on document group."""
    
    pass


class DocumentAlreadyInGroup(DocumentGroupException):
    """Document is already a member of the group."""
    
    def __init__(self, document_id, group_id):
        super().__init__(
            f"Document {document_id} is already in group {group_id}"
        )
        self.document_id = document_id
        self.group_id = group_id


class DocumentNotInGroup(DocumentGroupException):
    """Document is not a member of the group."""
    
    def __init__(self, document_id, group_id):
        super().__init__(
            f"Document {document_id} is not in group {group_id}"
        )
        self.document_id = document_id
        self.group_id = group_id
