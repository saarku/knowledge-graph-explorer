import os


def parse_eval_file(file_dir):
    eval_dict = {}
    with open(file_dir, 'r') as input_file:

        for line in input_file:
            args = line.rstrip('\n').split()
            measure = args[0]
            qid = args[1]
            value = args[2]

            if qid == 'all':
                continue

            if qid not in eval_dict:
                eval_dict[qid] = {}

            eval_dict[qid][measure] = float(value)
    return eval_dict


def split_result_file(input_dir, output_dir):

    print('getting run ids')
    run_id_list = set()
    with open(input_dir, 'r') as input_file:
        for i, line in enumerate(input_file):
            run_id = line.rstrip('\n').split()[5]
            run_id_list.add(run_id)

    print('opening files')
    files_dict = {}
    for run_id in run_id_list:
        files_dict[run_id] = open(output_dir + run_id + '.txt', 'w+')

    print('writing output')
    with open(input_dir, 'r') as input_file:
        for i, line in enumerate(input_file):
            if i%100000 == 0:
                print(i)
            run_id = line.rstrip('\n').split()[5]
            files_dict[run_id].write(line)

    print('closing files')
    for run_id in files_dict:
        files_dict[run_id].close()


def run_trec_eval(results_folder_dir, output_dir):
    trec_eval_dir = '../../java_workspace/anserini/eval/trec_eval.9.0.4/trec_eval'
    qrels_dir = '/Users/saarkuzi/acl_retrieval_collection/qrels.txt'

    for file_name in os.listdir(results_folder_dir):

        os.system(trec_eval_dir + ' ' + qrels_dir + ' ' + results_folder_dir + '/' + file_name + ' -q > ' + output_dir
                  + '/' + file_name + '.eval')


def best_cluster_analysis(evals_dir, num_clusters, measure):
    all_evals_dict = {}

    for file_name in os.listdir(evals_dir):
        single_eval_dict = parse_eval_file(evals_dir + '/' + file_name)
        for qid in single_eval_dict:
            all_evals_dict[qid] = all_evals_dict.get(qid, []) + [single_eval_dict[qid][measure]]

    for qid in all_evals_dict:
        all_evals_dict[qid] = sorted(all_evals_dict[qid], reverse=True)

    output_line = measure
    for i in range(num_clusters):
        score = 0
        counter = 0
        for qid in all_evals_dict:
            score += all_evals_dict[qid][i]
            counter += 1.0
        output_line += ',' + str(score / counter)
    print(output_line)


def parse_qrels(qrels_dir):
    qrels_dict = {}
    with open(qrels_dir, 'r') as input_file:
        for line in input_file:
            args = line.rstrip('\n').split()
            qrels_dict[args[0]] = qrels_dict.get(args[0], []) + [args[2]]
    return qrels_dict


def parse_result_file(result_dir, cutoff):
    result_dict = {}
    with open(result_dir, 'r') as input_file:
        for line in input_file:
            args = line.rstrip('\n').split()
            rank = int(args[3])
            if rank <= cutoff:
                result_dict[args[0]] = result_dict.get(args[0], []) + [args[2]]
    return result_dict


def get_query_ids(result_dir):
    qid_list = set()
    with open(result_dir, 'r') as input_file:
        for line in input_file:
            args = line.rstrip('\n').split()
            qid_list.add(args[0])
    return list(qid_list)


