def move6(players, stars):
    """
    players: list of (r, c) current positions for all 6 players
    stars: list of (r, c) star positions
    return: (r, c) new position for player 6 (max 1 orthogonal step or stay)
    """

    r, c = players[5]

    closest_star = None
    closest_mandist = 10000
    for star in stars:
        sr, sc = star
        d = abs(sc-c)+abs(sr-r)
        if d<closest_mandist:
            closest_mandist = d
            closest_star = star
    sr, sc = closest_star
    if c<sc:
        return (r, c+1)
    elif c>sc:
        return (r, c-1)
    elif r<sr:
        return (r+1, c)
    else:
        return (r-1, c)
