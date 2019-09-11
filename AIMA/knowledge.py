"""Knowledge in learning, Chapter 19"""

from random import shuffle
from math import log
from .utils import powerset
from collections import defaultdict
from itertools import combinations, product
from .logic import (FolKB, constant_symbols, predicate_symbols, standardize_variables,
                   variables, is_definite_clause, subst, expr, Expr)
from functools import partial

# ______________________________________________________________________________


def current_best_learning(examples, h, examples_so_far=[]):
    """ [Figure 19.2]
    The hypothesis is a list of dictionaries, with each dictionary representing
    a disjunction."""
    if not examples:
        return h

    e = examples[0]
    if is_consistent(e, h):
        return current_best_learning(examples[1:], h, examples_so_far + [e])
    elif false_positive(e, h):
        for h2 in specializations(examples_so_far + [e], h):
            h3 = current_best_learning(examples[1:], h2, examples_so_far + [e])
            if h3 != 'FAIL':
                return h3
    elif false_negative(e, h):
        for h2 in generalizations(examples_so_far + [e], h):
            h3 = current_best_learning(examples[1:], h2, examples_so_far + [e])
            if h3 != 'FAIL':
                return h3

    return 'FAIL'


def specializations(examples_so_far, h):
    """Specialize the hypothesis by adding AND operations to the disjunctions"""
    hypotheses = []

    for i, disj in enumerate(h):
        for e in examples_so_far:
            for k, v in e.items():
                if k in disj or k == 'GOAL':
                    continue

                h2 = h[i].copy()
                h2[k] = '!' + v
                h3 = h.copy()
                h3[i] = h2
                if check_all_consistency(examples_so_far, h3):
                    hypotheses.append(h3)

    shuffle(hypotheses)
    return hypotheses


def generalizations(examples_so_far, h):
    """Generalize the hypothesis. First delete operations
    (including disjunctions) from the hypothesis. Then, add OR operations."""
    hypotheses = []

    # Delete disjunctions
    disj_powerset = powerset(range(len(h)))
    for disjs in disj_powerset:
        h2 = h.copy()
        for d in reversed(list(disjs)):
            del h2[d]

        if check_all_consistency(examples_so_far, h2):
            hypotheses += h2

    # Delete AND operations in disjunctions
    for i, disj in enumerate(h):
        a_powerset = powerset(disj.keys())
        for attrs in a_powerset:
            h2 = h[i].copy()
            for a in attrs:
                del h2[a]

            if check_all_consistency(examples_so_far, [h2]):
                h3 = h.copy()
                h3[i] = h2.copy()
                hypotheses += h3

    # Add OR operations
    if hypotheses == [] or hypotheses == [{}]:
        hypotheses = add_or(examples_so_far, h)
    else:
        hypotheses.extend(add_or(examples_so_far, h))

    shuffle(hypotheses)
    return hypotheses


def add_or(examples_so_far, h):
    """Add an OR operation to the hypothesis. The AND operations in the disjunction
    are generated by the last example (which is the problematic one)."""
    ors = []
    e = examples_so_far[-1]

    attrs = {k: v for k, v in e.items() if k != 'GOAL'}
    a_powerset = powerset(attrs.keys())

    for c in a_powerset:
        h2 = {}
        for k in c:
            h2[k] = attrs[k]

        if check_negative_consistency(examples_so_far, h2):
            h3 = h.copy()
            h3.append(h2)
            ors.append(h3)

    return ors

# ______________________________________________________________________________


def version_space_learning(examples):
    """ [Figure 19.3]
    The version space is a list of hypotheses, which in turn are a list
    of dictionaries/disjunctions."""
    V = all_hypotheses(examples)
    for e in examples:
        if V:
            V = version_space_update(V, e)

    return V


def version_space_update(V, e):
    return [h for h in V if is_consistent(e, h)]


