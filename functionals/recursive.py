"""
Tools for writing recursive-style functions that don't push onto the call-stack
"""

from functionals.wrappers import OptionlessDecorator


class CallRequest(object):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


def do_return(value):
    raise StopIteration(value)


class StopRecursion(StopIteration):
    pass


class RecursiveCaller(object):
    def __init__(self, recursor, input_args, input_kwargs):
        self.recursor = recursor
        # TODO these could have better names
        # TODO garbage collection
        self.call_requests = []
        self.call_returns = []
        self.input_args = input_args
        self.input_kwargs = input_kwargs
        self.returns_to = {}
        self.generator_of = {}

    def call_and_log(self, generator, args, kwargs):
        iterator = generator(*args, **kwargs)
        self.generator_of[iterator] = generator
        return iterator

    def recurse(self):
        generator = self.recursor.generators[0]
        iterator = self.call_and_log(generator,
                                     self.input_args,
                                     self.input_kwargs)

        self.returns_to[iterator] = None
        self.generator_of[iterator] = generator

        self.append_next_request(iterator)

        while True:
            try:
                self._do_call_requests()
                self._do_call_returns()
            except StopRecursion as s:
                return s.value

    def _do_call_requests(self):
        while self.call_requests:
            iterator, req = self.call_requests.pop(0)
            req = self._canonicalize_request(req)
            generator = self.generator_of[iterator]
            # TODO don't brak this abstraction
            # TODO rename these
            target_generator = self.recursor.successors[generator]
            target_iterator = target_generator(*req.args, **req.kwargs)
            self.generator_of[target_iterator] = target_generator
            self.returns_to[target_iterator] = iterator
            self.append_next_request(target_iterator)

    def _do_call_returns(self):
        while self.call_returns:
            iterator, value = self.call_returns.pop(0)
            if iterator is None:
                raise StopRecursion(value)
            self.send_and_append_next_request(iterator, value)

    def append_next_request(self, iterator):
        # TODO make this try/except into a contextmanager
        try:
            self.call_requests.append((iterator, next(iterator)))
        except StopIteration as s:
            self.call_returns.append((self.returns_to[iterator], s.value))
            del self.returns_to[iterator]

    def send_and_append_next_request(self, iterator, value):
        try:
            next_request = iterator.send(value)
            self.call_requests.append((iterator, next_request))
        except StopIteration as s:
            self.call_returns.append((self.returns_to[iterator], s.value))
            del self.returns_to[iterator]

    def _canonicalize_request(self, request):
        if isinstance(request, CallRequest):
            return request
        return CallRequest(request)


class CyclicRecursor(object):
    pack = lambda *args, **kwargs: (args, kwargs)
    identity = lambda x: x

    def __init__(self, generators, preprocessor=pack, postprocessor=identity):
        self.generators = generators
        self.preprocessor = preprocessor
        self.postprocessor = postprocessor
        self.successors = {
            generators[i]: generators[i+1]
            for i in range(len(generators) - 1)
        }
        self.successors[generators[-1]] = generators[0]

    def recurse(self, *args, **kwargs):
        args, kwargs = self.preprocess(args, kwargs)
        recursive_caller = RecursiveCaller(self, args, kwargs)
        return self.postprocessor(recursive_caller.recurse())

    def preprocess(self, args, kwargs):
        result = self.preprocessor(*args, **kwargs)
        if isinstance(result, tuple):
            if len(result) == 2 and isinstance(result[1], dict):
                return result
            return result, {}
        return (result,), {}


recurse = CallRequest


class Recursor(CyclicRecursor, OptionlessDecorator):
    def __init__(self, f):
        CyclicRecursor.__init__(self, [f])
        OptionlessDecorator.__init__(self, f)

    def __call__(self, *args, **kwargs):
        return self.recurse(*args, **kwargs)
