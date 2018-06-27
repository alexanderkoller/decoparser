
from decoparse import Grammar, EarleyParser

g = Grammar()


@g.rule("S -> NP VP")
def testfn(np, vp):
    return ["S", np, vp]

@g.rule("NP -> hans")
def hans():
    return ["hans"]

@g.rule("NP -> den elefanten")
def elef():
    return ["den elefanten"]

@g.rule("NP -> dem fernrohr")
def fernrohr():
    return ["dem fernrohr"]

@g.rule("PP -> mit NP")
def mit(np):
    return ("mit", np)

@g.rule("NP -> NP PP")
def nppp(np, pp):
    return ["NP", np, pp]

@g.rule("VP -> VP PP")
def vppp(vp, pp):
    return ["VP", vp, pp]

@g.rule("VP -> betrachtet NP")
def vp(np):
    return ["VP", "betrachtet", np]

@g.rule("VP -> schlaeft")
def schlaeft():
    return ["schlaeft"]

p = EarleyParser(g)
print(p.parse("hans betrachtet den elefanten mit dem fernrohr".split()))


