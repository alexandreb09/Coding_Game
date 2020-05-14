import sys
import numpy as np
import copy


WATER = "X"
FREE = "."
DEST = "H"
LEFT, RIGHT, UP, DOWN = "LEFT", "RIGHT", "UP", "DOWN"
MOVE = {
    LEFT: "<",
    RIGHT: ">",
    UP: "^",
    DOWN: "v"
}

# Used for switching between local code and coding game tests
file = sys.stdout
# file = sys.stderr


#####################################################################
#                           WORKFLOW                                #
# - Load grid and store it in a numpy 2D matrix                     #
# - Create a Solution instance                                      #
# - Fill the solution with all the balls on the grid                #
# - Start reduction process:                                        #    
#     - For all balls: search all possible movement leading         #
#       to a hole (without taking into account the others           #
#       balls)                                                      #
#     - From this set of movements: identify obvious moves          #
#       using two approaches:                                       #
#           - All balls that have only one possible path to reach   #
#             a hole                                                #
#           - All hole that can be reached by only one ball         #
#     - Using these 2 methods, apply all obvious move               #
#     - Update the solution state (is solution founded)             #
#                                                                   #
# IF solution is found: nothing more                                #
# ELSE: there are no more possible obvious movement (here comes     #
#       the darkside...                                             #
#     - Select one ball                                             #
#     - For all associated paths to this ball:                      #
#           - Apply the path on this ball                           #
#           - Apply reduction                                       #
#           - If solution found: return solution                    #
#           - Else: recursively explore solution                    #
#                                                                   #
##################################################################### 


class Ball:
    id_counter = 0
    dirs = []

    def __init__(self, x, y, c):
        Ball.id_counter += 1
        self.x = x
        self.y = y
        self.c = c
        self.id = Ball.id_counter

    def __str__(self):
        return "Ball {}: \n\tx : {}\n\ty : {}\n\tc : {}\n\tdirs: {}".format(self.id, self.x, self.y, self.c, self.dirs)

    def _copy(self):
        return copy.deepcopy(self)

    # directions
    def _add_dir(self, direction):
        self.dirs.append(direction)

    # reset direction (set empty list)
    def _reset_dir(self):
        self.dirs = list()

    def _len_dir(self):
        return len(self.dirs)

    def _is_on_hole(self, grid):
        return grid[self.y, self.x] == DEST

    def _dir_left_possible(self, grid, balls):
        rep = self.x - self.c >= 0 and \
            grid[self.y, self.x - self.c] != WATER and \
            all([grid[self.y, self.x-x_i] in [FREE, WATER, DEST]
                 for x_i in range(1, self.c+1)])
        if balls is not None:
            rep = rep and not any(
                [b.x == self.x - self.c and b.y == self.y and b.id != self.id for b in balls.values()])
        return rep

    def _dir_right_possible(self, grid, balls):
        rep = self.x + self.c < len(grid[0]) and \
            grid[self.y, self.c + self.x] != WATER and \
            all([grid[self.y, self.x+x_i] in [FREE, WATER, DEST]
                 for x_i in range(1, self.c+1)])
        if balls is not None:
            rep = rep and not any(
                [b.x == self.x + self.c and b.y == self.y and b.id != self.id for b in balls.values()])
        return rep

    def _dir_up_possible(self, grid, balls):
        rep = self.y - self.c >= 0 and \
            grid[self.y - self.c, self.x] != WATER and \
            all([grid[self.y - y_i, self.x] in [FREE, WATER, DEST]
                 for y_i in range(1, self.c+1)])
        if balls is not None:
            rep = rep and not any(
                [b.x == self.x and b.y == self.y - self.c and b.id != self.id for b in balls.values()])
        return rep

    def _dir_down_possible(self, grid, balls):
        rep = self.y + self.c < len(grid) and \
            grid[self.y + self.c, self.x] != WATER and \
            all([grid[self.y + y_i, self.x] in [FREE, WATER, DEST]
                 for y_i in range(1, self.c+1)])
        if balls is not None:
            rep = rep and not any(
                [b.x == self.x and b.y == self.y + self.c and b.id != self.id for b in balls.values()])
        return rep

    # Update available directions for a given ball
    # If balls are not None: balls constraint are considered
    # Else: only grid constraint
    def _set_avail_dir(self, grid, balls=None, debug=False):
        # If first initialisation: set all direction
        self._reset_dir()

        # If ball on DESTINATION or no more shoots available
        if grid[self.y, self.x] != DEST and self.c != 0:
            # check LEFT
            if self._dir_left_possible(grid, balls):
                self._add_dir(LEFT)

            # Check RIGHT
            if self._dir_right_possible(grid, balls):
                self._add_dir(RIGHT)

            # Check UP
            if self._dir_up_possible(grid, balls):
                self._add_dir(UP)

            # Check DOWN
            if self._dir_down_possible(grid, balls):
                self._add_dir(DOWN)


