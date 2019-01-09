from typing import Type

from .plugin import PynamodbPlugin


def plugin(version: str) -> Type[PynamodbPlugin]:
    return PynamodbPlugin
