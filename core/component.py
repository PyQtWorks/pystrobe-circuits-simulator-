from __future__ import annotations

from abc import ABC, abstractmethod
from collections import namedtuple
from functools import reduce
from operator import and_
from typing import Iterable, Callable

import rx.operators as rxop
from PyQt5 import QtCore
from rx import combine_latest
from rx.scheduler.mainloop import QtScheduler
from rx.subject import BehaviorSubject

Connection = namedtuple("Connection", ("src", "src_port", "dst", "dst_port"))


class Component(ABC):
    def __init__(self, number_of_inputs, number_of_outputs):
        self._inputs = [BehaviorSubject(True) for _ in range(number_of_inputs)]
        self._outputs = [BehaviorSubject(True) for _ in range(number_of_outputs)]
        self._output_connections = []

        input_vector = combine_latest(*self._inputs)
        self._subscriptions = []

        for index, output in enumerate(self._outputs):
            self._subscriptions.append(
                input_vector.pipe(
                    rxop.delay(0.5),
                    rxop.map(lambda vec: self.transfer_function_for(index)(vec)),
                    rxop.distinct_until_changed(),
                ).subscribe(observer=output, scheduler=QtScheduler(QtCore))
            )

    @property
    def number_of_inputs(self) -> int:
        return len(self._inputs)

    @property
    def number_of_outputs(self) -> int:
        return len(self._outputs)

    def connect_to(self, port: int, other: Component, other_port: int) -> None:
        subscription = self._outputs[port].subscribe(other._inputs[other_port])
        self._output_connections.append(subscription)

    @abstractmethod
    def transfer_function_for(
        self, output_index: int
    ) -> Callable[[Iterable[bool]], bool]:
        ...

    def output(self, index):
        return self._outputs[index]

    def input(self, index):
        return self._inputs[index]


class Gate(Component):
    def transfer_function_for(
        self, output_index: int
    ) -> Callable[[Iterable[bool]], bool]:
        if output_index >= self.number_of_outputs:
            raise ValueError("Output index out of range")

        def function(input_vector: Iterable[bool]) -> bool:
            return reduce(and_, input_vector, True)

        return function
