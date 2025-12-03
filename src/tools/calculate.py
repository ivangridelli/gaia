from langchain.tools import tool
import ast
import operator as op

# Supported operators
allowed_operators = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
    ast.USub: op.neg
}


def safe_eval(expr):
    """
    Safely evaluate arithmetic expressions.
    Supports +, -, *, /, %, **, parentheses, and unary minus.
    """

    def _eval(node):
        if isinstance(node, ast.Num):  # <number>
            return node.n
        elif isinstance(node, ast.BinOp):  # <left> <op> <right>
            if type(node.op) not in allowed_operators:
                raise ValueError(f"Operator {type(node.op)} not allowed")
            return allowed_operators[type(node.op)](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp):  # - <operand>
            if type(node.op) not in allowed_operators:
                raise ValueError(f"Operator {type(node.op)} not allowed")
            return allowed_operators[type(node.op)](_eval(node.operand))
        else:
            raise TypeError(f"Unsupported expression: {node}")

    node = ast.parse(expr, mode="eval").body
    return _eval(node)


@tool
def calculate(expression: str) -> str:
    """
    Safely calculate a mathematical expression and return the result as a string.

    Example usage:
    calculate("2 + 3 * (4 - 1)") -> "11"

    Only supports arithmetic operations: +, -, *, /, %, **, parentheses, and unary minus.
    """
    try:
        result = safe_eval(expression)
        return str(result)
    except Exception as e:
        return f"Error: {e}"
