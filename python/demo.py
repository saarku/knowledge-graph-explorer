from flask import Flask, Response
from flask_cors import CORS
import json
from flask import request
from kb_server import KnowledgeBaseServer
from search_engine_server import SearchEngine

app = Flask(__name__)
CORS(app)


@app.route("/search/", methods=['GET', 'POST'])
def search():
    global search_engine
    json_data = request.get_data(as_text=True)
    data = json.loads(json_data)
    query = data['query']
    qid = data['qid']
    expansion_words = data['expansion']

    summaries, titles, rel_labels, clusters, clusters_line = list(search_engine.keyword_search(query, qid, expansion_words))

    tore_turn = {'abstracts': summaries, 'ids': titles, 'titles': titles, 'urls': titles, 'relevance': rel_labels,
                 'clusters': clusters, 'clusterline': clusters_line}
    response = Response(response=json.dumps(tore_turn), status=200, mimetype='application/json')
    return response


@app.route("/graph/", methods=['GET', 'POST'])
def graph():
    global kb_server
    json_data = request.get_data(as_text=True)
    data = json.loads(json_data)
    query = data['query']
    algorithm = data['algorithm']
    indexes = data['indexes']
    history_expansion = data['history_expansion']

    query_phrases = kb_server.parse_query(query, parse_type='phrase')

    indexes = [int(i) for i in indexes]
    if len(indexes) == 0:
        indexes = None

    first, second, weights, ids, names, colors, centrality, query_indexes = kb_server.get_partitions(query,
                                                                                                     query_phrases,
                                                                                                     algorithm,
                                                                                                     initial=indexes,
                                                                                                     previous_query=
                                                                                                     history_expansion)
    query_flag = []
    for i, name in enumerate(names):
        if name in query_phrases:
            query_flag.append(1)
        else:
            query_flag.append(0)

    tore_turn = {'first': to_string(first), 'second': to_string(second), 'weights': to_string(weights),
                 'ids': to_string(ids), 'names': to_string(names), 'colors': to_string(colors),
                 "flags": to_string(query_flag), 'centrality': to_string(centrality), 'indexes': to_string(query_indexes)}
    response = Response(response=json.dumps(tore_turn), status=200, mimetype='application/json')
    return response


@app.route("/queries/", methods=['GET', 'POST'])
def get_queries():
    output_html = '<select id="queries" class="myclass">'

    with open(queries_dir, 'r') as input_file:
        for line in input_file:
            args = line.rstrip('\n').split(':')
            qid = args[0]
            query = args[1]
            output_html += '<option id="' + qid + '" value="' + query + '">' + query + '</option>'
    output_html += '</select>&nbsp;<button id="add">Add</button>'
    tore_turn = {'output': output_html}
    response = Response(response=json.dumps(tore_turn), status=200, mimetype='application/json')
    return response


def to_string(input_list):
    output_list = [str(a) for a in input_list]
    return output_list


if __name__ == '__main__':

    #network_dir = '/Users/saarkuzi/robust_kb/robust.w2v.phrase.network'#''demi_data/w2v.network'
    network_dir = '/Users/saarkuzi/acl_retrieval_collection/acl.w2v.phrase.network'
    #queries_dir = 'queries.robust.stemmed.with.stop.txt'
    queries_dir = '/Users/saarkuzi/acl_retrieval_collection/acl.stemmed.with.stop.txt'
    stopword_dir = '/Users/saarkuzi/acl_retrieval_collection/lemur-stopwords.txt'
    #documents_dir = '/Users/saarkuzi/robust_kb/robust.w2v.phrase.input.txt'

    flask_port = 8098  # should be the same as in 'index.html'
    search_engine = SearchEngine()
    kb_server = KnowledgeBaseServer(network_dir, search_engine, 5, 10, stopword_dir)

    app.run(host='0.0.0.0', port=flask_port)  # 'local_host'