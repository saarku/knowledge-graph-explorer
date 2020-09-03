from py4j.java_gateway import JavaGateway, GatewayParameters
from utils import read_lines_from_file
from kb_server import KnowledgeBaseServer
from search_engine_server import SearchEngine
import time


class Simulator:

    def __init__(self, queries_dir, network_dir, anchor_weight, output_dir, stopword_dir):

        self.search_engine = SearchEngine()
        self.kb_server = KnowledgeBaseServer(network_dir, self.search_engine, 5, 10, stopword_dir)
        self.anchor_weight = anchor_weight
        self.output_dir = output_dir
        self.num_clusters = 0
        self.queries = self.load_queries(queries_dir)

    @staticmethod
    def load_queries(queries_dir):
        queries_dict = {}
        for i, line in enumerate(read_lines_from_file(queries_dir)):
            args = line.split(":")
            queries_dict[args[0]] = ' '.join(args[1:len(args)])
        return queries_dict

    def simulate_unsupervised(self):

        output_file = open(self.output_dir, 'w+')
        log_file = open('log.txt', 'w+')

        for qid in self.queries:
            t1 = time.time()
            query = self.queries[qid]
            parsed_query = self.kb_server.parse_query(query, 'phrases')
            _, _, _, _, words, partitions, centrality = self.kb_server.get_partitions(query, parsed_query,
                                                                                      "pathsextend", num_central=1)

            expansion_words = []
            expansion_weights = []
            for i, word in enumerate(words):
                for w in word.split('_'):
                    expansion_words.append(w)
                    expansion_weights.append(1.0)

            log_line = qid + ',' + query + ','
            for i, word in enumerate(expansion_words):
                log_line += word + ':' + str(expansion_weights[i]) + ' '
            log_file.write(log_line + '\n')
            log_file.flush()

            result = self.search_engine.simulator_search(qid, query, expansion_words, expansion_weights,
                                                         self.anchor_weight, True, False)

            output_file.write(result)
            output_file.flush()
            print(qid + ": " + str((time.time()-t1)/60.0))

        output_file.close()
        log_file.close()

    def oracle_experiment(self):
        output_file = open(self.output_dir, 'w+')
        log_file = open('log.txt', 'w+')

        for qid in self.queries:
            t1 = time.time()
            query = self.queries[qid]
            parsed_query = self.kb_server.parse_query(query, 'phrases')

            _, _, _, _, words, partitions, centrality, _ = self.kb_server.get_partitions(query, parsed_query, "partial", num_central=10)

            log_line = qid + ',' + query + ','
            expansion_words = {}
            expansion_weights = {}
            for i, p in enumerate(partitions):
                for w in words[i].split('_'):
                    expansion_words[p] = expansion_words.get(p, []) + [w]
                    expansion_weights[p] = expansion_weights.get(p, []) + [1.0]
                    log_line += w + ':' + str(p) + ' '

            log_file.write(log_line + '\n')
            log_file.flush()

            for p in expansion_words.keys():
                result, _ = self.search_engine.simulator_search(qid, query, expansion_words[p], expansion_weights[p],
                                                             self.anchor_weight, True, False, run_name="uiuc"+str(p))

                output_file.write(result)
                output_file.flush()

            print(qid + ": " + str((time.time()-t1)/60.0))

        output_file.close()
        log_file.close()

    def single_cluster_simulation(self):
        output_file = open(self.output_dir, 'w+')
        log_file = open('single.cluster.log.txt', 'w+')

        for qid in self.queries:
            t1 = time.time()
            query = self.queries[qid]
            parsed_query = self.kb_server.parse_query(query, 'phrases')
            _, _, _, _, words, partitions, centrality, _ = self.kb_server.get_partitions(query, parsed_query,
                                                                                         "pathsextend", num_central=10)

            expansion_dict = {}
            for i, word in enumerate(words):
                expansion_dict[partitions[i]] = [word] + expansion_dict.get(partitions[i], [])

            # print(expansion_dict)

            partition_scores = {}
            for partition_id in expansion_dict:
                partition_scores[partition_id] = self.search_engine.get_aspect_score(expansion_dict[partition_id], qid)
            # print(partition_scores)
            selected_partition = [x for x in sorted(partition_scores, key=partition_scores.get, reverse=True)][0]

            expansion_words = set()
            for i, word in enumerate(expansion_dict[selected_partition]):
                for w in word.split('_'):
                    expansion_words.add(w)

            expansion_weights = []
            expansion_words = list(expansion_words)
            for _ in range(len(expansion_words)):
                expansion_weights.append(1.0)

            log_line = qid + ',' + query + ','
            for i, word in enumerate(expansion_words):
                log_line += word + ':' + str(expansion_weights[i]) + ' '
            log_file.write(log_line + '\n')
            log_file.flush()

            result, _ = self.search_engine.simulator_search(qid, query, expansion_words, expansion_weights,
                                                         self.anchor_weight, True, False)

            output_file.write(result)
            output_file.flush()
            print(qid + ": " + str((time.time()-t1)/60.0) + " (single cluster tf)")

        output_file.close()
        log_file.close()

    def iterative_simulation(self):
        output_file = open(self.output_dir, 'w+')
        log_file = open('iterative.cluster.log.part4.txt', 'w+')

        for qid in self.queries:
            t1 = time.time()
            query = self.queries[qid]
            # print("===========" + query + "===========")
            num_relevant_docs = self.search_engine.get_num_rel_docs(qid)

            # print("total num rel: " + str(num_relevant_docs))
            relevant_discovered = set()
            parsed_query = self.kb_server.parse_query(query, 'phrases')
            initial_result, rel_docs = self.search_engine.simulator_search(qid, query, [], [], 1.0, True, False,
                                                                           run_name="uiuc0")
            output_file.write(initial_result)
            output_file.flush()
            relevant_discovered = relevant_discovered.union(rel_docs)

            # print("initially discovered: " + str(len(relevant_discovered)))

            query_indexes = []
            previous_expansion = []
            novel_cluster_flag = True
            iteration_counter = 0
            log_line = qid + ',' + query + ','

            while len(relevant_discovered) < num_relevant_docs and novel_cluster_flag and iteration_counter < 10:
                args = self.kb_server.get_partitions(query, parsed_query, "pathsextend", num_central=10,
                                                     initial=query_indexes, previous_query=previous_expansion)
                words = args[4]
                partitions = args[5]
                query_indexes = args[7]

                expansion_dict = {}
                for i, word in enumerate(words):
                    expansion_dict[partitions[i]] = [word] + expansion_dict.get(partitions[i], [])

                partition_scores = {}
                for partition_id in expansion_dict:
                    partition_scores[partition_id] = self.search_engine.get_aspect_score(expansion_dict[partition_id],
                                                                                         qid,
                                                                                         relevant_discovered=
                                                                                         relevant_discovered)
                sorted_partitions = [x for x in sorted(partition_scores, key=partition_scores.get, reverse=True)]

                novel_cluster_flag = False

                # print("========== iteration: " + str(iteration_counter) + "============")
                num_trails = 0
                for p in sorted_partitions:
                    num_trails += 1
                    expansion_words = set()
                    for i, word in enumerate(expansion_dict[p]):
                        for w in word.split('_'):
                            expansion_words.add(w)

                    expansion_words = list(expansion_words)
                    expansion_weights = [1.0] * len(expansion_words)
                    result, rel_docs = self.search_engine.simulator_search(qid, query, expansion_words,
                                                                           expansion_weights, self.anchor_weight, True,
                                                                           False,
                                                                           run_name="uiuc"+str(iteration_counter+1))

                    num_novel = len(rel_docs.difference(relevant_discovered))
                    relevant_discovered = relevant_discovered.union(rel_docs)

                    # print("num rel: " + str(len(rel_docs)) + " num novel: " + str(num_novel) + " " + str(expansion_words))

                    if num_novel > 0:
                        novel_cluster_flag = True
                        output_file.write(result)
                        output_file.flush()
                        iteration_counter += 1
                        previous_expansion = expansion_words.copy()
                        # print("selected cluster: " + str(expansion_words))

                        for i, word in enumerate(expansion_words):
                            log_line += word + ':' + str(iteration_counter) + ' '
                        log_line += 'numtrails:' + str(iteration_counter) + ":" + str(num_trails) + ' '
                        break

            log_file.write(log_line + '\n')
            log_file.flush()
            print(qid + ": " + str((time.time()-t1)/60.0) + " (iterative part 4)")

        output_file.close()
        log_file.close()

    def rm3_baseline(self):
        output_file = open(self.output_dir, 'w+')
        log_file = open('rm3_log.txt', 'w+')

        for qid in self.queries:
            t1 = time.time()
            query = self.queries[qid]

            rm3 = self.search_engine.get_rm3(query, 0.8, 10, 10)


            expansion_words = list(rm3.keys())
            expansion_weights = list(rm3.values())

            log_line = qid + ',' + query + ','
            for i, word in enumerate(expansion_words):
                log_line += word + ':' + str(expansion_weights[i]) + ' '
            log_file.write(log_line + '\n')
            log_file.flush()

            result, _ = self.search_engine.simulator_search(qid, query, expansion_words, expansion_weights, 0.0, True,
                                                         False)
            output_file.write(result)
            output_file.flush()
            # print(qid + ": " + str((time.time()-t1)/60.0))

        output_file.close()
        log_file.close()

    def bm25_baseline(self):
        output_file = open(self.output_dir, 'w+')

        for qid in self.queries:
            query = self.queries[qid]

            expansion_words = []
            expansion_weights = []

            result, _ = self.search_engine.simulator_search(qid, query, expansion_words, expansion_weights, 1.0, True,
                                                         False)
            output_file.write(result)
            output_file.flush()

        output_file.close()


