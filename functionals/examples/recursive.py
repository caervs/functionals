from functionals.recursive import CyclicRecursor, Recursor

class MetaCircularEvaluator(CyclicRecursor):
    def lisp_eval(expression, return_value=None):
        if isinstance(expression, tuple):
            return_value((yield expression))
        return_value(expression)

    def lisp_apply(expression, return_value):
        evaluated = []
        for part in expression:
            evaluated.append((yield part))
        return_value(evaluated[0](*evaluated[1:]))

    def __init__(self, eval_function=lisp_eval, apply_function=lisp_apply):
        super().__init__([eval_function, apply_function])

    def evaluate(self, expression):
        return self.recurse(expression)


@Recursor.decorate
def factorial(n, return_value):
    if n == 0:
        return_value(1)
    return_value(n * (yield n-1))


@Recursor.decorate
def fib(n, return_value):
    if n in [0, 1]:
        return_value(n)
    return_value((yield n-1) + (yield n-2))
