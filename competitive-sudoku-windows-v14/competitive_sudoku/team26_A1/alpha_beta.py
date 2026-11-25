POINTS = (0, 1, 3, 7)
INFINITY = float("inf")


def _position_for_player(game_state, player):
    return type(game_state)(
        initial_board=game_state.initial_board,
        board=game_state.board,
        taboo_moves=game_state.taboo_moves,
        moves=game_state.moves,
        scores=game_state.scores,
        current_player=player,
        allowed_squares1=game_state.allowed_squares1,
        allowed_squares2=game_state.allowed_squares2,
        occupied_squares1=game_state.occupied_squares1 or [],
        occupied_squares2=game_state.occupied_squares2 or [],
    )


def count_accessible_squares(game_state, player: int) -> int:
    position = _position_for_player(game_state, player)
    squares = position.player_squares()
    if squares is None:
        return position.board.squares.count(position.board.empty)
    return len(squares)


def _ordered_moves(ai, position, moves=None):
    if moves is None:
        moves = ai.generate_moves(position)
    if not moves:
        return []

    board = position.board
    blocks_per_row = board.N // board.n
    row_empty = [0] * board.N
    col_empty = [0] * board.N
    block_empty = [0] * board.N
    for index, value in enumerate(board.squares):
        if value == board.empty:
            row, col = board.index2square(index)
            block = (row // board.m) * blocks_per_row + col // board.n
            row_empty[row] += 1
            col_empty[col] += 1
            block_empty[block] += 1

    points_by_square = {}
    for move in moves:
        if move.square not in points_by_square:
            row, col = move.square
            block = (row // board.m) * blocks_per_row + col // board.n
            completed = (row_empty[row] == 1) + (col_empty[col] == 1) + (block_empty[block] == 1)
            points_by_square[move.square] = POINTS[completed]

    scored = [(move, points_by_square[move.square]) for move in moves]
    return sorted(scored, key=lambda choice: choice[1], reverse=True)


def _alpha_beta(ai, position, depth, alpha, beta, moves=None, passed=False):
    player = position.current_player
    board = position.board
    if board.empty not in board.squares:
        return ai.evaluation_function_difference(position, player), None
    if depth == 0:
        return ai.evaluation_function(position, player), None

    if moves is None:
        moves = _ordered_moves(ai, position)
    if not moves:
        if passed:
            return ai.evaluation_function_difference(position, player), None
        position.current_player = 3 - player
        value, _ = _alpha_beta(ai, position, depth, -beta, -alpha, passed=True)
        position.current_player = player
        return -value, None
    occupied = position.occupied_squares()
    position.current_player = 3 - player
    best_value = -INFINITY
    best_choice = None
    for choice in moves:
        move, points = choice
        board.put(move.square, move.value)
        position.scores[player - 1] += points
        occupied.append(move.square)

        value, _ = _alpha_beta(ai, position, depth - 1, -beta, -alpha)
        value = -value

        occupied.pop()
        position.scores[player - 1] -= points
        board.put(move.square, board.empty)

        if value > best_value:
            best_value = value
            best_choice = choice
        alpha = max(alpha, value)
        if alpha >= beta:
            break

    position.current_player = player
    return best_value, best_choice


def refine_best_move(ai, game_state, moves) -> None:
    if len(moves) <= 1:
        return
    position = _position_for_player(game_state, game_state.current_player)
    board = game_state.board
    position.board = type(board)(board.m, board.n)
    position.board.squares = board.squares.copy()
    position.scores = game_state.scores.copy()
    position.occupied_squares1 = position.occupied_squares1.copy()
    position.occupied_squares2 = position.occupied_squares2.copy()
    choices = _ordered_moves(ai, position, moves)
    best_choice = None
    remaining = board.squares.count(board.empty)
    for depth in range(1, remaining + 1):
        _, choice = _alpha_beta(ai, position, depth, -INFINITY, INFINITY, moves=choices)
        if choice != best_choice:
            ai.propose_move(choice[0])
            best_choice = choice
        if choice != choices[0]:
            choices.remove(choice)
            choices.insert(0, choice)
