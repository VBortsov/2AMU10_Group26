#  (C) Copyright Wieger Wesselink 2021. Distributed under the GPL-3.0-or-later
#  Software License, (See accompanying file LICENSE or copy at
#  https://www.gnu.org/licenses/gpl-3.0.txt)

from copy import copy
from math import inf
from operator import itemgetter

from competitive_sudoku.sudoku import GameState, Move, SudokuBoard
import competitive_sudoku.sudokuai


class SudokuAI(competitive_sudoku.sudokuai.SudokuAI):
    """
    Sudoku AI that computes a move for a given sudoku configuration.
    """

    def __init__(self):
        super().__init__()

    def generate_moves(self, game_state: GameState) -> list[Move]:
        return [move for move, _ in self._scored_moves(game_state)]

    def _scored_moves(self, game_state: GameState):
        board = game_state.board
        N = board.N
        m = board.m
        n = board.n

        if game_state.occupied_squares() is None and not game_state.is_classic_game():
            game_state = copy(game_state)
            game_state.occupied_squares1 = game_state.occupied_squares1 or []
            game_state.occupied_squares2 = game_state.occupied_squares2 or []

        allowed_squares = game_state.player_squares()
        if allowed_squares is not None:
            allowed_squares = set(allowed_squares)
        taboo_moves = {(move.square, move.value) for move in game_state.taboo_moves}

        for row in range(N):
            for col in range(N):
                square = (row, col)
                if allowed_squares is not None and square not in allowed_squares:
                    continue
                if board.get(square) != SudokuBoard.empty:
                    continue

                row_values = {
                    board.get((row, c))
                    for c in range(N)
                }

                column_values = {
                    board.get((r, col))
                    for r in range(N)
                }

                block_row = (row // m) * m
                block_col = (col // n) * n
                block_values = {
                    board.get((r, c))
                    for r in range(block_row, block_row + m)
                    for c in range(block_col, block_col + n)
                }

                regions = (row_values, column_values, block_values)
                for values in regions:
                    values.discard(SudokuBoard.empty)
                completed = sum(len(values) == N - 1 for values in regions)
                points = (0, 1, 3, 7)[completed]
                used_values = row_values | column_values | block_values

                for value in range(1, N + 1):
                    if value in used_values or (square, value) in taboo_moves:
                        continue
                    yield Move(square, value), points

    def evaluation_function_difference(self, game_state: GameState, ai_pl: int) -> float:
        scores = game_state.scores
        opponent = 3 - ai_pl
        return scores[ai_pl - 1] - scores[opponent - 1]

    def count_accessible_squares(self, game_state: GameState, player: int) -> int:
        board = game_state.board
        N = board.N
        if player == 1:
            occupied = game_state.occupied_squares1
            starting_squares = game_state.allowed_squares1
        else:
            occupied = game_state.occupied_squares2
            starting_squares = game_state.allowed_squares2
        if starting_squares is None:
            return board.squares.count(SudokuBoard.empty)

        starting_squares = set(starting_squares)
        occupied = occupied or ()
        count = 0
        for row in range(N):
            for col in range(N):
                if board.get((row, col)) != SudokuBoard.empty:
                    continue
                if (row, col) in starting_squares:
                    count += 1
                    continue
                for r, c in occupied:
                    if abs(row - r) <= 1 and abs(col - c) <= 1:
                        count += 1
                        break

        return count

    def evaluation_function(self, game_state: GameState, ai_player: int) -> float:
        opponent = 3 - ai_player
        score_diff = self.evaluation_function_difference(game_state, ai_player)
        mobility_ai = self.count_accessible_squares(game_state, ai_player)
        mobility_opponent = self.count_accessible_squares(game_state, opponent)
        mobility_diff = mobility_ai - mobility_opponent
        return score_diff + 0.1 * mobility_diff

    def _alpha_beta(self, game_state, depth, alpha, beta, moves=None, passed=False):
        player = game_state.current_player
        board = game_state.board
        if SudokuBoard.empty not in board.squares:
            return self.evaluation_function_difference(game_state, player), None
        if depth == 0:
            return self.evaluation_function(game_state, player), None

        if moves is None:
            moves = sorted(self._scored_moves(game_state), key=itemgetter(1), reverse=True)
        if not moves:
            if passed:
                return self.evaluation_function_difference(game_state, player), None
            game_state.current_player = 3 - player
            value, _ = self._alpha_beta(game_state, depth, -beta, -alpha, passed=True)
            game_state.current_player = player
            return -value, None

        occupied = game_state.occupied_squares()
        game_state.current_player = 3 - player
        best_score = -inf
        best_move = None
        for choice in moves:
            move, points = choice
            board.put(move.square, move.value)
            game_state.scores[player - 1] += points
            occupied.append(move.square)

            value, _ = self._alpha_beta(game_state, depth - 1, -beta, -alpha)
            value = -value

            occupied.pop()
            game_state.scores[player - 1] -= points
            board.put(move.square, SudokuBoard.empty)

            if value > best_score:
                best_score = value
                best_move = choice
            alpha = max(alpha, value)
            if alpha >= beta:
                break

        game_state.current_player = player
        return best_score, best_move

    def compute_best_move(self, game_state: GameState) -> None:
        position = copy(game_state)
        position.board = copy(game_state.board)
        position.board.squares = game_state.board.squares.copy()
        position.scores = game_state.scores.copy()
        position.occupied_squares1 = list(game_state.occupied_squares1 or ())
        position.occupied_squares2 = list(game_state.occupied_squares2 or ())

        candidates = self._scored_moves(position)
        best = next(candidates, None)
        if best is None:
            return

        self.propose_move(best[0])
        moves = [best, *candidates]
        if len(moves) == 1:
            return

        moves.sort(key=itemgetter(1), reverse=True)
        remaining = position.board.squares.count(SudokuBoard.empty)
        for depth in range(1, remaining + 1):
            _, choice = self._alpha_beta(position, depth, -inf, inf, moves=moves)
            if choice != best:
                best = choice
                self.propose_move(best[0])
            if choice != moves[0]:
                moves.remove(choice)
                moves.insert(0, choice)
