def check_inclusion(phrase, phrases_list):
    for other_phrase in phrases_list:
        if phrase in other_phrase:
            return False
    return True


def read_lines_from_file(input_dir, delimiter=None):
    lines = []

    if delimiter is not None:
        for line in get_file_lines(input_dir):
            lines.append(line.rstrip('\n').split(delimiter))

    else:
        for line in get_file_lines(input_dir):
            lines.append(line.rstrip('\n'))

    return lines


def get_file_lines(input_dir):
    with open(input_dir, 'r') as input_file:
        for line in input_file:
            yield line