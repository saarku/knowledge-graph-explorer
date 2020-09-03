import utils
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.cluster import KMeans


def parse_qrel_file(qrel_dir):
    qrel_dict = {}
    lines = utils.read_lines_from_file(qrel_dir, delimiter=' ')

    for line in lines:
        label = line[3]
        if label == '1':
            qid = line[0]
            doc = line[2]
            qrel_dict[qid] = qrel_dict.get(qid, []) + [doc]
    return qrel_dict


def get_tf_idf_vectors(data_dir, ids_dir, min_df=5):
    ids = utils.read_lines_from_file(ids_dir)
    count_vector = CountVectorizer(min_df=min_df)
    tf_idf_transformer = TfidfTransformer()
    data_lines = utils.read_lines_from_file(data_dir)
    tf_vectors = count_vector.fit_transform(data_lines)
    tf_idf_vectors = tf_idf_transformer.fit_transform(tf_vectors)
    return tf_idf_vectors, ids


def cluster_queries(qrels_dir, data_dir, ids_dir, output_dir, num_clusters):
    qrels_dict = parse_qrel_file(qrels_dir)
    tf_idf_vectors, ids = get_tf_idf_vectors(data_dir, ids_dir, min_df=1)
    output_file = open(output_dir, 'w+')

    for qid in qrels_dict:
        print(qid)
        doc_indexes = [ids.index(doc_id) for doc_id in qrels_dict[qid]]
        num_documents = len(doc_indexes)
        qid_vectors = tf_idf_vectors[doc_indexes]
        k_means = KMeans(n_clusters=min(num_clusters, num_documents), random_state=0).fit(qid_vectors)
        clusters_dict = {}
        for i, cluster_id in enumerate(list(k_means.labels_)):
            clusters_dict[cluster_id] = clusters_dict.get(cluster_id, []) + []
            output_file.write(' '.join([qid, str(cluster_id), str(ids[doc_indexes[i]])]) + '\n')
    output_file.close()


def main():
    anserini_prefix = ''#''/Users/saarkuzi/Documents/java_workspace/anserini/'
    data_prefix = ''#''/Users/saarkuzi/Documents/java_workspace/kb-explorer/'
    qrels_dir = 'qrels.robust2004.txt' #anserini_prefix + 'src/main/resources/topics-and-qrels/qrels.robust2004.txt'
    num_clusters = 5

    cluster_queries(qrels_dir, data_prefix + 'robust.processed.lines', data_prefix + 'ids.txt',
                    data_prefix + 'clusters.txt', num_clusters)

if __name__ == '__main__':
    main()