class Solution:
    grid            = None          # Init on creation
    balls           = None          # Init on creation

    solved          = False         # If this is the solution !
    continue_recur  = True          # If there are still no obvious paths after reduction 
    valid_sol       = True          # If some move are not allowed (e.g. unvalidate solution)

    paths = []                      # All paths not obvious
    paths_obvious = []              # obvious paths 
    grid_solved = None              # solution (quite useless variable :P)


    def __init__(self, grid):
        self.grid = grid
        self._set_balls_from_grid()


    def _copy(self):
        return copy.deepcopy(self)


    def _set_balls_from_grid(self):
        self.balls = [Ball(x, y, int(cell)) for y, line in enumerate(self.grid)
                      for x, cell in enumerate(line) if cell.isdigit()]
        self.balls = {b.id: b for b in self.balls}


    # Set available directions for all balls
    def _set_direction_balls(self):
        for id, ball in self.balls.items():
            self.balls[id]._set_avail_dir(self.grid, self.balls)


    # Don't use self.grid because of recursion
    def _find_all_paths_one_ball(self, ball, grid, path=[]):
        # Require ball directions have been set
        # Init all paths
        paths = []

        # For all possible direction
        for d in ball.dirs:
            # copy ball + grid + path
            b_copy = ball._copy()
            g_copy = grid.copy()
            p_copy = path.copy()

            # append direction to paths
            p_copy.append(d)
            # Apply move
            b_copy, g_copy = self._move(b_copy, g_copy, d)
            # If ball is on hole
            if b_copy._is_on_hole(g_copy):
                # Success: path finished
                paths.append(p_copy)
            else:
                # Update ball dirs
                b_copy._set_avail_dir(g_copy)
                # If no more dirs possible:
                if b_copy._len_dir():
                    # Continue sub paths
                    paths += self._find_all_paths_one_ball(
                        b_copy, g_copy, p_copy)
        return paths


    def _set_all_paths_to_all_balls(self, balls=None):
        # Init paths
        self.paths = []
        self.paths_obvious = []

        g_copy = self.grid.copy()
        # For all balls: set all possible path leading to a hole
        for ball in self.balls.values():
            b_copy = ball._copy()
            b_copy._set_avail_dir(g_copy, balls)
            paths = self._find_all_paths_one_ball(b_copy, g_copy)
            paths = [(b_copy, path) for path in paths]

            # Obvious move (e.g. 1 move)
            if len(paths) == 1:
                self.paths_obvious += paths

            # Several possible moves
            elif len(paths) > 0:
                self.paths += paths

        # Increase filter between paths and obvious paths
        self._filter_paths()


    # Count the number of possible sources for each DEST
    # If there is only one source, that mean this ball must come from this source
    # So the path associated to this ball becomes "obvious" :P
    # It's also important to remove the destinations where balls are already on !
    #   > This is the role of "already_used" variable
    def _filter_paths(self):
        # dummy grid
        grid = copy.deepcopy(self.grid)

        # Remove all balls positions to destinations candidate
        already_used = ["{},{}".format(b.y, b.x) for b in self.balls.values()]

        all_paths = copy.deepcopy(self.paths) + copy.deepcopy(self.paths_obvious)

        # Create a dict with a list of path leading to a point:
        #   - Key: (y,x) point coordinate
        #   - Value: list of paths
        mat = {}
        for ball, path in all_paths:
            ball_move = ball._copy()
            for direction in path:
                ball_move, _ = self._move(ball_move, grid, direction)

            k = "{},{}".format(ball_move.y, ball_move.x)
            if k not in already_used:
                if k not in mat.keys():
                    mat[k] = []
                mat[k].append([ball, path])

        # Select all new obvious path:
        # already obvious path: balls ID
        paths_obvious_balls_id = [p[0].id for p in self.paths_obvious]
        new_paths = [d_path[0] for pos, d_path in mat.items() if len(
            d_path) == 1 and d_path[0][0].id not in paths_obvious_balls_id]

        # Set them to current "paths_obvious"
        self.paths_obvious = self.paths_obvious + new_paths

        # For balls that become obvious, remove all others paths 
        balls_id = [b.id for b, p in self.paths_obvious]
        self.paths = [(b, p) for b, p in self.paths if b.id not in balls_id]

    # For a given ball, apply all move according a path
    # If some move are impossible:
    #   - movement is stopped
    #   - solution is set as unvalid

    def _follow_path(self, ball, path):
        # Copy the ball
        b_debug = ball._copy()
        # Iterate over movement
        for direction in path:
            # Update possible movement
            ball._set_avail_dir(self.grid, self.balls, True)
            # Check the path movement is possible
            if direction in ball.dirs:
                ball, self.grid = self._move(ball, self.grid, direction)
            else:
                # Unvalidate solution
                self.valid_sol = False
                self.continue_recur = False
                self.solved = False
                break

        self.balls[ball.id] = ball
        return self

    # Apply all obvious solution movements

    def _reduce_solution(self):
        # While there are obvious movement and the solution is still valid
        while len(self.paths_obvious) > 0 and self.valid_sol:
            # For each obvious movement
            for ball, path in self.paths_obvious:
                # Perform movement
                self._follow_path(ball, path)
            # Update all balls directions
            self._set_direction_balls()
            # Compute obvious movement
            self._set_all_paths_to_all_balls(self.balls)

        # Sort paths
        # self.paths.sort(key=lambda p: len(p[1]))
    # Update status of
    #   - continue_recur
    #   - solved

    def _update_sol_state(self):
        self.continue_recur = len(self.paths) != 0
        if not self.continue_recur:
            self.solved = all(
                [self.grid[b.y, b.x] == DEST for b in self.balls.values()])
            if self.solved:
                self.grid_solved = self.grid

    # Apply reduction problem steps
    def _reduce(self):
        if self.valid_sol:
            self._set_direction_balls()
            self._set_all_paths_to_all_balls()
            self._reduce_solution()
            self._update_sol_state()
        return self

    # Print output as coding game expect
    def _print_solution(self):
        if self.grid_solved is not None:
            print('Solution found:', file=file)
            for g in self.grid_solved:
                print("".join(g).replace(DEST, FREE).replace(WATER, FREE))
        else:
            print('No solution found', file=file)

    #########################################
    #               MOVE                    #
    #########################################
    def _move_left(self, ball, grid):
        grid[ball.y, ball.x] = MOVE[LEFT]
        ball.x -= 1
        return ball, grid

    def _move_right(self, ball, grid):
        grid[ball.y, ball.x] = MOVE[RIGHT]
        ball.x += 1
        return ball, grid

    def _move_up(self, ball, grid):
        grid[ball.y, ball.x] = MOVE[UP]
        ball.y -= 1
        return ball, grid

    def _move_down(self, ball, grid):
        grid[ball.y, ball.x] = MOVE[DOWN]
        ball.y += 1
        return ball, grid

    # Apply a ball move on the grid
    # No check is done (assumed the direction is correct)
    def _move(self, ball, grid, direction):
        for i in range(ball.c):
            if direction == LEFT:
                ball, grid = self._move_left(ball, grid)
            elif direction == RIGHT:
                ball, grid = self._move_right(ball, grid)
            elif direction == UP:
                ball, grid = self._move_up(ball, grid)
            elif direction == DOWN:
                ball, grid = self._move_down(ball, grid)
        ball.c -= 1
        return ball, grid