def all_hypotheses(examples):
    """Build a list of all the possible hypotheses"""
    values = values_table(examples)
    h_powerset = powerset(values.keys())
    hypotheses = []
    for s in h_powerset:
        hypotheses.extend(build_attr_combinations(s, values))

    hypotheses.extend(build_h_combinations(hypotheses))

    return hypotheses


def values_table(examples):
    """Build a table with all the possible values for each attribute.
    Returns a dictionary with keys the attribute names and values a list
    with the possible values for the corresponding attribute."""
    values = defaultdict(lambda: [])
    for e in examples:
        for k, v in e.items():
            if k == 'GOAL':
                continue

            mod = '!'
            if e['GOAL']:
                mod = ''

            if mod + v not in values[k]:
                values[k].append(mod + v)

    values = dict(values)
    return values


def build_attr_combinations(s, values):
    """Given a set of attributes, builds all the combinations of values.
    If the set holds more than one attribute, recursively builds the
    combinations."""
    if len(s) == 1:
        # s holds just one attribute, return its list of values
        k = values[s[0]]
        h = [[{s[0]: v}] for v in values[s[0]]]
        return h

    h = []
    for i, a in enumerate(s):
        rest = build_attr_combinations(s[i+1:], values)
        for v in values[a]:
            o = {a: v}
            for r in rest:
                t = o.copy()
                for d in r:
                    t.update(d)
                h.append([t])

    return h


def build_h_combinations(hypotheses):
    """Given a set of hypotheses, builds and returns all the combinations of the
    hypotheses."""
    h = []
    h_powerset = powerset(range(len(hypotheses)))

    for s in h_powerset:
        t = []
        for i in s:
            t.extend(hypotheses[i])
        h.append(t)

    return h

# ______________________________________________________________________________


def minimal_consistent_det(E, A):
    """Return a minimal set of attributes which give consistent determination"""
    n = len(A)

    for i in range(n + 1):
        for A_i in combinations(A, i):
            if consistent_det(A_i, E):
                return set(A_i)


def consistent_det(A, E):
    """Check if the attributes(A) is consistent with the examples(E)"""
    H = {}

    for e in E:
        attr_values = tuple(e[attr] for attr in A)
        if attr_values in H and H[attr_values] != e['GOAL']:
            return False
        H[attr_values] = e['GOAL']

    return True

# ______________________________________________________________________________


