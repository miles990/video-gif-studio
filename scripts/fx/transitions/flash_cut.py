from ..core import transition

@transition()
def flash_cut(a, b, p, ctx):
    """White peak at the cut, with original endpoints and source coverage."""
    result = (a if p<.5 else b).copy()
    amount = max(0,1-abs(2*p-1))**2
    result[...,:3] += (1-result[...,:3])*amount
    return result
