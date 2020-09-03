# Python program to print all paths from a source to destination.
# Adopted from https://www.geeksforgeeks.org/find-paths-given-source-destination/
from collections import defaultdict
import copy


# This class represents a directed graph
# using adjacency list representation
class Graph:
    def __init__(self, vertices, length):
        # No. of vertices
        self.V = vertices
        # default dictionary to store graph
        self.graph = defaultdict(list)
        # list of all paths
        self.paths = []
        self.length = length

    # function to add an edge to graph
    def add_edge(self, u, v):
        self.graph[u].append(v)

    def get_all_paths_util(self, u, d, visited, path):

        # Mark the current node as visited and store in path
        visited[u] = True
        path.append(u)

        # If current vertex is same as destination, then print
        # current path[]
        if u == d:
            self.paths.append(copy.copy(path))

        else:
            # If current vertex is not destination
            # Recur for all the vertices adjacent to this vertex
            if len(path) < self.length:
                for i in self.graph[u]:
                    if not visited[i]:
                        self.get_all_paths_util(i, d, visited, path)

        # Remove current vertex from path[] and mark it as unvisited
        path.pop()
        visited[u] = False

    # Prints all paths from 's' to 'd'
    def get_all_paths(self, s, d):
        self.paths = []
        # Mark all the vertices as not visited
        visited = [False] * self.V
        # Create an array to store paths
        path = []
        # Call the recursive helper function to print all paths
        self.get_all_paths_util(s, d, visited, path)


def main():
    g = Graph(4, 4)
    g.add_edge(0, 1)
    g.add_edge(1, 0)
    g.add_edge(0, 2)
    g.add_edge(2, 0)
    g.add_edge(0, 3)
    g.add_edge(3, 0)
    g.add_edge(2, 1)
    g.add_edge(1, 2)
    g.add_edge(1, 3)
    g.add_edge(3, 1)

    s = 2
    d = 3
    print("Following are all different paths from %d to %d :" % (s, d))
    g.get_all_paths(s, d)

    print(g.paths)

if __name__ == '__main__':
    main()



