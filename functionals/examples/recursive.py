from functionals.recursive import CyclicRecursor, do_return, Recursor


class MetaCircularEvaluator(CyclicRecursor):
    def lisp_eval(expression):
        if isinstance(expression, tuple):
            do_return((yield expression))
        do_return(expression)

    def lisp_apply(expression):
        evaluated = []
        for part in expression:
            evaluated.append((yield part))
        do_return(evaluated[0](*evaluated[1:]))

    def __init__(self, eval_function=lisp_eval, apply_function=lisp_apply):
        super().__init__([eval_function, apply_function])

    def evaluate(self, expression):
        return self.recurse(expression)


@Recursor.decorate
def factorial(n):
    if n == 0:
        do_return(1)
    do_return(n * (yield n-1))


@Recursor.decorate
def fib(n):
    if n in [0, 1]:
        do_return(n)
    do_return((yield n-1) + (yield n-2))
