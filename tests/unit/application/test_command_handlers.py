import pytest
from uuid import uuid4
from dataclasses import dataclass

from src.application.commands.base import (
    CommandHandler,
    CommandDispatcher,
    CommandHandlerNotFound,
    CommandResult,
)
from src.domain.commands.base import Command


@dataclass(frozen=True)
class TestCommand(Command):
    value: str = ""


@dataclass(frozen=True)
class AnotherTestCommand(Command):
    number: int = 0


class TestCommandHandler(CommandHandler[TestCommand, str]):
    async def handle(self, command: TestCommand) -> str:
        return f"Handled: {command.value}"


class AnotherTestCommandHandler(CommandHandler[AnotherTestCommand, int]):
    async def handle(self, command: AnotherTestCommand) -> int:
        return command.number * 2


class FailingCommandHandler(CommandHandler[TestCommand, str]):
    async def handle(self, command: TestCommand) -> str:
        raise ValueError("Handler failed")


class TestCommandDispatcher:
    def test_register_handler(self):
        dispatcher = CommandDispatcher()
        handler = TestCommandHandler()
        dispatcher.register(TestCommand, handler)
        assert dispatcher.has_handler(TestCommand)

    def test_has_handler_returns_false_for_unregistered(self):
        dispatcher = CommandDispatcher()
        assert not dispatcher.has_handler(TestCommand)

    @pytest.mark.asyncio
    async def test_dispatch_to_registered_handler(self):
        dispatcher = CommandDispatcher()
        handler = TestCommandHandler()
        dispatcher.register(TestCommand, handler)

        command = TestCommand(value="test")
        result = await dispatcher.dispatch(command)

        assert result == "Handled: test"

    @pytest.mark.asyncio
    async def test_dispatch_unregistered_command_raises(self):
        dispatcher = CommandDispatcher()
        command = TestCommand(value="test")

        with pytest.raises(CommandHandlerNotFound) as exc_info:
            await dispatcher.dispatch(command)

        assert "TestCommand" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_dispatch_multiple_command_types(self):
        dispatcher = CommandDispatcher()
        dispatcher.register(TestCommand, TestCommandHandler())
        dispatcher.register(AnotherTestCommand, AnotherTestCommandHandler())

        result1 = await dispatcher.dispatch(TestCommand(value="hello"))
        result2 = await dispatcher.dispatch(AnotherTestCommand(number=5))

        assert result1 == "Handled: hello"
        assert result2 == 10

    @pytest.mark.asyncio
    async def test_handler_exception_propagates(self):
        dispatcher = CommandDispatcher()
        dispatcher.register(TestCommand, FailingCommandHandler())

        with pytest.raises(ValueError) as exc_info:
            await dispatcher.dispatch(TestCommand(value="test"))

        assert "Handler failed" in str(exc_info.value)


class TestCommandResult:
    def test_ok_with_data(self):
        result = CommandResult.ok(data={"id": "123"})
        assert result.success is True
        assert result.data == {"id": "123"}
        assert result.error is None

    def test_ok_without_data(self):
        result = CommandResult.ok()
        assert result.success is True
        assert result.data is None

    def test_fail_with_error(self):
        result = CommandResult.fail("Something went wrong")
        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.data is None


class TestCommandHandlerNotFound:
    def test_exception_message(self):
        exc = CommandHandlerNotFound("UploadDocument")
        assert exc.command_name == "UploadDocument"
        assert "UploadDocument" in str(exc)
        assert "No handler registered" in str(exc)
