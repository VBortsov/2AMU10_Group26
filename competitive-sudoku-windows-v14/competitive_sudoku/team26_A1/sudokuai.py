from math import inf
from operator import itemgetter

from competitive_sudoku.sudoku import GameState, Move, SudokuBoard
from competitive_sudoku.sudokuai import SudokuAI as BaseSudokuAI


POINTS = (0, 1, 3, 7)


class _Search:
    def __init__(self, game_state):
        board = game_state.board
        size = board.N
        blocks_per_row = size // board.n
        self.all_digits = (1 << size) - 1
        self.almost_full = size - 1
        self.empty = 0
        self.regions = []
        self.neighbors = []
        self.region_digits = [0] * (3 * size)
        self.taboo_digits = [0] * (size * size)

        for index, value in enumerate(board.squares):
            row, col = board.index2square(index)
            block = (row // board.m) * blocks_per_row + col // board.n
            regions = (row, size + col, 2 * size + block)
            self.regions.append(regions)
            self.neighbors.append(sum(
                1 << board.square2index((r, c))
                for r in range(max(0, row - 1), min(size, row + 2))
                for c in range(max(0, col - 1), min(size, col + 2))
                if (r, c) != (row, col)
            ))

            if value == SudokuBoard.empty:
                self.empty |= 1 << index
            else:
                for region in regions:
                    self.region_digits[region] |= 1 << (value - 1)

        for move in game_state.taboo_moves:
            self.taboo_digits[board.square2index(move.square)] |= 1 << (move.value - 1)

        self.allowed = [
            self._allowed_mask(board, game_state.allowed_squares1, game_state.occupied_squares1),
            self._allowed_mask(board, game_state.allowed_squares2, game_state.occupied_squares2),
        ]

    def _allowed_mask(self, board, starting_squares, occupied_squares):
        if starting_squares is None:
            return self.empty
        allowed = 0
        for square in starting_squares:
            allowed |= 1 << board.square2index(square)
        for square in occupied_squares or ():
            allowed |= self.neighbors[board.square2index(square)]
        return allowed

    def legal_moves(self, player):
        squares = self.empty & self.allowed[player]
        while squares:
            square = squares & -squares
            squares ^= square
            index = square.bit_length() - 1
            row, col, block = self.regions[index]
            row_digits = self.region_digits[row]
            col_digits = self.region_digits[col]
            block_digits = self.region_digits[block]
            unavailable = row_digits | col_digits | block_digits | self.taboo_digits[index]
            digits = self.all_digits & ~unavailable
            completed = ((row_digits.bit_count() == self.almost_full)
                         + (col_digits.bit_count() == self.almost_full)
                         + (block_digits.bit_count() == self.almost_full))
            while digits:
                digit = digits & -digits
                digits ^= digit
                yield index, digit, POINTS[completed]

    def play(self, player, index, digit):
        previous_allowed = self.allowed[player]
        self.allowed[player] |= self.neighbors[index]
        self.empty ^= 1 << index
        for region in self.regions[index]:
            self.region_digits[region] |= digit
        return previous_allowed

    def undo(self, player, index, digit, previous_allowed):
        self.allowed[player] = previous_allowed
        self.empty |= 1 << index
        for region in self.regions[index]:
            self.region_digits[region] ^= digit

    def alpha_beta(self, player, score, depth, alpha, beta, moves=None, passed=False):
        if depth == 0 or not self.empty:
            return score, None

        if moves is None:
            moves = sorted(self.legal_moves(player), key=itemgetter(2), reverse=True)
        opponent = 1 - player
        if not moves:
            if passed:
                return score, None
            value, _ = self.alpha_beta(opponent, -score, depth, -beta, -alpha, passed=True)
            return -value, None

        best_score = -inf
        best_move = None
        for move in moves:
            index, digit, points = move
            previous_allowed = self.play(player, index, digit)
            value, _ = self.alpha_beta(opponent, -score - points, depth - 1, -beta, -alpha)
            self.undo(player, index, digit, previous_allowed)
            value = -value

            if value > best_score:
                best_score = value
                best_move = move
            alpha = max(alpha, value)
            if alpha >= beta:
                break

        return best_score, best_move


class SudokuAI(BaseSudokuAI):
    def compute_best_move(self, game_state: GameState) -> None:
        search = _Search(game_state)
        player = game_state.current_player - 1
        moves = search.legal_moves(player)
        best_move = next(moves, None)
        if best_move is None:
            return

        def propose(move):
            index, digit, _ = move
            self.propose_move(Move(game_state.board.index2square(index), digit.bit_length()))

        propose(best_move)
        root_moves = [best_move, *moves]
        if len(root_moves) == 1:
            return

        root_moves.sort(key=itemgetter(2), reverse=True)
        score = game_state.scores[player] - game_state.scores[1 - player]
        for depth in range(1, search.empty.bit_count() + 1):
            _, move = search.alpha_beta(player, score, depth, -inf, inf, moves=root_moves)
            if move != best_move:
                best_move = move
                propose(move)
            if move != root_moves[0]:
                root_moves.remove(move)
                root_moves.insert(0, move)
