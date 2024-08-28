
import heapq
import agentpy as ap
from matplotlib import pyplot as plt
import IPython
from owlready2 import *
import numpy as np


onto = get_ontology("file://onto_warehouse.owl")


with onto:
    class Entity(Thing):
        pass

    class Robot(Entity):
        pass

    class Object(Entity):
        pass

    class Stack(Object):
        pass

    class Place(Thing):
        pass

    class Position(Place):
        pass

    class has_place(ObjectProperty, FunctionalProperty):
        domain = [Entity]
        range = [Place]

    class has_position(DataProperty, FunctionalProperty):
        domain = [Place]
        range = [str]

    class carries(ObjectProperty):
        domain = [Robot]
        range = [Object]

    Robot.equivalent_to.append(carries.max(5, Object))


class WarehouseAgent(ap.Agent):
    pass


class WarehouseObject(ap.Agent):
    pass


class WarehouseStack(ap.Agent):
    pass


def astar(grid, start, goal):
    open_set = []
    pos = grid.positions[start]
    heapq.heappush(open_set, (0, pos))

    came_from = {}
    g_score = {pos: 0}
    f_score = {pos: heuristic(pos, goal)}

    while open_set:
        _, current = heapq.heappop(open_set)

        if current == goal:
            return reconstruct_path(came_from, current)

        for direction in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            neighbor_pos = (current[0] + direction[0],
                            current[1] + direction[1])

            if 0 <= neighbor_pos[0] < grid.shape[0] and 0 <= neighbor_pos[1] < grid.shape[1]:
                location = grid.grid[neighbor_pos[0]][neighbor_pos[1]]
                if type(location) == np.record:
                    agent_set = location[0]
                    blocked = False
                    for agent in agent_set:
                        if isinstance(agent, WarehouseAgent) or isinstance(agent, WarehouseStack):
                            blocked = True
                            break
                    if blocked:
                        continue
                tentative_g_score = g_score[current] + 1

                if neighbor_pos not in g_score or tentative_g_score < g_score[neighbor_pos]:
                    came_from[neighbor_pos] = current
                    g_score[neighbor_pos] = tentative_g_score
                    f_score[neighbor_pos] = tentative_g_score + \
                        heuristic(neighbor_pos, goal)
                    heapq.heappush(
                        open_set, (f_score[neighbor_pos], neighbor_pos))

    return []


def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def reconstruct_path(came_from, current):
    total_path = [current]
    while current in came_from:
        current = came_from[current]
        total_path.append(current)
    return total_path[::-1]


class WarehouseObject(ap.Agent):
    def setup(self):
        self.agentType = 2
        self.stacked = False

    def step(self):
        if all(agent.stacked for agent in self.model.objects):
            self.model.stop()


class WarehouseAgent(ap.Agent):
    def setup(self):
        self.agentType = 0
        self.direction = (1, 0)
        self.rules = [
            self.rule_drop,
            self.rule_move,
            self.rule_pickup
        ]
        self.actions = [
            self.drop,
            self.move_towards_target,
            self.pickup,
        ]
        self.percepts = []
        self.carries = []
        self.target = None
        self.moves = 0

    def see(self):
        x, y = self.model.grid.positions[self]
        self.percepts = []

        neighbors = self.model.grid.neighbors(self)
        for neighbor in neighbors:
            nx, ny = self.model.grid.positions[neighbor]

            if (nx == x and abs(ny - y) == 1) or (ny == y and abs(nx - x) == 1):
                self.percepts.append(neighbor)

    def next(self):
        for act in self.actions:
            for rule in self.rules:
                if rule(act):
                    act()

    def step(self):
        self.see()
        self.next()

    def rule_move(self, act):
        return act == self.move_towards_target

    def move(self, target):
        x, y = self.model.grid.positions[self]

        while True:
            nx, ny = target
            dx, dy = self.direction
            if x + dx == nx and y + dy == ny:
                break
            self.rotate_left()

        self.model.grid.move_by(self, self.direction)
        self.moves += 1

    def rotate_left(self):
        self.direction = (self.direction[1], -self.direction[0])

    def pickup(self):
        for obj in self.percepts:
            if self.target == obj:
                self.carries.append(obj)
                obj.stacked = True
                self.model.grid.remove_agents(obj)
                self.target = None
                break

    def rule_pickup(self, act):
        if act == self.pickup:
            if self.target in self.percepts and len(self.carries) < 5:
                return True
        return False

    def drop(self):
        x, y = self.model.grid.positions[self]
        nx, ny = self.direction

        # drop objects as a stack
        stack = WarehouseStack(self.model)
        self.model.stacks.append(stack)
        self.model.grid.add_agents([stack], positions=[(x + nx, y + ny)])
        stack.stack = self.carries
        self.carries = []

    def rule_drop(self, act):
        if act == self.drop:
            if len(self.carries) >= 5:
                return True

    def find_nearest_object(self):
        for obj in self.percepts:
            if isinstance(obj, WarehouseObject):
                self.target = obj
                return

        closest_object = None
        shortest_path = None

        for obj in self.model.objects:
            try:
                obj_pos = self.model.grid.positions[obj]
            except KeyError:
                continue
            path = astar(self.model.grid, self, obj_pos)
            if not closest_object or (path and len(path) < len(shortest_path)):
                closest_object = obj
                shortest_path = path

        self.target = closest_object
        return shortest_path

    def move_towards_target(self):
        path = self.find_nearest_object()
        if path and len(path) > 1:
            next_position = path[1]
            self.move(next_position)


class WarehouseStack(ap.Agent):
    def setup(self):
        self.agentType = 1
        self.content = []


class WarehouseModel(ap.Model):
    def setup(self):
        self.grid = ap.Grid(self, (self.p.M, self.p.N), track_empty=True)
        self.robots = ap.AgentList(self, self.p.robots, WarehouseAgent)
        self.objects = ap.AgentList(self, self.p.objects, WarehouseObject)
        self.stacks = ap.AgentList(self, self.p.stacks, WarehouseStack)
        self.grid.add_agents(self.robots, random=True, empty=True)
        self.grid.add_agents(self.objects, random=True, empty=True)
        self.steps = 0

    def step(self):
        self.robots.step()
        self.steps += 1
        return self.grid.grid

    def end(self):
        return {
            'steps': self.steps,
            'moves': [agent.moves for agent in self.robots]
        }


def animation_plot(model, ax):
    agent_type_grid = model.grid.attr_grid('agentType')
    ap.gridplot(agent_type_grid, cmap='Accent', ax=ax)

    for agent in model.robots:
        if isinstance(agent, WarehouseAgent) and model.grid.positions:
            try:
                x, y = model.grid.positions[agent]
            except KeyError:
                continue
            ax.text(y, x, len(agent.carries), ha='center',
                    va='center', color='black')
        elif isinstance(agent, WarehouseObject):
            try:
                x, y = model.grid.positions[agent]
            except KeyError:
                continue

    ax.set_title(f"Warehouse Model \n Time-step: {model.t}")


# SIMULATION:


# parameters = {
#     'M': 10,
#     'N': 10,
#     "steps": 25,
#     'robots': 5,
#     'objects': 30,
#     'stacks': 0,
# }


# model = WarehouseModel(parameters)

# Run with animation
# model.run()

# animation = ap.animate(model, fig, ax, animation_plot)
# IPython.display.HTML(animation.to_jshtml())
