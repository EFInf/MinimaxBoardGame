def move3(players, loot):
    """
    Spieler 3 bleibt stehen und gibt seine aktuellen Koordinaten zurück.
    :param players: Liste der aktuellen Spielerkoordinaten [(r, c), ...]
    :param loot: Liste der Loot-Koordinaten (wird hier nicht verwendet)
    :return: Tuple (r, c) mit der neuen Position (gleich altem Wert)
    """
    # players[2] entspricht den Koordinaten von Spieler3
    return tuple(players[2])
