from scipy.sparse import csr_matrix
import numpy as np
import networkx as nx
from networkx import connected_components
from networkx.algorithms.community.centrality import girvan_newman
from itertools import permutations
from networkx.algorithms.centrality import degree_centrality
from utils import check_inclusion


class KnowledgeBaseServer:

    def __init__(self, network_dir, search_engine_server, depth, num_clusters, stopword_dir):
        self.network, self.vocabulary = self.load_network(network_dir)
        self.search_engine = search_engine_server
        self.depth = depth
        self.nx_graph = self.get_nx_graph()
        self.num_clusters = num_clusters
        self.stop_words = [line.rstrip('\n') for line in open(stopword_dir, 'r').readlines()]

    @staticmethod
    def load_network(input_dir):
        vocabulary_dict = {}
        vocabulary_list = []
        term_index = 0

        row = []
        col = []
        data = []

        with open(input_dir, 'r') as input_file:
            for line in input_file:
                args = line.rstrip('\n').split()
                w1, w2, score = args[0], args[1], float(args[2])

                if w1 not in vocabulary_dict:
                    vocabulary_dict[w1] = term_index
                    vocabulary_list.append(w1)
                    term_index += 1

                if w2 not in vocabulary_dict:
                    vocabulary_dict[w2] = term_index
                    vocabulary_list.append(w2)
                    term_index += 1

                row.append(vocabulary_dict[w1])
                col.append(vocabulary_dict[w2])
                if w1 == w2:
                    data.append(1)
                else:
                    data.append(score)

                if w1 != w2:
                    row.append(vocabulary_dict[w2])
                    col.append(vocabulary_dict[w1])
                    data.append(score)

        num_terms = len(vocabulary_list)
        network = csr_matrix((data, (row, col)), shape=(num_terms, num_terms))
        return network, vocabulary_list

    @staticmethod
    def couple_unique_permutations(iterable):
        for p in permutations(sorted(iterable), 2):
            if p[0] < p[1]:
                yield p

    @staticmethod
    def reduce_partition(partition, num_groups):
        output = []
        sizes_dict = {}
        for i, group in enumerate(partition):
            sizes_dict[i] = len(group)
        sorted_indexes = [x for x in sorted(sizes_dict, key=sizes_dict.get, reverse=True)]
        for i in sorted_indexes[0:num_groups]:
            output.append(partition[i])
        return tuple(output)

    @staticmethod
    def get_central_nodes(nodes, parts, full_network, num_nodes, page_rank):
        central_flags = [0]*len(parts)

        for part_id in set(parts):
            part_nodes = []
            pr_centrality = {}
            for i, node in enumerate(nodes):
                if parts[i] == part_id:
                    part_nodes.append(node)
                    if len(page_rank) > 0:
                        pr_centrality[node] = page_rank[node]

            if len(page_rank) == 0:
                sub_graph = full_network.subgraph(part_nodes)
                centrality = degree_centrality(sub_graph)
                centrality_sorted = [x for x in sorted(centrality, key=centrality.get, reverse=True)]
            else:
                centrality_sorted = [x for x in sorted(pr_centrality, key=pr_centrality.get, reverse=True)]

            for central_node in centrality_sorted[0: num_nodes]:
                central_flags[nodes.index(central_node)] = 1

        return central_flags

    def parse_query(self, query, parse_type='unigrams'):
        query_words = query.split()
        num_words = len(query_words)

        if parse_type == 'unigrams':
            query_phrases = query.split()
            final_words = []
            for word in query_phrases:
                if word not in self.stop_words:
                    final_words.append(word)
            return query_phrases

        else:
            query_phrases = []
            for phrase_length in range(num_words, 0, -1):
                for i in range(num_words):
                    if i + phrase_length <= num_words:
                        phrase = '_'.join(query_words[i:i + phrase_length])
                        if check_inclusion(phrase, query_phrases) and phrase in self.vocabulary:
                            query_phrases.append(phrase)
            return query_phrases

    def get_network_partitions(self, matrix, num_groups, threshold=0.5):
        first_array = matrix.nonzero()[0]
        second_array = matrix.nonzero()[1]
        # print("num edges before filter: " + str(len(first_array)))
        graph = nx.Graph()
        nodes = set()

        weights_dict = {}
        # print(len(first_array))
        for i in range(len(first_array)):
            if first_array[i] < second_array[i] and matrix[first_array[i], second_array[i]] > threshold:
                weights_dict[i] = matrix[first_array[i], second_array[i]]

        num_edges = 0
        sorted_weights = [i for i in sorted(weights_dict, key=weights_dict.get, reverse=True)]

        limit = min(len(sorted_weights), 1000)
        for i in sorted_weights[0: limit]:
            nodes.add(first_array[i])
            nodes.add(second_array[i])
            graph.add_edge(first_array[i], second_array[i])
            num_edges += 1

        #print("num nodes after filter: " + str(len(nodes)))
        graph.add_nodes_from(list(nodes))

        nodes = list(nodes)
        nodes_to_remove = []

        for sub_graph in connected_components(graph):
            if len(sub_graph) < 4:
                for node_id in sub_graph:
                    nodes_to_remove.append(node_id)
                    del nodes[nodes.index(node_id)]

        # print("num nodes after cliques: " + str(len(nodes)))

        for node_id in nodes_to_remove:
            graph.remove_node(node_id)

        comp = girvan_newman(graph)
        partition = ()

        for communities in comp:
            partition = tuple(sorted(c) for c in communities)
            if len(partition) >= num_groups:
                break
            elif len(partition) > num_groups:
                partition = self.reduce_partition(partition, num_groups)
                break
            else:
                continue

        parts = [-1] * len(nodes)
        for group_id, group in enumerate(partition):
            for index in group:
                parts[nodes.index(index)] = group_id

        modified_parts = []
        modified_nodes = []

        for i, part in enumerate(parts):
            if part >= 0:
                modified_parts.append(part)
                modified_nodes.append(nodes[i])

        return modified_nodes, modified_parts, graph

    def get_nx_graph(self):
        first_array = self.network.nonzero()[0]
        second_array = self.network.nonzero()[1]
        graph = nx.Graph()
        nodes = set()

        num_edges = 0
        for i in range(len(first_array)):
            graph.add_edge(first_array[i], second_array[i])
            nodes.add(first_array[i])
            nodes.add(second_array[i])
            num_edges += 1
        graph.add_nodes_from(list(nodes))

        return graph

    def expand_network_neighbors(self, query_indexes, depth):
        for _ in range(depth):
            matrix = np.sum(self.network[query_indexes], axis=0)
            matrix[matrix > 0] = 1
            indexes = np.asarray(range(1, matrix.shape[1]+1)).reshape(matrix.shape)

            output = np.asarray(np.multiply(indexes, matrix)-1)[0,:]
            for i in output:
                if i >= 0:
                    query_indexes.append(int(i))
            query_indexes = list(set(query_indexes))
        return query_indexes

    def network_path_projection(self, query_words, expansion={}, initial=list()):

        query_indexes = [self.vocabulary.index(word) for word in query_words if word in self.vocabulary]
        expansion_indexes = []
        path_indexes = []

        if len(initial) == 0:
            for couple in self.couple_unique_permutations(query_indexes):
                paths = nx.all_simple_paths(self.nx_graph, source=couple[0], target=couple[1], cutoff=self.depth)
                for path in paths:
                    for node in path:
                        path_indexes.append(node)

        extra_paths = 0
        if len(expansion) > 0:
            term_indexes = [self.vocabulary.index(word) for word in expansion.keys() if word in self.vocabulary]
            for num, term_id in enumerate(term_indexes):
                for query_id in query_indexes:
                    path = nx.shortest_path(self.nx_graph, source=term_id, target=query_id)
                    if len(path) <= 4:
                        extra_paths += 1
                        for node in path:
                            expansion_indexes.append(node)

        if len(initial) > 0:
            expansion_indexes = list(set(expansion_indexes))
            expansion_indexes = self.expand_network_neighbors(expansion_indexes, 1)
            all_indexes = list(set(initial + expansion_indexes))

        else:
            all_indexes = list(set(expansion_indexes + query_indexes + path_indexes))
            all_indexes = self.expand_network_neighbors(all_indexes, 1)
            all_indexes = list(set(all_indexes))

        reduced_net = self.network[:, all_indexes][all_indexes, :]
        return reduced_net, all_indexes

    def reduce_page_rank_network(self, query_terms, threshold=0.0):
        query_indexes = [self.vocabulary.index(word) for word in query_terms if word in self.vocabulary]
        query_indexes = self.expand_network_neighbors(query_indexes, 3)
        reduced_net = self.network[:, query_indexes][query_indexes, :]

        first_array = reduced_net.nonzero()[0]
        second_array = reduced_net.nonzero()[1]
        graph = nx.Graph()
        nodes = set()

        for i in range(len(first_array)):
            if first_array[i] < second_array[i] and reduced_net[first_array[i], second_array[i]] > threshold:
                nodes.add(first_array[i])
                nodes.add(second_array[i])
                graph.add_edge(first_array[i], second_array[i])

        graph.add_nodes_from(list(nodes))
        return graph

    def get_page_rank_projection(self, query_words_dict, sub_graph):

        nodes_list = list(sub_graph.nodes)
        personalization_dict = {key: 0 for key in nodes_list}

        normalizer = 0
        for w in query_words_dict:
            if w in self.vocabulary:
                if self.vocabulary.index(w) in nodes_list:
                    normalizer += query_words_dict[w]

        for w in query_words_dict:
            if w in self.vocabulary:
                if self.vocabulary.index(w) in nodes_list:
                    personalization_dict[self.vocabulary.index(w)] = query_words_dict[w] / normalizer

        pr = nx.pagerank(sub_graph, personalization=personalization_dict)
        query_indexes = [key for key in sorted(pr, key=pr.get, reverse=True)][0:500]

        query_words = [self.vocabulary[key] for key in query_indexes[0:50]]
        reduced_net = self.network[:, query_indexes][query_indexes, :]
        return reduced_net, query_indexes, pr

    def visualize_partition(self, nodes, parts, network, query_indexes, centrality):

        ids = []
        names = []
        colors = []
        for i, node in enumerate(nodes):
            word_id = query_indexes[node]
            if centrality[i] > 0:
                ids += [node]
                names.append(self.vocabulary[word_id])
                colors.append(parts[i])

        first_array = network.nonzero()[0]
        second_array = network.nonzero()[1]
        first = []
        second = []

        for i in range(len(first_array)):
            if first_array[i] < second_array[i] and network[first_array[i], second_array[i]] > 0.0 \
                    and first_array[i] in ids and second_array[i] in ids:

                first.append(first_array[i])
                second.append(second_array[i])

        return first, second, [], ids, names, colors, centrality

    def get_partitions(self, query, query_words, algorithm, num_central=5, initial=list(), previous_query=list()):

        sub_network = []
        query_indexes = []
        page_rank_dict = {}

        if algorithm == "partial":
            query_unigrams = self.parse_query(query, parse_type='unigrams')
            query_phrases = self.parse_query(query, parse_type='phrases')

            query_indexes = [self.vocabulary.index(word) for word in query_phrases if word in self.vocabulary]
            query_weights = [4.0] * len(query_indexes)

            unigram_indexes = []
            unigram_weights = []
            for word in self.vocabulary:
                existence_flag = False
                words_counter = 0
                for query_unigram in query_unigrams:
                    if query_unigram in word:
                        existence_flag = True
                        words_counter += 1
                if existence_flag:
                    unigram_indexes.append(self.vocabulary.index(word))
                    if words_counter > 1:
                        unigram_weights.append(3.0)
                    else:
                        unigram_weights.append(2.0)

            query_indexes = query_indexes + unigram_indexes
            query_weights = query_weights + unigram_weights


            query_indexes = list(set(query_indexes))
            query_expand_indexes = query_indexes.copy()
            query_expand_indexes = self.expand_network_neighbors(query_expand_indexes, 1)
            query_expand_indexes = list(set(query_expand_indexes))

            query_expand_indexes_weights = []
            for i in query_expand_indexes:
                if i in query_indexes:
                    query_expand_indexes_weights.append(query_weights[query_indexes.index(i)])
                else:
                    query_expand_indexes_weights.append(1.0)

            query_indexes = query_expand_indexes
            sub_network = self.network[:, query_indexes][query_indexes, :]

            first_array = sub_network.nonzero()[0]
            second_array = sub_network.nonzero()[1]

            for i in range(len(first_array)):
                weight = query_expand_indexes_weights[first_array[i]] * query_expand_indexes_weights[second_array[i]]
                sub_network[first_array[i], second_array[i]] = weight * sub_network[first_array[i] ,second_array[i]]

        elif algorithm == "paths":
            sub_network, query_indexes = self.network_path_projection(query_words)

        elif algorithm == 'pathsextend':
            if len(previous_query) == 0:
                query_weight_dict = self.search_engine.get_rm1(query, 0.1, 10, 10)
            else:
                query_weight_dict = self.search_engine.get_rm1_iterative(query, previous_query, 0.1, 10, 10)

            sub_network, query_indexes = self.network_path_projection(query_words, expansion=query_weight_dict, initial=initial)

        elif algorithm == "pagerank":
            query_weight_dict = self.search_engine.get_rm3(query, 0.5, 10, 10)
            sub_graph = self.reduce_page_rank_network(list(query_weight_dict.keys()))
            sub_network, query_indexes, page_rank_dict = self.get_page_rank_projection(query_weight_dict, sub_graph)
        else:
            print("No such algorithm")
            exit(-1)

        nodes, parts, network = self.get_network_partitions(sub_network, self.num_clusters)
        centrality = self.get_central_nodes(nodes, parts, network, num_central, page_rank=page_rank_dict)

        first, second, _, ids, names, colors, centrality = \
            self.visualize_partition(nodes, parts, sub_network, query_indexes, centrality)

        return first, second, [], ids, names, colors, centrality, query_indexes


def main():
    query_words = ['database', 'systems']
    network_dir = 'demi_data/w2v.network'

    server = KnowledgeBaseServer(network_dir, 6, 5)

    clusters = server.get_partitions('database systems', query_words)
    print(clusters)

if __name__ == '__main__':
    main()