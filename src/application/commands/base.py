from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Dict, Type, Any
from dataclasses import dataclass

from src.domain.commands.base import Command

TCommand = TypeVar("TCommand", bound=Command)
TResult = TypeVar("TResult")


class CommandHandler(ABC, Generic[TCommand, TResult]):
    @abstractmethod
    async def handle(self, command: TCommand) -> TResult:
        pass


class CommandDispatcher:
    def __init__(self):
        self._handlers: Dict[Type[Command], CommandHandler] = {}

    def register(
        self,
        command_type: Type[TCommand],
        handler: CommandHandler[TCommand, Any]
    ) -> None:
        self._handlers[command_type] = handler

    async def dispatch(self, command: Command) -> Any:
        command_type = type(command)
        handler = self._handlers.get(command_type)
        if handler is None:
            raise CommandHandlerNotFound(command_type.__name__)
        return await handler.handle(command)

    def has_handler(self, command_type: Type[Command]) -> bool:
        return command_type in self._handlers


class CommandHandlerNotFound(Exception):
    def __init__(self, command_name: str):
        self.command_name = command_name
        super().__init__(f"No handler registered for command: {command_name}")


@dataclass
class CommandResult:
    success: bool
    data: Any = None
    error: str = None

    @classmethod
    def ok(cls, data: Any = None) -> "CommandResult":
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, error: str) -> "CommandResult":
        return cls(success=False, error=error)
