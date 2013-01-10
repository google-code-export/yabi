"""
A set of exceptions for use throughout the backend
"""

class BlockingException(Exception):
    """Any exception derived from this instead of the normal base exception will cause
    The task manager to temporarily block rather than error out
    """
    pass

class PermissionDenied(Exception):
    """Permission denied error"""
    pass

class InvalidPath(Exception):
    """The path passed is an invalid path for this connector"""
    pass

class IsADirectory(Exception):
    """pretty much only used where you try to delete a directory and dont use recurse"""
    pass

class AuthException(BlockingException):
    pass

class ProxyInitError(Exception):
    pass

class ProxyInvalidPassword(Exception):
    pass

class NotImplemented(Exception):
    """Exception to mark methods that haven't been overridden... yet..."""
    pass

class ExecutionError(Exception):
    pass

class CredentialNotFound(Exception):
    pass
