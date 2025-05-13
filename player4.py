def move4(players, loot):
    """
    Spieler 4 bleibt stehen und gibt seine aktuellen Koordinaten zurück.
    :param players: Liste der aktuellen Spielerkoordinaten [(r, c), ...]
    :param loot: Liste der Loot-Koordinaten (wird hier nicht verwendet)
    :return: Tuple (r, c) mit der neuen Position (gleich altem Wert)
    """
    # players[3] entspricht den Koordinaten von Spieler4
    return tuple(players[3])
