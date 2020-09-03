from gensim.models import Word2Vec
from gensim.models.word2vec import LineSentence
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk import stem


def pre_process_text(text, additional_stopwords=None, stem_flag=False):
    """Perform pre-processing for a piece of text.

    Args:
      text: (string) the input text.
      additional_stopwords: (list) additional (corpus-specific) stopwords to consider.
      stem_flag: (boolean) put True for stemming with Porter.
    Returns:
      The processed text.
    """
    text = text.lower()
    stop_words = set(stopwords.words('english'))
    if additional_stopwords is not None:
        stop_words = stop_words.union(set(additional_stopwords))

    word_tokens = word_tokenize(text)
    word_tokens = [w for w in word_tokens if (w not in stop_words) and (not has_numbers(w)) and len(w) > 2]

    if stem_flag:
        stemmer = stem.PorterStemmer()
        word_tokens = [stemmer.stem(w) for w in word_tokens]

    return " ".join(word_tokens)


def merge_phrases(text, phrase_stopwords):
    """Convert a (segmented) line of AutoPhrase output for learning an embedding model.

    Args:
      text: (string) the segmented line.
      phrase_stopwords: (list) a list of stopwords that cannot appear in phrases
    Returns:
      The processed text.
    """
    phrase_flag = False
    new_line = ''
    phrase = ''
    for word in text.rstrip('\n').split():
        if phrase_flag:
            phrase += '_' + word.replace('</phrase>', '')
            if '</phrase>' in word:
                phrase_flag = False
                if not check_phrasal_stopwords(phrase, phrase_stopwords):
                    new_line += phrase + ' '

        elif '<phrase>' in word and '</phrase>' in word:
            if not check_phrasal_stopwords(word, phrase_stopwords):
                new_line += word.replace('<phrase>', '').replace('</phrase>', '') + ' '

        elif '<phrase>' in word:
            phrase = word.replace('<phrase>', '')
            phrase_flag = True

        #else:
        #    new_line += word + ' '
    return new_line


def check_phrasal_stopwords(phrase, stopwords_list):
    """Check if a phrase contains a stopword from the list.

    Args:
      phrase: (string) a text (phrase).
      stopwords_list: (list) a list of stopwords that cannot appear in phrases
    Returns:
      True if the phrase contains a stopword
    """
    flag = False
    for w in stopwords_list:
        if w in phrase:
            return True
    return flag


def prepare_data(segmented_dir, output_dir):
    """Convert a (segmented) file of AutoPhrase to a file for learning an embedding model.

    Args:
      segmented_dir: (string) the segmented file directory.
      output_dir: (string) output directory
    Returns:
      Void. Writes the output to file.
    """
    robust_stopwords = ['pjg', 'ftag', 'itag', 'qtag', 'stag', 'hyph', 'frnewline', 'text', 'usdept', 'usbureau',
                        'blank', 'table', 'paragraph','intable', 'tableformat', 'cfr', 'cfrno', 'new', 'frfile']

    output_file = open(output_dir, 'w+')
    with open(segmented_dir, 'r') as input_file:
        for i, line in enumerate(input_file):
            modified_line = pre_process_text(merge_phrases(line, robust_stopwords), additional_stopwords=robust_stopwords)
            output_file.write(modified_line + '\n')
    output_file.close()


def learn_model(data_dir, model_dir):
    """Learn a word embeddings model.

    Args:
      data_dir: (string) input data dir - each document is a line.
      model_dir: (string) model directory.
    Returns:
      Void. Saves the model to a file.
    """
    sentences = LineSentence(data_dir)
    model = Word2Vec(sentences)
    model.save(model_dir)


def has_numbers(input_string):
    """Checks if a string contains digits.

    Args:
      input_string: (string) the input string.
    Returns:
      boolean. True if there are digits.
    """

    return any(char.isdigit() for char in input_string)


def build_network(model_dir, output_dir):
    """Build a network of words/phrases using a word embedding model.

    Args:
      model_dir: (string) the directory of the model.
      output_dir: (string) the output directory for the network.
    Returns:
      Void. Writes the output to a file.
    """
    network_dict = {}
    model = Word2Vec.load(model_dir)
    for word in model.wv.vocab.keys():
        neighbors = model.wv.similar_by_vector(model[word], topn=11, restrict_vocab=None)
        for n in neighbors:
            neighbor_word = n[0]
            similarity = n[1]
            if similarity > 0:
                if word < neighbor_word:
                    pair = tuple([word, neighbor_word])
                else:
                    pair = tuple([neighbor_word, word])
                network_dict[pair] = similarity

    with open(output_dir, 'w+') as output_file:
        for pair in network_dict:
            output_file.write(pair[0] + ' ' + pair[1] + ' ' + str(network_dict[pair]) + '\n')


def main():

    prepare_data_flag = False
    model_flag = True
    network_flag = True

    auto_phrase_data_dir = '/home/skuzi2/kb-explorer/AutoPhrase/models/ACL/segmentation.txt'
    w2v_data_dir = '/home/skuzi2/kb-explorer/acl.w2v.phrase.title.input.txt'
    model_dir = '/home/skuzi2/kb-explorer/acl.w2v.phrase.title.model'
    network_dir = '/home/skuzi2/kb-explorer/acl.w2v.phrase.title.network'

    if prepare_data_flag:
        print("preparing data")
        prepare_data(auto_phrase_data_dir, w2v_data_dir)
    if model_flag:
        print("learning model")
        learn_model(w2v_data_dir, model_dir)
    if network_flag:
        print("getting network")
        build_network(model_dir, network_dir)

if __name__ == '__main__':
    main()