def main():
    java_dir_prefix = "/Users/saarkuzi/Documents/java_workspace/kb-explorer/"
    # queries_dir = java_dir_prefix + "queries.robust.stemmed.with.stop.txt"
    data_dir = "/home/skuzi2/kb-explorer/"

    data_dir_local = "/Users/saarkuzi/acl_retrieval_collection/"
    #data_dir = data_dir_local

    queries_dir = data_dir + "/acl.stemmed.with.stop.part4.txt"
    original_queries_dir = "/Users/saarkuzi/acl_data/acl_retrieval_collection/queries/acl.txt"

    # queries_dir = java_dir_prefix + "queries.robust.txt"
    # queries_dir = "/home/skuzi2/kb-explorer/queries.robust.stemmed.with.stop.txt"
    # kb_dir = "/Users/saarkuzi/robust_kb/robust.w2v.phrase.network"
    kb_dir = data_dir + '/acl.w2v.phrase.network' #''/acl.w2v.phrase.title.network'
    # kb_dir = "/home/skuzi2/kb-explorer/w2v_model/robust.w2v.phrase.network"
    stopword_dir = data_dir + 'lemur-stopwords.txt'

    anchor_weight = 0.5

    simulator = Simulator(queries_dir, kb_dir, anchor_weight, 'acl.iterative.pathextend.part4.clusters.10.terms.10.anchor.0.5.txt', stopword_dir)
    simulator.iterative_simulation()

if __name__ == '__main__':
    main()