def read_data():
    # read dim + grid
    width, height = [int(i) for i in input().split()]
    return np.array([list(input().replace(" ", "")) for i in range(height)])


def solver(sols):
    # Remove unvalid sols
    sols = [sol for sol in sols if sol.valid_sol]

    new_sols = []
    # For each candidate solution
    for sol in sols:
        # If solution is valid:
        if sol.solved:
            # Return the solution
            return [sol]
        # If there are still some choice among path to do:
        elif sol.continue_recur:

            # Select 1 ball and all paths associated to this ball
            ball_ref = sol.paths[-1][0]
            paths = [p[1] for p in sol.paths if p[0].id == ball_ref.id]

            # Create a new list of solutions
            s = []
            # For each path to this ball
            for path in paths:

                # Try to apply this move
                # + reduction
                sol_copy = sol._copy()
                sol_copy = sol_copy._follow_path(
                    ball_ref._copy(), path)._reduce()

                # If solution is till a candidate (e.g. solution valid)
                if sol_copy.valid_sol:
                    # if solution solved
                    if sol_copy.solved:
                        # Return solution anyway
                        return [sol_copy]
                    else:
                        # Keep this solution as a candidate
                        s.append(sol_copy)
            # If there are some candidates
            if len(s) > 0:
                # Solve them !
                sols += solver(s)

    return sols


if __name__ == '__main__':
    # Read data
    grid = read_data()

    sol = Solution(grid)
    sol._reduce()

    s = solver([sol])

    if len(s) > 0:
        s[0]._print_solution()
    else:
        print("No solution")
