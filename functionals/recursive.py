"""
Tools for writing recursive-style functions that don't push onto the call-stack
"""

from functionals.wrappers import OptionlessDecorator


class CallRequest(object):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


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
        call_requests, returns, main_return = [], [], []
        generator = self.generators[0]
        args, kwargs = self.preprocess(args, kwargs)

        self.make_return_function(kwargs, main_return, None, None)
        iterator = generator(*args, **kwargs)

        self.append_next_request(generator, iterator, call_requests)

        while not main_return:
            while call_requests:
                generator, iterator, req = call_requests.pop(0)
                req = self._canonicalize_request(req)
                self.make_return_function(req.kwargs, returns,
                                          generator, iterator)
                target_generator = self.successors[generator]
                target_iterator = target_generator(*req.args, **req.kwargs)
                self.append_next_request(target_generator, target_iterator,
                                         call_requests)

            while returns:
                generator, iterator, return_value = returns.pop(0)
                self.send_and_append_next_request(generator, iterator,
                                                  call_requests, return_value)

        return self.postprocessor(main_return[0])

    def append_next_request(self, generator, iterator, request_queue):
        try:
            request_queue.append((generator, iterator, next(iterator)))
        except StopIteration:
            pass

    def send_and_append_next_request(self, generator, iterator,
                                     request_queue, to_send):
        try:
            next_request = iterator.send(to_send)
            request_queue.append((generator, iterator, next_request))
        except StopIteration:
            pass

    def make_return_function(self, kwargs, return_queue, generator, iterator):
        def return_value(r):
            if generator is not None:
                return_queue.append((generator, iterator, r))
            else:
                return_queue.append(r)
            raise StopIteration()
        kwargs['return_value'] = return_value

    def preprocess(self, args, kwargs):
        result = self.preprocessor(*args, **kwargs)
        if isinstance(result, tuple):
            if len(result) == 2 and isinstance(result[1], dict):
                return result
            return result, {}
        return (result,), {}

    def _canonicalize_request(self, request):
        if isinstance(request, CallRequest):
            return request
        return CallRequest(request)


recurse = CallRequest


class Recursor(CyclicRecursor, OptionlessDecorator):
    def __init__(self, f):
        CyclicRecursor.__init__(self, [f])
        OptionlessDecorator.__init__(self, f)

    def __call__(self, *args, **kwargs):
        return self.recurse(*args, **kwargs)
