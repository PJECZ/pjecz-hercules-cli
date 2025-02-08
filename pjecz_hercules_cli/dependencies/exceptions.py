"""
Exceptions
"""


class MyAnyError(Exception):
    """Base exception class"""


class MyAuthenticationError(MyAnyError):
    """Excepción porque fallo la autentificación"""


class MyConnectionError(MyAnyError):
    """Excepción porque no se pudo conectar"""


class MyEmptyError(MyAnyError):
    """Excepción porque no hay resultados"""


class MyFileNotAllowedError(MyAnyError):
    """Excepción porque no se permite el tipo del archivo"""


class MyFileNotFoundError(MyAnyError):
    """Excepción porque no se encontró el archivo"""


class MyIsDeletedError(MyAnyError):
    """Excepción porque está eliminado"""


class MyMissingConfigurationError(MyAnyError):
    """Excepción porque falta configuración"""


class MyNotExistsError(MyAnyError):
    """Excepción porque no existe"""


class MyOutOfRangeParamError(MyAnyError):
    """Excepción porque un parámetro esta fuera de rango"""


class MyRequestError(MyAnyError):
    """Excepción porque falló el request"""


class MyTimeoutError(MyAnyError):
    """Excepción porque se agoto el tiempo de espera"""
