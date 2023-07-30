


def get_index(source: str, search_string: str, start = 0, add_end_ouf_found_string: bool = False):
    if source is None:
        raise Exception("Source None")
    if search_string is None:
        raise Exception("SearchString None")

    idx = source.index(search_string, start)
    if add_end_ouf_found_string:
        idx += len(search_string)
    return idx
