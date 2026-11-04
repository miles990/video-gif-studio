from ..core import transition, premultiply, straight

@transition()
def crossfade(a, b, p, ctx):
    """Coverage-correct premultiplied dissolve."""
    if p<=0: return a
    if p>=1: return b
    return straight(premultiply(a)*(1-p)+premultiply(b)*p)