def iterative_cluster_analysis(results_folder, qrels_dir, num_iterations, cutoff):
    qrels_dict = parse_qrels(qrels_dir)
    qid_list = get_query_ids(results_folder + '/uiuc0.txt')
    rel_doc_dict = {qid: set() for qid in qid_list}
    recall_dict = {qid: [] for qid in qid_list}
    final_values = [0.0] * (num_iterations + 1)
    final_nums = [0.0] * (num_iterations + 1)

    for iter_num in range(num_iterations + 1):
        result_dict = parse_result_file(results_folder + '/uiuc' + str(iter_num) + '.txt', cutoff)
        for qid in rel_doc_dict:
            rel_docs = set(result_dict.get(qid, [])).intersection(set(qrels_dict[qid]))
            if len(rel_docs.difference(rel_doc_dict[qid])) > 0:
                final_nums[iter_num] += 1.0
            rel_doc_dict[qid] = rel_doc_dict[qid].union(rel_docs)
            recall_dict[qid] += [len(rel_doc_dict[qid])/float(len(qrels_dict[qid]))]
            final_values[iter_num] += len(rel_doc_dict[qid])/float(len(qrels_dict[qid]))

    for i in range(len(final_values)):
        final_values[i] /= float(len(qid_list))
        final_nums[i] /= float(len(qid_list))

    print(','.join([str(i) for i in final_values]))
    print(','.join([str(i) for i in final_nums]))


def iterative_cluster_precision(evals_dir, num_iterations, cutoff):
    values = [0.0] * (num_iterations+1)

    for iter_num in range(num_iterations+1):
        eval_dict = parse_eval_file(evals_dir + '/uiuc' + str(iter_num) + '.txt.eval')
        counter = 0
        for qid in eval_dict:
            values[iter_num] += eval_dict[qid]['P_'+str(cutoff)]
            counter += 1
        values[iter_num] /= counter
    print(','.join([str(i) for i in values]))


def get_recall_upper_bounds(results_folder, qrels_dir, num_iterations, cutoff):
    qrels_dict = parse_qrels(qrels_dir)
    qid_list = get_query_ids(results_folder + '/uiuc0.txt')
    values = [0.0] * (num_iterations + 1)

    for i in range(num_iterations+1):
        recall = 0
        counter = 0
        cumulative_cutoff = (i + 1) * cutoff
        for qid in qid_list:
            counter += 1
            max_num_rel = len(qrels_dict[qid])
            if cumulative_cutoff >= max_num_rel:
                recall += 1
            else:
                recall += float(cumulative_cutoff)/max_num_rel
        values[i] = recall/counter

    print(','.join([str(i) for i in values]))


def main():
    data_folder = '/Users/saarkuzi/acl_retrieval_collection/results/'
    input_result_dir = data_folder + '/iterative_simulation/acl.iterative.pathextend.all.clusters.10.terms.10.anchor.0.5.txt'
    output_clusters_dir = data_folder + '/iterative_simulation/' + 'acl_iterative_pathextend_clusters_10_terms_10_anchor_05_results/'
    output_evals_dir = data_folder + '/iterative_simulation/acl_iterative_pathextend_clusters_10_terms_10_anchor_05_evals/'
    qrels_dir = '/Users/saarkuzi/acl_retrieval_collection/qrels.txt'

    split_results_flag = False
    run_eval_flag = False
    cluster_analysis_flag = False
    recall_bound_flag = True
    iterative_analysis_flag = False
    iterative_precision_flag = False

    if split_results_flag:
        if not os.path.exists(output_clusters_dir):
            os.mkdir(output_clusters_dir)
        split_result_file(input_result_dir, output_clusters_dir)
    if run_eval_flag:
        if not os.path.exists(output_evals_dir):
            os.mkdir(output_evals_dir)
        run_trec_eval(output_clusters_dir, output_evals_dir)
    if cluster_analysis_flag:
        measures = ['map', 'P_5', 'P_10', 'P_15', 'P_20', 'P_30']
        for m in measures:
            best_cluster_analysis(output_evals_dir, 10, m)
    if iterative_analysis_flag:
        iterative_cluster_analysis(output_clusters_dir, qrels_dir, 10, 50)
    if recall_bound_flag:
        for i in [10,20,30,40,50]:
            get_recall_upper_bounds(output_clusters_dir, qrels_dir, 10, i)
    if iterative_precision_flag:
        iterative_cluster_precision(output_evals_dir, 10, 10)

if __name__ == '__main__':
    main()