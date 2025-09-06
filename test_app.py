# ---------- test_app.py (server) ----------
import random
import importlib
import concurrent.futures
import uuid
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# --- Game configuration ---
DEFAULT_NB_PLAYERS = 6  # requirement: exactly 6 players by default
ROWS, COLS = 20, 30
STAR_COUNT = 50

# Worker pool to safely run user move functions with a timeout
_executor = concurrent.futures.ProcessPoolExecutor(max_workers=DEFAULT_NB_PLAYERS)

# Per-game state (allows many simultaneous viewers/games)
# game_id -> {"scores": [...], "nb_players": int}
GAMES = {}

# --- Load player move functions (player1.py .. player6.py). Fallback: stay in place ---
move_functions = []
for i in range(1, DEFAULT_NB_PLAYERS + 1):
    module_name = f"player{i}"
    try:
        mod = importlib.import_module(module_name)
        fn = getattr(mod, f"move{i}")
        move_functions.append(fn)
    except Exception:
        # Fallback: keep current position
        def stay(players, stars, idx=i - 1):
            return players[idx]
        move_functions.append(stay)


def generate_initial_positions(nb_players: int):
    """Create random player positions (pairwise Manhattan >=5) and STAR_COUNT star tiles
    that start at Manhattan >4 from all players.
    """
    players = []
    while len(players) < nb_players:
        r, c = random.randint(0, ROWS - 1), random.randint(0, COLS - 1)
        if all(abs(r - pr) + abs(c - pc) >= 5 for pr, pc in players):
            players.append((r, c))

    stars = []
    while len(stars) < STAR_COUNT:
        r, c = random.randint(0, ROWS - 1), random.randint(0, COLS - 1)
        if (r, c) not in stars and all(abs(r - pr) + abs(c - pc) > 4 for pr, pc in players):
            stars.append((r, c))

    return players, stars


@app.route("/")
def index():
    # Serves index.html from the template folder
    return render_template("index.html")


@app.route("/start", methods=["POST"])  # changed to POST with JSON
def start():
    """Start a new game instance and return its game_id and initial state.
    Allows many concurrent games (multi-viewers)."""
    payload = request.get_json(silent=True) or {}
    nb_players = int(payload.get("nbplayers", DEFAULT_NB_PLAYERS))
    # Force exactly 6 players, as requested
    nb_players = DEFAULT_NB_PLAYERS

    players, stars = generate_initial_positions(nb_players)

    game_id = uuid.uuid4().hex
    GAMES[game_id] = {
        "scores": [0] * nb_players,
        "nb_players": nb_players,
    }
    return jsonify(game_id=game_id, players=players, stars=stars, scores=GAMES[game_id]["scores"])


@app.route("/move", methods=["POST"])
def move():
    """Compute one simulation step with tie-breaking and occupancy rules.

    Rules:
    1) Exactly 6 players.
    2) If two or more players target the same tile, pick one at random; others stay.
    3) A player cannot move into an occupied tile unless the current occupant also moves away this turn.
       (Swaps are allowed if both move.)
    """
    data = request.get_json() or {}
    game_id = data.get("game_id")
    if not game_id or game_id not in GAMES:
        return jsonify(error="invalid game_id"), 400

    players = [tuple(p) for p in data.get("players", [])]
    stars = [tuple(l) for l in data.get("stars", [])]

    # 1) Ask each move function for a proposed move, with timeout and validation
    proposed = []
    for idx, fn in enumerate(move_functions):
        try:
            future = _executor.submit(fn, players, stars)
            new_coord = future.result(timeout=1.0)
        except Exception:
            new_coord = players[idx]
        # Validate: single orthogonal step or stay; inside bounds
        r0, c0 = players[idx]
        r1, c1 = new_coord if isinstance(new_coord, (list, tuple)) and len(new_coord) == 2 else (r0, c0)
        if abs(r1 - r0) + abs(c1 - c0) <= 1 and 0 <= r1 < ROWS and 0 <= c1 < COLS:
            proposed.append((r1, c1))
        else:
            proposed.append((r0, c0))

    old_positions = players[:]  # before movement

    # 2) Resolve same-target conflicts randomly (only one winner per target)
    target_to_indices = {}
    for i, tgt in enumerate(proposed):
        target_to_indices.setdefault(tgt, []).append(i)

    winners = set()  # indices allowed to move to their target after tie-break
    for tgt, idxs in target_to_indices.items():
        if len(idxs) == 1:
            winners.add(idxs[0])
        else:
            # More than one player wants this tile: random winner, others stay
            winner = random.choice(idxs)
            winners.add(winner)
            # non-winners implicitly stay because they won't be in winners set

    # 3) Enforce occupancy rule: cannot enter a tile if its current occupant stays
    #    (i.e., occupant is NOT moving away after tie-break)
    will_move = [False] * len(proposed)
    for i in range(len(proposed)):
        will_move[i] = (i in winners) and (proposed[i] != old_positions[i])

    # Determine, for each old tile, whether its occupant vacates it
    vacating = {old_positions[i]: will_move[i] for i in range(len(old_positions))}

    final_positions = list(old_positions)
    for i in range(len(proposed)):
        if not will_move[i]:
            continue  # stays in place
        target = proposed[i]
        # If target equals some player's old position and that player is NOT vacating, block the move
        if target in vacating and not vacating[target]:
            continue  # blocked: stays at old position
        # Otherwise the move is allowed
        final_positions[i] = target

    # 4) Update score if landing on stars (star removal is handled on client)
    scores = GAMES[game_id]["scores"]
    star_set = set(stars)
    for idx, pos in enumerate(final_positions):
        if pos in star_set:
            scores[idx] += 1

    return jsonify(coord=final_positions, scores=scores)


if __name__ == "__main__":
    app.run(debug=True)
