#  (C) Copyright Wieger Wesselink 2021. Distributed under the GPL-3.0-or-later
#  Software License, (See accompanying file LICENSE or copy at
#  https://www.gnu.org/licenses/gpl-3.0.txt)

import random
import time
from competitive_sudoku.sudoku import GameState, Move, SudokuBoard, TabooMove
import competitive_sudoku.sudokuai


class SudokuAI(competitive_sudoku.sudokuai.SudokuAI):
    """
    Sudoku AI that computes a move for a given sudoku configuration.
    """

    def __init__(self):
        super().__init__()

    def generate_moves(self, game_state: GameState) -> list[Move]:
        board = game_state.board
        N = board.N
        m = board.m
        n = board.n

        allowed_squares = game_state.player_squares()
        moves = []

        for row in range (N):
            for col in range(N):
                square = (row, col)

                # None means all squares are accessible.
                # Skip squares the current player cannot access
                if allowed_squares is not None:
                    if square not in allowed_squares:
                        continue

                # skip squares that already contain a number.
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

                # Retrieve top-left square of this square's block
                block_row = (row // m) * m
                block_col = (col // n) * n

                # Collect values already present in the block
                block_values = {
                    board.get((r, c))
                    for r in range(block_row, block_row + m)
                    for c in range(block_col, block_col + n)
                }

                used_values = row_values | column_values | block_values
                
                for value in range(1, N+1):
                    if value in used_values:
                        # Reject row, column, or block duplicates.
                        continue
                    if TabooMove(square, value) in game_state.taboo_moves:
                        # Reject moves already declared taboo.
                        continue

                    moves.append(Move(square, value))

        return moves  
    #using difference
    def evaluation_function_difference(self, game_state:GameState, ai_pl:int) -> float:
        scores = game_state.scores
        opponent = 3- ai_pl
        return scores[ai_pl - 1] - scores[opponent - 1]

    #helper for evaluation function
    def count_accessible_squares(self, game_state: GameState, player:int) -> int:
        board = game_state.board
        N = board.N
        if player ==1:
            occupied = game_state.occupied_squares1
            starting_row = 0
        else:
            occupied = game_state.occupied_squares2
            starting_row = N-1
        count = 0

        for row in range(N):
            for col in range(N):
                if board.get((row, col)) != SudokuBoard.empty:
                    continue
                if row == starting_row:
                    count+=1
                    continue
                for r,c in occupied:
                    if abs(row - r) <=1 and abs(col - c) <=1:
                        count+=1
                        break

        return count

    #better function
    def evaluation_function(self, game_state: GameState, ai_player:int) -> float:
        opponent = 3 - ai_player
        score_diff = (game_state.scores[ai_player-1] - game_state.scores[opponent-1])
        mobility_ai = self.count_accessible_squares(game_state,ai_player)
        mobility_opponent = self.count_accessible_squares(game_state,opponent)
        mobility_diff = mobility_ai - mobility_opponent
        return score_diff + 0.1 * mobility_diff #0.1 can be adjusted



    # N.B. This is a very naive implementation.
    def compute_best_move(self, game_state: GameState) -> None:
        # N = game_state.board.N

        # # Check whether a cell is empty, a value in that cell is not taboo, and that cell is allowed
        # def possible(i, j, value):
        #     return game_state.board.get((i, j)) == SudokuBoard.empty \
        #            and not TabooMove((i, j), value) in game_state.taboo_moves \
        #                and (i, j) in game_state.player_squares()

        # all_moves = [Move((i, j), value) for i in range(N) for j in range(N)
        #              for value in range(1, N+1) if possible(i, j, value)]
        # move = random.choice(all_moves)
        # self.propose_move(move)
        # while True:
        #     time.sleep(0.2)
        #     self.propose_move(random.choice(all_moves))

        moves = self.generate_moves(game_state)

        if not moves:
            return

        self.propose_move(random.choice(moves))

