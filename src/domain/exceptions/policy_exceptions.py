from uuid import UUID


class PolicyException(Exception):
    pass


class PolicyRepositoryNotFound(PolicyException):
    def __init__(self, repository_id: UUID):
        self.repository_id = repository_id
        super().__init__(f"Policy repository not found: {repository_id}")


class InvalidPolicy(PolicyException):
    def __init__(self, policy_name: str, reason: str):
        self.policy_name = policy_name
        self.reason = reason
        super().__init__(f"Invalid policy '{policy_name}': {reason}")


class PolicyAlreadyExists(PolicyException):
    def __init__(self, policy_name: str):
        self.policy_name = policy_name
        super().__init__(f"Policy already exists with name: {policy_name}")


class PolicyIdAlreadyExists(PolicyException):
    def __init__(self, policy_id):
        self.policy_id = policy_id
        super().__init__(f"Policy already exists with ID: {policy_id}")
