class FinkernelError(Exception):
    pass

class PSLSyntaxError(FinkernelError):
    def __init__(self, message: str, line: int = None, column: int = None):
        super().__init__(message)
        self.line = line
        self.column = column

class PSLTypeError(FinkernelError):
    pass

class PSLValidationError(FinkernelError):
    pass
