behavior GetBallPossession():
    """
    Move to the ball and get possession of it. 
    """
    pass

behavior Idle()
    """
    Wait and do nothing.
    """
    pass

behavior Pass(target)
    """
    Pass the ball to the target.

    Input Argument:
        - target (str): The target player name to pass the ball to.
    """
    pass

behavior MoveTo(λ_dest):

    """
    Move to a destination which satisfies the given predicate function.
    The behavior terminates when the player executing this behavior is within 0.5 meter of the destination that
    satisfies the given predicate function, λ_dest.

    Input Argument:
        - λ_dest: A predicate function that the destination must satisfy.
    """
    pass