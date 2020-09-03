from py4j.java_gateway import JavaGateway, GatewayParameters
from nltk.tokenize import sent_tokenize
import numpy as np


class SearchEngine:

    def __init__(self, port_num=24000):
        self.server = JavaGateway(gateway_parameters=GatewayParameters(port=port_num))
        self.lucene_simulator = self.server.getSimulator()

    @staticmethod
    def boldface_query(text, query):
        # Generate a snippet by bold-facing the query terms in the text.

        keywords = [w.lower() for w in query.split()]
        words = text.split()

        for i, word in enumerate(words):
            for keyword in keywords:
                if keyword in word.lower():
                    words[i] = '<b>' + word + '</b>'
                    break
        return ' '.join(words).rstrip("\"").rstrip(".") + "."

    @staticmethod
    def get_sentence_score(sentence, query_words):
        score = 0
        words = sentence.split()
        for word in words:
            for q in query_words:
                if q.lower() in word.lower():
                    score += 1
        return score

    def get_num_rel_docs(self, qid):
        num_rel = self.lucene_simulator.getNumRelevant(qid)
        return num_rel


    def keyword_search(self, query, qid, expansion):

        expansion_terms = []
        for w in expansion:
            for t in w.split('_'):
                expansion_terms.append(t)
        expansion_terms = list(set(expansion_terms))
        expansion_weights = [1.0]*len(expansion_terms)

        terms_list = self.server.jvm.java.util.ArrayList()
        weights_list = self.server.jvm.java.util.ArrayList()

        for i, t in enumerate(expansion_terms):
            terms_list.append(t)
            weights_list.append(expansion_weights[i])

        results = list(self.lucene_simulator.searchGetText(qid, query, terms_list, weights_list, 0.5, 10, True, False))
        summaries = []
        titles = []
        ids = []
        rel_labels = []
        clusters = []

        for single_dict in results:
            summaries.append(self.create_summary(query, single_dict['text'], num_lines=10))
            titles.append(single_dict['title'])
            ids.append(single_dict['id'])
            rel_labels.append(single_dict['relevance'])
            clusters.append(single_dict['cluster'])

        doc_ids = self.server.jvm.java.util.ArrayList()
        for id in ids:
            doc_ids.append(id)

        clusters_line = self.lucene_simulator.getClusterDistribution(qid, doc_ids)

        return summaries, titles, rel_labels, clusters, clusters_line

    def simulator_search(self, qid, query, expansion_terms, expansion_weights, query_weight, process_orig, process_exp,
                         run_name="uiuc", top_results=20):

        expansion_terms_java = self.server.jvm.java.util.ArrayList()
        expansion_weights_java = self.server.jvm.java.util.ArrayList()

        for i, term in enumerate(expansion_terms):
            expansion_terms_java.append(term)
            expansion_weights_java.append(expansion_weights[i])

        result = self.lucene_simulator.search(qid, query, expansion_terms_java, expansion_weights_java, query_weight,
                                              process_orig, process_exp, run_name)

        doc_ids = self.server.jvm.java.util.ArrayList()
        for i, res_line in enumerate(result.split('\n')):
            if i == top_results:
                break
            doc_ids.append(res_line.split()[2])

        rel_docs = self.lucene_simulator.getRelDocuments(doc_ids, qid)

        return result, set(rel_docs)

    def get_rm3(self, query, anchor_weight, num_docs, num_terms):
        rm3_vector = self.lucene_simulator.getRm3Terms(query, anchor_weight, num_docs, num_terms)
        return rm3_vector

    def get_rm1(self, query, anchor_weight, num_docs, num_terms):
        rm1_vector = self.lucene_simulator.getRm1Terms(query, anchor_weight, num_docs, num_terms)
        return rm1_vector

    def get_rm1_iterative(self, query, previous_query, anchor_weight, num_docs, num_terms):
        expansion_terms = []
        for term in previous_query:
            for w in term.split('_'):
                expansion_terms.append(w)
        expansion_terms = set(expansion_terms)

        terms_list = self.server.jvm.java.util.ArrayList()
        weights_list = self.server.jvm.java.util.ArrayList()

        for w in expansion_terms:
            terms_list.append(w)
            weights_list.append(1.0)

        rm1_vector = self.lucene_simulator.getRm1IterativeTerms(query, terms_list, weights_list, anchor_weight, num_docs, num_terms)

        return rm1_vector

    def get_aspect_score(self, words, qid, relevant_discovered=set()):
        unique_words = set()

        for word in words:
            args = word.split('_')
            for a in args:
                unique_words.add(a)

        expansion_terms = self.server.jvm.java.util.ArrayList()
        for a in unique_words:
            expansion_terms.append(a)

        relevant_docs = self.server.jvm.java.util.ArrayList()
        for doc in relevant_discovered:
            relevant_docs.append(doc)

        return self.lucene_simulator.getQueryAspectScore(expansion_terms, qid, relevant_docs)

    def re_rank(self, qid, query, expansion_words, expansion_weights):
        expansion_terms_java = self.server.jvm.java.util.ArrayList()
        expansion_weights_java = self.server.jvm.java.util.ArrayList()

        for i, term in enumerate(expansion_words):
            expansion_terms_java.append(term)
            expansion_weights_java.append(expansion_weights[i])

        result = self.lucene_simulator.reRank(qid, query, expansion_terms_java, expansion_weights_java)
        return result

    def create_summary(self, query, text, num_lines=3):
        sentences = sent_tokenize(text)
        scores = []
        for s in sentences:
            scores.append(self.get_sentence_score(s, query.split()))

        max_index = np.argmax(scores)
        summary = ''
        for i in range(1, num_lines+1):
            if max_index - i >= 0:
                summary = sentences[max_index-i] + ' '

        summary += sentences[max_index]

        for i in range(1, num_lines+1):
            if max_index + i < len(sentences):
                summary += ' ' + sentences[max_index+i]

        summary = '. '.join(summary.split('.'))
        summary = ': '.join(summary.split(':'))
        summary = '; '.join(summary.split(';'))

        return self.boldface_query(summary, query)