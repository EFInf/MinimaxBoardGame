from flask import Flask, render_template, request, jsonify
import importlib

app = Flask(__name__)

# Globale Spielerscores
scores = [0] * 7  # Index 0 für Spieler 1, ...

# Versuche, Spieler-Module zu importieren
move_functions = []
for i in range(1, 8):
    module_name = f"player{i}"
    try:
        mod = importlib.import_module(module_name)
        move_fn = getattr(mod, f"move{i}", None)
        if callable(move_fn):
            move_functions.append(move_fn)
        else:
            raise AttributeError
    except (ImportError, AttributeError, SyntaxError) as e:
        # Fehlendes oder fehlerhaftes Modul; stattdessen Bleibt-Spieler-Funktion
        def stay_in_place(players, loot, idx=i-1):
            return players[idx]
        move_functions.append(stay_in_place)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/move', methods=['POST'])
def move():
    global scores
    data = request.get_json()
    players = data.get('player', [])
    loot = data.get('loot', [])

    proposed = []
    # Spielerzug vorschlagen
    for idx, fn in enumerate(move_functions):
        try:
            new_coord = fn(players, loot)
        except Exception:
            # Fehler in KI-Funktion: bleibe stehen
            new_coord = players[idx]
        proposed.append(tuple(new_coord))

    # Validierung: angrenzend oder gleich
    validated = []
    for idx, (old, new) in enumerate(zip(players, proposed)):
        r0, c0 = old
        r1, c1 = new
        dr = abs(r1 - r0)
        dc = abs(c1 - c0)
        # erlaubte Züge: keine Diagonale, max 1 Schritt
        if dr + dc <= 1:
            # innerhalb Grenzen?
            if 0 <= r1 < 20 and 0 <= c1 < 30:
                validated.append((r1, c1))
                continue
        # ansonsten bleibe
        validated.append((r0, c0))

    # Kollision: zwei Spieler auf gleicher Zielzelle
    final = list(validated)
    # Zähle Vorkommen
    counts = {}
    for pos in validated:
        counts[pos] = counts.get(pos, 0) + 1
    # Rücksetzen bei Konflikten
    for idx, pos in enumerate(validated):
        if counts[pos] > 1:
            final[idx] = tuple(players[idx])

    # Kollision mit stehenden Spielern
    for idx, new in enumerate(final):
        if new == players[idx]:
            continue  # selbst blieb stehen
        # prüfe, ob jemand anderes steht
        for jdx, other_old in enumerate(players):
            if jdx != idx and new == other_old and final[jdx] == other_old:
                final[idx] = players[idx]
                break

    # Score updaten
    remaining_loot = set(map(tuple, loot))
    for idx, new in enumerate(final):
        if new in remaining_loot:
            scores[idx] += 1
    # Rückgabe der neuen Koordinaten (und Scores)
    return jsonify(coord=final, scores=scores)

if __name__ == '__main__':
    app.run(debug=True)
