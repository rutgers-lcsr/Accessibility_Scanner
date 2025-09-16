
from typing import List
import esprima

def is_valid_js(s: str) -> bool:
    try:
        esprima.parseScript(s)
        return True
    except esprima.Error:
        return False
    

def is_single_arrow_function(s: str, args: list, optional_async_function: bool = False) -> bool:
    try:
        parsed = esprima.parseScript(s)
        if not (len(parsed.body) == 1 and (isinstance(parsed.body[0].expression, esprima.nodes.ArrowFunctionExpression) or (isinstance(parsed.body[0].expression, esprima.nodes.AsyncArrowFunctionExpression) and optional_async_function))):
            return False
        
        func: esprima.nodes.FunctionDeclaration = parsed.body[0].expression  
        params: List[esprima.nodes.Identifier] = func.params
        
        for i, arg in enumerate(args):
            optional = arg.endswith("?")
            if optional:
                arg = arg[:-1]
            
            if i >= len(params):
                # if there are no more params, the rest must be optional
                if optional:
                    continue
                return False
            
            if params[i].name != arg and not optional:
                return False
        
        return True
    except esprima.Error:
        return False
    
def is_valid_object(s: str) -> bool:
    try:
        parsed = esprima.parseScript(f"({s})")
        return isinstance(parsed.body[0].expression, esprima.nodes.ObjectExpression)
    except esprima.Error:
        return False