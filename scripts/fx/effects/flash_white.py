from ..core import effect

@effect(amount='White mix, 0 identity, 1 white; alpha unchanged')
def flash_white(frame, t_ms, ctx, amount=1.0):
    """Beat accent with preserved coverage."""
    frame[..., :3] += (1-frame[..., :3])*amount
    return frame
