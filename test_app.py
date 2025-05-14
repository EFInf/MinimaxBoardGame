import random
import importlib
from flask import Flask, render_template, request, jsonify
import concurrent.futures

app = Flask(__name__)

nb_player = 7

# Poll von workers processes, um die Moves auszuführen
_executor = concurrent.futures.ProcessPoolExecutor(max_workers=7)

# Globale Spielerscores
scores = [0] * 7

# Versuche, Spieler-Module zu importieren
move_functions = []
for i in range(1, 8):
    module_name = f"player{i}"
    try:
        mod = importlib.import_module(module_name)
        fn = getattr(mod, f"move{i}")
        move_functions.append(fn)
    except Exception:
        # Fallback
        def stay(players, loot, idx=i-1):
            return players[idx]
        move_functions.append(stay)

def generate_initial_positions():
    """Erzeugt zufällig nb_player Spieler-Positionen (Manhattan ≥5)
    und 50 Loot-Positionen (Manhattan >4 zu allen Spielern)."""
    players = []
    while len(players) < nb_player:
        r, c = random.randint(0, 19), random.randint(0, 29)
        if all(abs(r - pr) + abs(c - pc) >= 5 for pr, pc in players):
            players.append((r, c))

    loot = []
    while len(loot) < 50:
        r, c = random.randint(0, 19), random.randint(0, 29)
        if (r, c) not in loot and all(abs(r - pr) + abs(c - pc) > 4 for pr, pc in players):
            loot.append((r, c))

    return players, loot

@app.route('/')
def index():
    # Seite lädt nur das HTML/JS – Startpositionen holt das Frontend später
    return render_template('index.html')

@app.route('/start/<int:nbplayer>')
def start(nbplayer):
    # nbplayer wird aktuell ignoriert (immer 7)
    players, loot = generate_initial_positions()
    # Reset Scores
    global scores
    scores = [0] * nbplayer
    return jsonify(players=players, loot=loot, scores=scores)

@app.route('/move', methods=['POST'])
def move():
    global scores
    data    = request.get_json()
    players = data.get('player', [])
    loot    = data.get('loot', [])

    proposed = []
    # Jede Funktion movei() in einem separaten Prozess mit timeout=1s
    for idx, fn in enumerate(move_functions):
        try:
            future    = _executor.submit(fn, players, loot)
            new_coord = future.result(timeout=1.0)
        except concurrent.futures.TimeoutError:
            # 1 Sekunde überschrieten
            new_coord = players[idx]
        except Exception:
            # Fehler in der Funktion
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

    conflict = True
    while conflict:
        conflict = False

        # Zähle Vorkommen
        counts = {}
        for pos in final:
            counts[pos] = counts.get(pos, 0) + 1
        # Rücksetzen bei Konflikten
        for idx, pos in enumerate(final):
            if counts[pos] > 1:
                final[idx] = tuple(players[idx])
                conflict = True

    # Score updaten
    remaining_loot = set(map(tuple, loot))
    for idx, new in enumerate(final):
        if new in remaining_loot:
            scores[idx] += 1
    # Rückgabe der neuen Koordinaten (und Scores)
    print(final, scores)
    return jsonify(coord=final, scores=scores)

if __name__ == '__main__':
    app.run(debug=True)
