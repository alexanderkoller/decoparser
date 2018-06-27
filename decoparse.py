from collections import defaultdict
from queue import Queue

class Symbol:
    def __init__(self, s):
        self.sym = s

    def __str__(self):
        return self.sym

    def __repr__(self):
        return self.sym

    def __eq__(self, other):
        return (self.__class__ == other.__class__) and (self.sym == other.sym)

    def __hash__(self):
        return hash(self.sym)

class Terminal(Symbol):
    def __init__(self, s):
        super().__init__(s)

class Nonterminal(Symbol):
    def __init__(self, s):
        super().__init__(s)



class Rule:
    def __init__(self, lhs, rhs, eval):
        self.lhs = lhs
        self.rhs = rhs
        self.eval = eval

    @staticmethod
    def _make_symbol(sym):
        if sym[0].isupper():
            return Nonterminal(sym)
        else:
            return Terminal(sym)

    @staticmethod
    def create(rule_string, eval):
        parts = rule_string.strip().split()
        assert parts[1] == "->"

        lhs = Rule._make_symbol(parts[0])
        assert isinstance(lhs, Nonterminal)

        rhs = [Rule._make_symbol(x) for x in parts[2:]]
        assert len(rhs) > 0

        return Rule(lhs, rhs, eval)

    def __str__(self):
        rhss = [symbol.sym for symbol in self.rhs]
        return f"{self.lhs} -> {' '.join(rhss)}: {self.eval.__name__}"

    def __repr__(self):
        return str(self)


class Grammar:
    def __init__(self):
        self.topdown = defaultdict(list)

    def rule(self, rule_string):
        def decorate(eval):
            r = Rule.create(rule_string, eval)
            self.topdown[r.lhs].append(r)


            # self.ruledict[eval.__name__] = r
            return eval

        return decorate




class EarleyItem:
    def __init__(self, rule, startpos, strpos, dotpos):
        self.rule = rule
        self.startpos = startpos
        self.strpos = strpos
        self.dotpos = dotpos
        self.backpointers = None

    def __str__(self):
        rhss = []
        for i, sym in enumerate(self.rule.rhs):
            if i == self.dotpos:
                rhss.append("*")
            rhss.append(str(sym))

        if self.dotpos == len(self.rule.rhs):
            rhss.append("*")

        return f"[{self.startpos}:{self.strpos} {self.rule.lhs} -> {' '.join(rhss)}]"

    def __repr__(self):
        return str(self)

    def next_rhs(self):
        return self.rule.rhs[self.dotpos]

    def is_complete(self):
        return self.dotpos == len(self.rule.rhs)

    def __eq__(self, other):
        if not isinstance(other, EarleyItem):
            return False

        return (self.rule, self.startpos, self.strpos, self.dotpos) == (other.rule, other.startpos, other.strpos, other.dotpos)

    def __hash__(self):
        return 3*hash(self.rule) + 51*hash(self.startpos) + 79*hash(self.strpos) + 139*hash(self.dotpos)

    def set_backpointers(self, backpointers):
        self.backpointers = backpointers


class EarleyParser:
    def __init__(self, grammar):
        self.grammar = grammar
        self.startsym = Nonterminal("S")


    def parse(self, tokens, startsym=None):
        agenda = Queue()
        chart = defaultdict(set)
        string_length = len(tokens)

        if startsym is None:
            startsym = self.startsym

        # initialize agenda with productions of start symbol
        for rule in self.grammar.topdown[startsym]:
            self._make_item(rule, 0, 0, 0, agenda, chart)

        # Loop over agenda, adding new items to agenda and chart.
        # If a goal item is found, evaluate it and return immediately.
        while not agenda.empty():
            item = agenda.get() # type: EarleyItem
            # print(f"\npop: {item}")

            if item.is_complete():
                # COMPLETE
                # print("  complete")
                for partner_item in chart[(item.startpos, item.rule.lhs)]:
                    new_item = self._make_item(partner_item.rule, partner_item.startpos, item.strpos, partner_item.dotpos+1, agenda, chart)
                    new_item.set_backpointers([partner_item, item]) # left bp: functor; right bp: complete argument

                    if self._is_goal_item(new_item, startsym, string_length):
                        return self._evaluate(new_item)

            else:
                next_sym = item.next_rhs()

                if isinstance(next_sym, Terminal):
                    # SCAN
                    # print("  scan")
                    if item.strpos < len(tokens) and next_sym.sym == tokens[item.strpos]:
                        new_item = self._make_item(item.rule, item.startpos, item.strpos+1, item.dotpos+1, agenda, chart)
                        if self._is_goal_item(new_item, startsym, string_length):
                            return self._evaluate(new_item)

                else:
                    # PREDICT
                    # print("  predict")
                    for rule in self.grammar.topdown[item.next_rhs()]:
                        new_item = self._make_item(rule, item.strpos, item.strpos, 0, agenda, chart)
                        if self._is_goal_item(new_item, startsym, string_length):
                            return self._evaluate(new_item)

        # No goal item found => no parse trees exist.
        return None

    def _is_goal_item(self, item:EarleyItem, startsym, string_length):
        return item.is_complete() and item.rule.lhs == startsym and item.startpos == 0 and item.strpos == string_length


    def _evaluate(self, item:EarleyItem):
        # print(f"evaluate: {item}")

        assert item.is_complete()
        children = []

        it = item
        while it.backpointers is not None:
            # Right backpointer was the complete premise of a Complete step.
            # Evaluate it recursively and add value to "children" list.
            right_child = it.backpointers[1]
            assert right_child.is_complete()
            val = self._evaluate(right_child)
            children.append(val)

            # Left backpointer was the item in which the dot was moved all
            # the way through the rule. Iterate until we reach A -> * \beta,
            # which has no backpointers because it was created by Predict
            # and not by Complete.
            it = it.backpointers[0]

        children.reverse()
        ret = item.rule.eval(*children)

        return ret


    def _make_item(self, rule, startpos, strpos, dotpos, agenda, chart):
        item = EarleyItem(rule, startpos, strpos, dotpos)
        # print(f"  -> {item}")

        # Check if item is known. If yes, return the new item.
        # The parser may add backpointers to it, but then the new
        # item will just get forgotten because it is not added
        # to the chart.
        if item.is_complete():
            if item in chart["complete_items"]:
                # print("     (known)")
                return item
        else:
            next = item.next_rhs()
            if item in chart[(strpos, next)]:
                # print("     (known)")
                return item

        # add item to chart
        if item.is_complete():
            chart["complete_items"].add(item)
        else:
            chart[(strpos,next)].add(item)

        # add item to agenda
        agenda.put(item)
        # print("     (added)")

        return item
