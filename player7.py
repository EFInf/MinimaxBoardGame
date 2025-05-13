def move7(players, loot):
    """
    Spieler 7 bleibt stehen und gibt seine aktuellen Koordinaten zurück.
    :param players: Liste der aktuellen Spielerkoordinaten [(r, c), ...]
    :param loot: Liste der Loot-Koordinaten (wird hier nicht verwendet)
    :return: Tuple (r, c) mit der neuen Position (gleich altem Wert)
    """
    # players[6] entspricht den Koordinaten von Spieler7
    return tuple(players[6])
