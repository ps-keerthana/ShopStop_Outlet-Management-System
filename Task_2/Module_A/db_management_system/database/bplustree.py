from graphviz import Digraph
import math
import bisect


# B+ Tree Node class. Can be used as either internal or leaf node.
class BPlusTreeNode:
    def __init__(self, order, is_leaf=True):
        self.order = order                  # Maximum number of children a node can have
        self.is_leaf = is_leaf              # Flag to check if node is a leaf
        self.keys = []                      # List of keys in the node
        self.values = []                    # Used in leaf nodes to store associated values
        self.children = []                  # Used in internal nodes to store child pointers
        self.next = None                    # Points to next leaf node for range queries

    def is_full(self):
        # A node is full if it has reached the maximum number of keys (order - 1)
        return len(self.keys) >= self.order - 1

    def min_keys(self):
        """
        Return minimum keys that a non‑root node must have.
        For a node with order t: at least ceil(t/2) - 1 keys.
        """
        return max(0, math.ceil(self.order / 2) - 1)


class BPlusTree:
    """
    B+ Tree with branching factor `order`.
      - Internal node: at most `order - 1` keys, `order` children.
      - Each node after underflow kept at least `ceil(order/2) - 1` keys.
      - Leaves are linked via .next for efficient range scans.
    """

    def __init__(self, order=8):
        if order < 2:
            raise ValueError("Order must be >= 2")
        self.order = order
        self.root = BPlusTreeNode(order)

    #  helpers (bisect‑based, separator‑consistent) 

    def _find_child_index(self, node, key):
        """
        For internal node, find child index such that:
          - key < node.keys[0]  -> child 0
          - node.keys[i-1] <= key < node.keys[i]  -> child i
          - key >= node.keys[-1] -> child len(node.children) - 1

        We use bisect_right so that:
          - If key == node.keys[i], it behaves the same as key > node.keys[i]
            and goes to the right child (index i+1), matching the separator convention.
        """
        if not node.keys:
            return 0
        i = bisect.bisect_right(node.keys, key)
        return i

    def _find_leaf(self, key):
        """
        Traverse from root down to the leaf where key belongs.
        Uses _find_child_index so that keys equal to separators follow the right‑child path.
        """
        node = self.root
        while node and not node.is_leaf:
            i = self._find_child_index(node, key)
            node = node.children[i]
        return node

    def _leaf_key_index(self, leaf, key):
        """
        Binary search for key in leaf.keys; return index, or -1 if not found.
        Uses bisect_left so that key == leaf.keys[i] is found at index i.
        """
        if not leaf.keys:
            return -1
        i = bisect.bisect_left(leaf.keys, key)
        if i < len(leaf.keys) and leaf.keys[i] == key:
            return i
        return -1

    def _node_size_bytes(self):
        """
        Return an approximate memory size (in bytes) of the whole tree.
        Used for performance‑analysis / memory‑usage plots.
        """
        import sys
        def _size(node):
            total = sys.getsizeof(node)
            total += sys.getsizeof(node.keys)
            total += sys.getsizeof(node.values)
            total += sys.getsizeof(node.children)

            for v in node.values:
                total += sys.getsizeof(v)

            if not node.is_leaf:
                for c in node.children:
                    total += _size(c)
            return total

        return _size(self.root) if self.root else 0


    #  search 

    def search(self, key):
        """
        Search for a key in the B+ tree. Return the associated value if found, else None.
        """
        leaf = self._find_leaf(key)
        if not leaf:
            return None
        i = self._leaf_key_index(leaf, key)
        if i >= 0:
            return leaf.values[i]
        return None

    def _search(self, node, key):
        """
        Recursive helper for search.
        """
        if node.is_leaf:
            i = self._leaf_key_index(node, key)
            if i >= 0:
                return node.values[i]
            return None

        i = self._find_child_index(node, key)
        return self._search(node.children[i], key)

    #  insert (with single‑pass update) 

    def insert(self, key, value):
        """
        Insert key‑value pair into the B+ tree.
        If key already exists, update it in place during descent (single pass).
        This avoids the 2×logN penalty of search() + update().
        Return:
          - True if key was inserted,
          - False if key was updated,
          - None on structural error (should not happen).
        """
        # First split root if needed
        if self.root.is_full():
            old_root = self.root
            new_root = BPlusTreeNode(self.order, is_leaf=False)
            new_root.children.append(old_root)
            self._split_child(new_root, 0)
            self.root = new_root

        status = self._insert_update_pass(self.root, key, value)
        if status is None:
            return False  # error case
        return status

    def _insert_update_pass(self, node, key, value):
        """
        Single‑pass descent: insert if key not found,
        or update in place if key already exists.

        Returns:
          - True  if key was inserted,
          - False if key was updated,
          - None  on structural error.
        """
        if node.is_leaf:
            i = self._leaf_key_index(node, key)
            if i >= 0:
                # Key exists: update in place
                node.values[i] = value
                return False  # updated
            else:
                # Insert new key‑value pair
                i = bisect.bisect_left(node.keys, key)
                node.keys.insert(i, key)
                node.values.insert(i, value)
                return True  # inserted

        # For internal node, find correct child using separator‑consistent index
        i = self._find_child_index(node, key)
        child = node.children[i]

        # If child is full, split it and re‑find child index
        if child.is_full():
            self._split_child(node, i)
            i = self._find_child_index(node, key)
            if i >= len(node.children):
                return None
            child = node.children[i]

        return self._insert_update_pass(child, key, value)

    def _split_child(self, parent, index):
        """
        Split the child at the given index in the parent.
        For internal nodes: promote the middle key to parent and remove it from both children.
        For leaves: copy the middle key to parent and keep it in the right leaf.
        """
        child = parent.children[index]
        mid = self.order // 2 if child.is_leaf else (self.order - 1) // 2

        new_node = BPlusTreeNode(self.order, child.is_leaf)

        if child.is_leaf:
            #  Leaf split 
            new_node.keys = child.keys[mid:]
            new_node.values = child.values[mid:]
            child.keys = child.keys[:mid]
            child.values = child.values[:mid]

            new_node.next = child.next
            child.next = new_node

            # Promoted key is the smallest key in the right leaf (first of new_node)
            promoted_key = new_node.keys[0]

        else:
            #  Internal split 
            promoted_key = child.keys[mid]

            # Right child: keys after mid; children after mid+1
            new_node.keys = child.keys[mid + 1:]
            new_node.children = child.children[mid + 1:]

            # Left child: keys before mid; children up to mid
            child.keys = child.keys[:mid]
            child.children = child.children[:mid + 1]

        parent.keys.insert(index, promoted_key)
        parent.children.insert(index + 1, new_node)

    #  delete, _delete, _fill_child, _borrow, _merge 

    def delete(self, key):
        """
        Delete key from the B+ tree.
        Handle underflow by borrowing from siblings or merging nodes.
        Update the root if it becomes empty.
        Return True if deletion succeeded, False otherwise.
        """
        if not self.root.keys:
            return False

        success = self._delete(self.root, key)

        # If root has no keys and is internal, drop one level
        if self.root.is_leaf and len(self.root.keys) == 0:
            self.root = BPlusTreeNode(self.order)
        elif not self.root.is_leaf and len(self.root.keys) == 0:
            self.root = self.root.children[0]

        return success

    def _delete(self, node, key):
        """
        Recursive helper for deletion.
        Ensure all nodes maintain minimum keys after deletion.
        """
        if node.is_leaf:
            i = self._leaf_key_index(node, key)
            if i >= 0:
                node.keys.pop(i)
                node.values.pop(i)
                return True
            return False

        i = self._find_child_index(node, key)
        if i >= len(node.children):
            return False

        child = node.children[i]
        min_keys = child.min_keys()

        if len(child.keys) <= min_keys:
            self._fill_child(node, i)
            i = self._find_child_index(node, key)
            if i >= len(node.children):
                return False
            child = node.children[i]

        success = self._delete(child, key)

        if success:
            for j in range(len(node.keys)):
                if key == node.keys[j]:
                    n = node.children[j + 1]
                    while not n.is_leaf:
                        n = n.children[0]
                    if n.keys:
                        node.keys[j] = n.keys[0]

        return success


    def _fill_child(self, node, index):
        """
        Ensure child at given index has enough keys by borrowing from siblings or merging.
        Underflow corrections can bubble upward via _delete recursion.
        """
        if index >= len(node.children):
            return

        child = node.children[index]
        if len(child.keys) > child.min_keys():
            return

        left_ok  = (index > 0 and
                    len(node.children[index - 1].keys) > node.children[index - 1].min_keys())
        right_ok = (index < len(node.children) - 1 and
                    len(node.children[index + 1].keys) > node.children[index + 1].min_keys())

        if left_ok:
            self._borrow_from_prev(node, index)
        elif right_ok:
            self._borrow_from_next(node, index)
        else:
            if index < len(node.children) - 1:
                self._merge(node, index)
            else:
                self._merge(node, index - 1)

    def _borrow_from_prev(self, node, index):
        """
        Borrow a key from the left sibling to prevent underflow.
        """
        if index == 0 or index >= len(node.children):
            return

        child  = node.children[index]
        sibling = node.children[index - 1]

        if child.is_leaf:
            # Move last key‑value of left sibling into front of child
            k = sibling.keys.pop()
            v = sibling.values.pop()
            child.keys.insert(0, k)
            child.values.insert(0, v)
            node.keys[index - 1] = child.keys[0]  
        else:
            # Move parent key down into child, bring last child of sibling up
            child.keys.insert(0, node.keys[index - 1])
            child.children.insert(0, sibling.children.pop())
            node.keys[index - 1] = sibling.keys.pop()

    def _borrow_from_next(self, node, index):
        """
        Borrow a key from the right sibling to prevent underflow.
        """
        if index < 0 or index >= len(node.children) - 1:
            return

        child  = node.children[index]
        sibling = node.children[index + 1]

        if child.is_leaf:
            k = sibling.keys.pop(0)
            v = sibling.values.pop(0)
            child.keys.append(k)
            child.values.append(v)
            node.keys[index] = child.keys[-1] 
        else:
            child.keys.append(node.keys[index])
            child.children.append(sibling.children.pop(0))
            node.keys[index] = sibling.keys.pop(0)

    def _merge(self, node, index):
        """
        Merge child at index with its right sibling.
        """
        if index < 0 or index >= len(node.children) - 1:
            return

        left  = node.children[index]
        right = node.children[index + 1]

        if left.is_leaf:
            left.keys.extend(right.keys)
            left.values.extend(right.values)
            left.next = right.next
        else:
            left.keys.append(node.keys[index])
            left.keys.extend(right.keys)
            left.children.extend(right.children)

        node.keys.pop(index)
        node.children.pop(index + 1)

        
    #  update 

    def update(self, key, new_value):
        """
        Update value associated with an existing key.
        For assignment integrity, this is a separate API call,
        but in practice insert() already handles updates in a single pass.
        """
        leaf = self._find_leaf(key)
        if not leaf:
            return False
        i = self._leaf_key_index(leaf, key)
        if i >= 0:
            leaf.values[i] = new_value
            return True
        return False

    #  range queries 

    def range_query(self, start_key, end_key):
        """
        Return all key‑value pairs where start_key <= key <= end_key.
        Uses leaf‑linked‑list traversal for O(log n + k) range scans.
        """
        if start_key > end_key:
            return []

        result = []
        leaf = self._find_leaf(start_key)
        if leaf is None:
            return []

        first = True
        while leaf is not None:
            if first:
                start_i = bisect.bisect_left(leaf.keys, start_key)
                first = False
            else:
                start_i = 0
            for i in range(start_i, len(leaf.keys)):
                k = leaf.keys[i]
                if k > end_key:
                    return result
                result.append((k, leaf.values[i]))
            leaf = leaf.next
        return result

    def get_all(self):
        """
        Return every (key, value) pair in sorted order via leaf traversal.
        """
        result = []
        node = self.root
        while node and not node.is_leaf:
            node = node.children[0]
        while node:
            for i, k in enumerate(node.keys):
                result.append((k, node.values[i]))
            node = node.next
        return result

    #  visualize_tree 

    def visualize_tree(self, filename=None):
        """
        Generate a Graphviz representation of the tree structure.
        Optional filename can be provided to save as PNG.
        """
        dot = Digraph(comment="B+ Tree")
        dot.attr(rankdir="TB", size="12,8", nodesep="0.5")

        if self.root is not None:
            self._add_nodes(dot, self.root)
            self._add_edges(dot, self.root)

        if filename:
            dot.render(filename, format="png", cleanup=True)
        return dot

    def _add_nodes(self, dot, node):
        """
        Recursively add nodes to Graphviz using HTML‑like table labels.
        Clearly distinguishes leaf / internal nodes and their keys/values.
        """
        node_id = str(id(node))
        node._viz_id = node_id

        if node.is_leaf:
            cells = "".join(
                f'<TD BGCOLOR="#FFFDE7" BORDER="1" CELLPADDING="6">'
                f'<B>{k}</B><BR/><FONT POINT-SIZE="9">{str(v)[:12]}</FONT></TD>'
                for k, v in zip(node.keys, node.values)
            ) or '<TD>empty</TD>'
            label = (
                '<<TABLE BORDER="2" CELLBORDER="0" CELLSPACING="0" BGCOLOR="#FFFDE7" COLOR="#F9A825">'
                f'<TR><TD COLSPAN="{max(len(node.keys),1)}" BGCOLOR="#FFF9C4">'
                '<FONT POINT-SIZE="9"><B>LEAF</B></FONT></TD></TR>'
                f"<TR>{cells}</TR></TABLE>>"
            )
            dot.node(node_id, label=label, shape="none", margin="0")
        else:
            cells = "".join(
                f'<TD BGCOLOR="#E3F2FD" BORDER="1" CELLPADDING="6"><B>{k}</B></TD>'
                for k in node.keys
            ) or '<TD>empty</TD>'
            label = (
                '<<TABLE BORDER="2" CELLBORDER="0" CELLSPACING="0" BGCOLOR="#E3F2FD" COLOR="#1565C0">'
                f'<TR><TD COLSPAN="{max(len(node.keys),1)}" BGCOLOR="#BBDEFB">'
                '<FONT POINT-SIZE="9"><B>INTERNAL</B></FONT></TD></TR>'
                f"<TR>{cells}</TR></TABLE>>"
            )
            dot.node(node_id, label=label, shape="none", margin="0")

        if not node.is_leaf:
            for child in node.children:
                self._add_nodes(dot, child)
  

    def _add_edges(self, dot, node):
        """
        Add edges between nodes and dashed lines for leaf connections (for visualisation).
        Dashed red line is labeled "Next Leaf Pointer" to explicitly show leaf linkage.
        """
        if not node.is_leaf:
            for i, child in enumerate(node.children):
                dot.edge(node._viz_id, child._viz_id, label=str(i))
                self._add_edges(dot, child)

        if node.is_leaf and node.next is not None and hasattr(node.next, "_viz_id"):
            dot.edge(
                node._viz_id,
                node.next._viz_id,
                style="dashed",
                color="red",
                label="Next Leaf Pointer",
                fontsize="9",
                fontcolor="#9E9E9E"
            )

