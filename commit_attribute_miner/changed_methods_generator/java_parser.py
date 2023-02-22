from pathlib import Path

from tree_sitter import Language, Parser
from tree_sitter import Tree, Node

from util import read_file_as_bytes

Language.build_library(
    # Store the library in the `build` directory
    'build/my-languages.so',

    # Include one or more languages
    [
        'vendor/tree-sitter-java'
    ]
)

JAVA_LANGUAGE = Language('build/my-languages.so', 'java')
parser = Parser()
parser.set_language(JAVA_LANGUAGE)


def traverse_tree(tree: Tree):
    cursor = tree.walk()

    reached_root = False
    while not reached_root:
        yield cursor.node

        if cursor.goto_first_child():
            continue

        if cursor.goto_next_sibling():
            continue

        retracing = True
        while retracing:
            if not cursor.goto_parent():
                retracing = False
                reached_root = True

            if cursor.goto_next_sibling():
                retracing = False


def is_node_in_boundaries(node, start_idx, end_idx):
    method_start_row = node.start_point[0]
    method_end_row = node.end_point[0]

    return (method_start_row <= start_idx <= method_end_row) or (method_start_row <= end_idx <= method_end_row)


def get_methods_by_row_indicies(file_bytes: bytes, indicies: list[tuple[int, int]]) -> list[Node]:
    methods = []

    tree = parser.parse(file_bytes)
    for node in traverse_tree(tree):
        if node.type == "method_declaration":
            if any(is_node_in_boundaries(node, start_idx, end_idx) for start_idx, end_idx in indicies):
                methods.append(node)

    return methods


def get_all_methods(file_bytes: bytes) -> list[Node]:
    methods = []

    tree = parser.parse(file_bytes)
    for node in traverse_tree(tree):
        if node.type == "method_declaration":
            methods.append(node)

    return methods


def get_node_name(node: Node, decode_str: str | None = None) -> str | None:
    if not node.is_named:
        return None

    node_id_child = next((child for child in node.children if child.type == "identifier"), None)

    if not node_id_child:
        raise ValueError("No name for a named node?")
    if decode_str:
        node_id_child.text.decode(decode_str)

    return node_id_child.text.decode()


def are_nodes_with_same_name(node: Node, other_node: Node) -> bool:
    if not node.is_named or not other_node.is_named:
        raise ValueError("Only named nodes should be given to this function!")

    return get_node_name(node) == get_node_name(other_node)

