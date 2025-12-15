"""
Code generation utilities for creating Python reference implementations.

Provides helpers for generating clean, executable Python code from
semantic specifications with proper formatting and type annotations.
"""

from typing import Any, Dict, List, Optional, Set
import textwrap


class CodeGenerator:
    """Utility for generating formatted Python code."""
    
    def __init__(self, indent_size: int = 4):
        """
        Initialize code generator.
        
        Args:
            indent_size: Number of spaces per indentation level
        """
        self.indent_size = indent_size
        self._current_indent = 0
    
    def indent(self) -> None:
        """Increase indentation level."""
        self._current_indent += self.indent_size
    
    def dedent(self) -> None:
        """Decrease indentation level."""
        self._current_indent = max(0, self._current_indent - self.indent_size)
    
    def reset_indent(self) -> None:
        """Reset indentation to zero."""
        self._current_indent = 0
    
    def line(self, code: str = "") -> str:
        """
        Generate an indented line of code.
        
        Args:
            code: Code content (without indentation)
            
        Returns:
            Indented code line with newline
        """
        if not code:
            return "\n"
        return " " * self._current_indent + code + "\n"
    
    def block(self, lines: List[str]) -> str:
        """
        Generate a block of code with current indentation.
        
        Args:
            lines: List of code lines (without indentation)
            
        Returns:
            Indented code block
        """
        return "".join(self.line(line) for line in lines)
    
    def function_signature(
        self,
        name: str,
        params: List[str],
        return_type: Optional[str] = None,
    ) -> str:
        """
        Generate a function signature.
        
        Args:
            name: Function name
            params: List of parameter definitions (e.g., ["x: float", "y: int"])
            return_type: Return type annotation
            
        Returns:
            Function signature line
        """
        params_str = ", ".join(params)
        if return_type:
            return f"def {name}({params_str}) -> {return_type}:"
        return f"def {name}({params_str}):"
    
    def docstring(self, content: str, style: str = "google") -> str:
        """
        Generate a docstring.
        
        Args:
            content: Docstring content
            style: Docstring style ("google", "numpy", "sphinx")
            
        Returns:
            Formatted docstring with quotes
        """
        if not content:
            return ""
        
        lines = content.strip().split("\n")
        if len(lines) == 1:
            return f'"""{lines[0]}"""\n'
        
        result = '"""\n'
        for line in lines:
            result += line + "\n"
        result += '"""\n'
        return result
    
    def import_statement(self, module: str, items: Optional[List[str]] = None) -> str:
        """
        Generate an import statement.
        
        Args:
            module: Module name
            items: Specific items to import (None for "import module")
            
        Returns:
            Import statement
        """
        if items:
            items_str = ", ".join(items)
            return f"from {module} import {items_str}\n"
        return f"import {module}\n"
    
    def class_definition(self, name: str, bases: Optional[List[str]] = None) -> str:
        """
        Generate a class definition.
        
        Args:
            name: Class name
            bases: Base classes
            
        Returns:
            Class definition line
        """
        if bases:
            bases_str = ", ".join(bases)
            return f"class {name}({bases_str}):"
        return f"class {name}:"
    
    def type_annotation(self, python_type: type) -> str:
        """
        Get type annotation string for a Python type.
        
        Args:
            python_type: Python type object
            
        Returns:
            Type annotation string
        """
        type_map = {
            int: "int",
            float: "float",
            str: "str",
            bool: "bool",
            list: "List[Any]",
            dict: "Dict[str, Any]",
        }
        
        # Handle date type
        if python_type.__name__ == "date":
            return "date"
        
        return type_map.get(python_type, "Any")
    
    def format_value(self, value: Any) -> str:
        """
        Format a Python value as code.
        
        Args:
            value: Value to format
            
        Returns:
            String representation suitable for code
        """
        if isinstance(value, str):
            return f'"{value}"'
        elif isinstance(value, bool):
            return "True" if value else "False"
        elif isinstance(value, (int, float)):
            return str(value)
        elif value is None:
            return "None"
        elif isinstance(value, (list, tuple)):
            items = ", ".join(self.format_value(v) for v in value)
            return f"[{items}]"
        elif isinstance(value, dict):
            items = ", ".join(f'"{k}": {self.format_value(v)}' for k, v in value.items())
            return f"{{{items}}}"
        else:
            return repr(value)
    
    def conditional(
        self,
        condition: str,
        then_block: List[str],
        else_block: Optional[List[str]] = None,
    ) -> str:
        """
        Generate an if-else conditional.
        
        Args:
            condition: Conditional expression
            then_block: Lines for the if block
            else_block: Lines for the else block (optional)
            
        Returns:
            Complete conditional statement
        """
        result = self.line(f"if {condition}:")
        self.indent()
        result += self.block(then_block)
        self.dedent()
        
        if else_block:
            result += self.line("else:")
            self.indent()
            result += self.block(else_block)
            self.dedent()
        
        return result
    
    def try_except(
        self,
        try_block: List[str],
        except_blocks: List[tuple[str, List[str]]],
        finally_block: Optional[List[str]] = None,
    ) -> str:
        """
        Generate a try-except block.
        
        Args:
            try_block: Lines for try block
            except_blocks: List of (exception_type, handler_lines) tuples
            finally_block: Lines for finally block (optional)
            
        Returns:
            Complete try-except statement
        """
        result = self.line("try:")
        self.indent()
        result += self.block(try_block)
        self.dedent()
        
        for exc_type, handler_lines in except_blocks:
            result += self.line(f"except {exc_type}:")
            self.indent()
            result += self.block(handler_lines)
            self.dedent()
        
        if finally_block:
            result += self.line("finally:")
            self.indent()
            result += self.block(finally_block)
            self.dedent()
        
        return result
    
    def assignment(self, variable: str, value: Any, type_hint: Optional[str] = None) -> str:
        """
        Generate an assignment statement.
        
        Args:
            variable: Variable name
            value: Value to assign (will be formatted)
            type_hint: Optional type hint
            
        Returns:
            Assignment statement
        """
        value_str = self.format_value(value) if not isinstance(value, str) else value
        if type_hint:
            return f"{variable}: {type_hint} = {value_str}"
        return f"{variable} = {value_str}"
    
    def return_statement(self, value: Optional[str] = None) -> str:
        """
        Generate a return statement.
        
        Args:
            value: Value to return (as string expression)
            
        Returns:
            Return statement
        """
        if value is None:
            return "return"
        return f"return {value}"
