from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from typing import Callable
from typing import Collection

__all__ = ["dumps", "loads"]


@dataclass
class Handler[T](ABC):
    tag: str
    factory: Callable[[Any], T]
    delimiter: str = ":"

    @classmethod
    def _pack(cls, length: int, value: str) -> str:
        return f"{cls.tag}{length}{cls.delimiter}{value}"

    @classmethod
    def get_tag(cls, raw: str) -> str:
        return raw[0]

    @classmethod
    def _unpack(cls, raw: str) -> tuple[str, int, int]:
        tag = cls.get_tag(raw)
        length_str = raw[len(tag) :].split(cls.delimiter, maxsplit=1)[0]
        value_offset = len(length_str) + len(tag) + len(cls.delimiter)
        length = int(length_str)
        value = str(raw[value_offset : value_offset + length])
        return value, length, value_offset

    @classmethod
    @abstractmethod
    def encode(cls, data: T) -> tuple[str, int]:
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def decode(cls, raw: str) -> tuple[T, int]:
        raise NotImplementedError


class Factory:
    _tag_2_handler: dict[str, type[Handler]] = {}
    _type_2_handler: dict[Callable[[Any], Any], type[Handler]] = {}

    @classmethod
    def register(cls, handler: type[Handler]) -> type[Handler]:
        if handler.tag in cls._tag_2_handler:
            raise KeyError(f"{handler.tag} already registered")
        cls._tag_2_handler[handler.tag] = handler
        cls._type_2_handler[handler.factory] = handler
        return handler

    @classmethod
    def get_by_raw_data(cls, raw: str) -> type[Handler]:
        tag = Handler.get_tag(raw)
        return cls._tag_2_handler[tag]

    @classmethod
    def get_by_data(cls, data: Any) -> type[Handler]:
        return cls._type_2_handler[type(data)]


@Factory.register
@dataclass
class NoneHandler(Handler[None]):  # type: ignore
    tag: str = "N"
    factory: Callable[[], None] = type(None)

    @classmethod
    def encode(cls, data: None) -> tuple[str, int]:
        value = ""
        length = len(value)
        return cls._pack(length, value), length

    @classmethod
    def decode(cls, data: str) -> tuple[None, int]:
        value, length, offset = cls._unpack(data)
        none = cls.factory()
        return none, len(value) + offset


@Factory.register
@dataclass
class BooleanHandler(Handler[bool]):
    tag: str = "B"
    factory: Callable[[Any], bool] = bool

    @classmethod
    def encode(cls, data: bool) -> tuple[str, int]:
        item_raw = str(int(data))
        length = len(item_raw)
        return cls._pack(length, item_raw), length

    @classmethod
    def decode(cls, raw: str) -> tuple[bool, int]:
        value, length, offset = cls._unpack(raw)
        return cls.factory(int(value)), len(value) + offset


@Factory.register
@dataclass
class StringHandler(Handler[str]):
    tag: str = "S"
    factory: Callable[[Any], str] = str

    @classmethod
    def encode(cls, data: str) -> tuple[str, int]:
        length = len(data)
        return cls._pack(length, data), length

    @classmethod
    def decode(cls, raw: str) -> tuple[str, int]:
        value, length, offset = cls._unpack(raw)
        return cls.factory(value), len(value) + offset


@Factory.register
@dataclass
class DatetimeHandler(Handler[datetime]):
    tag: str = "D"
    factory: Callable[[Any], datetime] = datetime

    @classmethod
    def encode(cls, data: datetime) -> tuple[str, int]:
        value = data.isoformat()
        length = len(value)
        return cls._pack(length, value), length

    @classmethod
    def decode(cls, raw: str) -> tuple[datetime, int]:
        value, length, offset = cls._unpack(raw)
        return datetime.fromisoformat(value), len(value) + offset


@dataclass
class GenericNumberHandler[T](Handler):
    @classmethod
    def encode(cls, data: T) -> tuple[str, int]:
        item_raw = str(data)
        length = len(item_raw)
        return cls._pack(length, item_raw), length

    @classmethod
    def decode(cls, raw: str) -> tuple[T, int]:
        value, length, offset = cls._unpack(raw)
        return cls.factory(value), len(value) + offset


@Factory.register
@dataclass
class IntegerHandler(GenericNumberHandler[int]):
    tag: str = "I"
    factory: Callable[[Any], int] = int


@Factory.register
@dataclass
class FloatHandler(GenericNumberHandler[float]):
    tag: str = "F"
    factory: Callable[[Any], float] = float


class GenericCollectionHandler[T: Collection](Handler):
    @classmethod
    def encode(cls, data: T) -> tuple[str, int]:
        data_str = "".join(Factory.get_by_data(i).encode(i)[0] for i in data)
        length = len(data_str)
        return cls._pack(length, data_str), length

    @classmethod
    def decode(cls, raw: str) -> tuple[T, int]:
        value, length, value_offset = cls._unpack(raw)
        items = []
        offset = 0
        while offset < len(value):
            item_data = value[offset:]
            item_handler = Factory.get_by_raw_data(item_data)
            item, item_len = item_handler.decode(item_data)
            items.append(item)
            offset += item_len
        return cls.factory(items), len(value) + value_offset


@Factory.register
@dataclass
class ListHandler(GenericCollectionHandler[list]):
    tag: str = "L"
    factory: Callable[[Any], list] = list


@Factory.register
@dataclass
class TupleHandler(GenericCollectionHandler[tuple]):
    tag: str = "T"
    factory: Callable[[Any], tuple] = tuple


@Factory.register
@dataclass
class SetHandler(GenericCollectionHandler[set]):
    tag: str = "s"
    factory: Callable[[Any], set] = set


@Factory.register
@dataclass
class DictionaryHandler(Handler[dict]):
    tag: str = "d"
    factory: Callable[[Any], dict] = dict
    pair_handler: type[GenericCollectionHandler] = TupleHandler

    @classmethod
    def encode(cls, data: dict) -> tuple[str, int]:
        data_str = "".join(
            cls.pair_handler.encode((key, value))[0] for key, value in data.items()
        )
        length = len(data_str)
        return cls._pack(length, data_str), length

    @classmethod
    def decode(cls, raw: str) -> tuple[dict, int]:
        value, length, value_offset = cls._unpack(raw)
        pairs = []
        offset = 0
        while offset < len(value):
            pair_raw = value[offset:]
            pair, pair_len = cls.pair_handler.decode(pair_raw)
            pairs.append(pair)
            offset += pair_len
        return cls.factory(pairs), len(value) + value_offset


def dumps(data: Any) -> str:
    handler = Factory.get_by_data(data)
    return handler.encode(data)[0]


def loads(data: str) -> Any:
    handler = Factory.get_by_raw_data(data)
    return handler.decode(data)[0]
