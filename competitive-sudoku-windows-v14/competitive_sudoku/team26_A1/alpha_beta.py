from copy import copy
from math import inf
from operator import itemgetter

from competitive_sudoku.sudoku import GameState, SudokuBoard


POINTS = (0, 1, 3, 7)


def count_accessible_squares(game_state: GameState, player: int) -> int:
    position = copy(game_state)
    position.current_player = player
    position.occupied_squares1 = game_state.occupied_squares1 or []
    position.occupied_squares2 = game_state.occupied_squares2 or []
    squares = position.player_squares()
    if squares is None:
        return position.board.squares.count(SudokuBoard.empty)
    return len(squares)


def _first_move(ai, position):
    squares = position.player_squares()
    if squares is None:
        board = position.board
        squares = (
            board.index2square(index)
            for index, value in enumerate(board.squares)
            if value == SudokuBoard.empty
        )

    view = copy(position)
    view.occupied_squares1 = []
    view.occupied_squares2 = []
    for square in squares:
        view.allowed_squares1 = view.allowed_squares2 = [square]
        moves = ai.generate_moves(view)
        if moves:
            return moves[0]
    return None


def _ordered_moves(ai, position):
    moves = ai.generate_moves(position)
    if not moves:
        return []

    board = position.board
    blocks_per_row = board.N // board.n
    row_empty = [0] * board.N
    col_empty = [0] * board.N
    block_empty = [0] * board.N
    for index, value in enumerate(board.squares):
        if value == SudokuBoard.empty:
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
    return sorted(scored, key=itemgetter(1), reverse=True)


def _alpha_beta(ai, position, depth, alpha, beta, moves=None, passed=False):
    player = position.current_player
    board = position.board
    if SudokuBoard.empty not in board.squares:
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
    best_value = -inf
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
        board.put(move.square, SudokuBoard.empty)

        if value > best_value:
            best_value = value
            best_choice = choice
        alpha = max(alpha, value)
        if alpha >= beta:
            break

    position.current_player = player
    return best_value, best_choice


def search_best_move(ai, game_state: GameState) -> None:
    position = copy(game_state)
    position.board = copy(game_state.board)
    position.board.squares = game_state.board.squares.copy()
    position.scores = game_state.scores.copy()
    position.occupied_squares1 = list(game_state.occupied_squares1 or ())
    position.occupied_squares2 = list(game_state.occupied_squares2 or ())

    best_move = _first_move(ai, position)
    if best_move is None:
        return
    ai.propose_move(best_move)

    moves = _ordered_moves(ai, position)
    if len(moves) <= 1:
        return

    remaining = position.board.squares.count(SudokuBoard.empty)
    for depth in range(1, remaining + 1):
        _, choice = _alpha_beta(ai, position, depth, -inf, inf, moves=moves)
        move, _ = choice
        if move != best_move:
            ai.propose_move(move)
            best_move = move
        if choice != moves[0]:
            moves.remove(choice)
            moves.insert(0, choice)