class FOIL_container(FolKB):
    """Hold the kb and other necessary elements required by FOIL."""

    def __init__(self, clauses=None):
        self.const_syms = set()
        self.pred_syms = set()
        FolKB.__init__(self, clauses)

    def tell(self, sentence):
        if is_definite_clause(sentence):
            self.clauses.append(sentence)
            self.const_syms.update(constant_symbols(sentence))
            self.pred_syms.update(predicate_symbols(sentence))
        else:
            raise Exception("Not a definite clause: {}".format(sentence))

    def foil(self, examples, target):
        """Learn a list of first-order horn clauses
        'examples' is a tuple: (positive_examples, negative_examples).
        positive_examples and negative_examples are both lists which contain substitutions."""
        clauses = []

        pos_examples = examples[0]
        neg_examples = examples[1]

        while pos_examples:
            clause, extended_pos_examples = self.new_clause((pos_examples, neg_examples), target)
            # remove positive examples covered by clause
            pos_examples = self.update_examples(target, pos_examples, extended_pos_examples)
            clauses.append(clause)

        return clauses

    def new_clause(self, examples, target):
        """Find a horn clause which satisfies part of the positive
        examples but none of the negative examples.
        The horn clause is specified as [consequent, list of antecedents]
        Return value is the tuple (horn_clause, extended_positive_examples)."""
        clause = [target, []]
        # [positive_examples, negative_examples]
        extended_examples = examples
        while extended_examples[1]:
            l = self.choose_literal(self.new_literals(clause), extended_examples)
            clause[1].append(l)
            extended_examples = [sum([list(self.extend_example(example, l)) for example in
                                      extended_examples[i]], []) for i in range(2)]

        return (clause, extended_examples[0])

    def extend_example(self, example, literal):
        """Generate extended examples which satisfy the literal."""
        # find all substitutions that satisfy literal
        for s in self.ask_generator(subst(example, literal)):
            s.update(example)
            yield s

    def new_literals(self, clause):
        """Generate new literals based on known predicate symbols.
        Generated literal must share atleast one variable with clause"""
        share_vars = variables(clause[0])
        for l in clause[1]:
            share_vars.update(variables(l))
        for pred, arity in self.pred_syms:
            new_vars = {standardize_variables(expr('x')) for _ in range(arity - 1)}
            for args in product(share_vars.union(new_vars), repeat=arity):
                if any(var in share_vars for var in args):
                    # make sure we don't return an existing rule
                    if not Expr(pred, args) in clause[1]:
                        yield Expr(pred, *[var for var in args])


    def choose_literal(self, literals, examples): 
        """Choose the best literal based on the information gain."""

        return max(literals, key = partial(self.gain , examples = examples))


    def gain(self, l ,examples):
        """
        Find the utility of each literal when added to the body of the clause. 
        Utility function is: 
            gain(R, l) = T * (log_2 (post_pos / (post_pos + post_neg)) - log_2 (pre_pos / (pre_pos + pre_neg)))

        where: 
        
            pre_pos = number of possitive bindings of rule R (=current set of rules)
            pre_neg = number of negative bindings of rule R 
            post_pos = number of possitive bindings of rule R' (= R U {l} )
            post_neg = number of negative bindings of rule R' 
            T = number of possitive bindings of rule R that are still covered 
                after adding literal l 

        """
        pre_pos = len(examples[0])
        pre_neg = len(examples[1])
        post_pos = sum([list(self.extend_example(example, l)) for example in examples[0]], [])           
        post_neg = sum([list(self.extend_example(example, l)) for example in examples[1]], []) 
        if pre_pos + pre_neg ==0 or len(post_pos) + len(post_neg)==0:
            return -1
        # number of positive example that are represented in extended_examples
        T = 0
        for example in examples[0]:
            represents = lambda d: all(d[x] == example[x] for x in example)
            if any(represents(l_) for l_ in post_pos):
                T += 1
        value = T * (log(len(post_pos) / (len(post_pos) + len(post_neg)) + 1e-12,2) - log(pre_pos / (pre_pos + pre_neg),2))
        return value


    def update_examples(self, target, examples, extended_examples):
        """Add to the kb those examples what are represented in extended_examples
        List of omitted examples is returned."""
        uncovered = []
        for example in examples:
            represents = lambda d: all(d[x] == example[x] for x in example)
            if any(represents(l) for l in extended_examples):
                self.tell(subst(example, target))
            else:
                uncovered.append(example)

        return uncovered


# ______________________________________________________________________________


def check_all_consistency(examples, h):
    """Check for the consistency of all examples under h."""
    for e in examples:
        if not is_consistent(e, h):
            return False

    return True


def check_negative_consistency(examples, h):
    """Check if the negative examples are consistent under h."""
    for e in examples:
        if e['GOAL']:
            continue

        if not is_consistent(e, [h]):
            return False

    return True


def disjunction_value(e, d):
    """The value of example e under disjunction d."""
    for k, v in d.items():
        if v[0] == '!':
            # v is a NOT expression
            # e[k], thus, should not be equal to v
            if e[k] == v[1:]:
                return False
        elif e[k] != v:
            return False

    return True


def guess_value(e, h):
    """Guess value of example e under hypothesis h."""
    for d in h:
        if disjunction_value(e, d):
            return True

    return False


def is_consistent(e, h):
    return e["GOAL"] == guess_value(e, h)


def false_positive(e, h):
    return guess_value(e, h) and not e["GOAL"]


def false_negative(e, h):
    return e["GOAL"] and not guess_value(e, h)


    


