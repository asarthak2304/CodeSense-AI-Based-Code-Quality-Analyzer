"""
CodeSense - DSA Detection Engine
Detects 40+ algorithms and 22+ data structures with complexity analysis and explanations.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from constants import ALGORITHM_COMPLEXITIES
from logger import get_logger

logger = get_logger(__name__)


@dataclass
class AlgorithmMatch:
    name:         str
    display_name: str
    start_line:   int
    end_line:     int
    confidence:   float          # 0.0 – 1.0
    reason:       str            # Why it was detected
    complexity:   Dict[str, str] = field(default_factory=dict)
    suggestion:   str            = ""
    category:     str            = ""


@dataclass
class DataStructureMatch:
    name:         str
    display_name: str
    line:         int
    evidence:     str


# ─── Algorithm Pattern Definitions ────────────────────────────────────────────

# Each entry: (algo_key, display_name, category, [patterns], reason_template)
# Patterns are regex strings matched against the raw code.
ALGORITHM_PATTERNS: List[Tuple[str, str, str, List[str], str]] = [
    # ── Sorting ──
    ("bubble_sort", "Bubble Sort", "Sorting",
     [r"def\s+(?:bubble_sort|bubblesort)\b",
      r"bubble.*sort",
      r"for\s+\w+\s+in\s+range.*?for\s+\w+\s+in\s+range",
      r"for\s+\w+.*?for\s+\w+.*?if\s+\w+\[\w+\].*?>"],
     "Nested loops with element comparison and swap — classic Bubble Sort pattern."),

    ("selection_sort", "Selection Sort", "Sorting",
     [r"min_idx|min_index|minimum.*index",
      r"for.*for.*if.*<.*arr\[min"],
     "Outer loop with inner minimum-finding loop and swap — Selection Sort."),

    ("insertion_sort", "Insertion Sort", "Sorting",
     [r"key\s*=\s*\w+\[.*\].*while.*\w+\[.*\]\s*>\s*key",
      r"insertion.*sort|insert.*sort"],
     "Key element shifted past larger elements — Insertion Sort."),

    ("merge_sort", "Merge Sort", "Sorting",
     [r"def\s+merge\w*\s*\(|merge_sort|mergesort",
      r"mid\s*=.*//.*2.*merge|left.*right.*merge"],
     "Recursive divide-at-midpoint with merge step — Merge Sort."),

    ("quick_sort", "Quick Sort", "Sorting",
     [r"pivot|partition\s*\(",
      r"def\s+quick_sort|quicksort|def\s+partition"],
     "Pivot selection and partitioning — Quick Sort."),

    ("heap_sort", "Heap Sort", "Sorting",
     [r"heapify|heap_sort|heapsort",
      r"heapq\.(heappush|heappop|heapify)"],
     "Heap property maintenance and extraction — Heap Sort."),

    ("counting_sort", "Counting Sort", "Sorting",
     [r"count\s*=\s*\[0\].*\*|count_arr|counting.*sort",
      r"for.*count\[.*\]\s*\+=\s*1.*for.*count\[.*\]\s*>"],
     "Frequency count array used for sorting — Counting Sort."),

    ("radix_sort", "Radix Sort", "Sorting",
     [r"radix|counting_sort.*exp|digit.*sort",
      r"exp\s*=\s*1.*while.*exp.*//.*10"],
     "Digit-by-digit stable sort — Radix Sort."),

    ("bucket_sort", "Bucket Sort", "Sorting",
     [r"bucket|buckets\s*=\s*\[",
      r"floor.*n.*\*.*arr.*bucket"],
     "Elements distributed into buckets — Bucket Sort."),

    ("shell_sort", "Shell Sort", "Sorting",
     [r"gap\s*=.*//\s*2|shell.*sort",
      r"while\s+gap\s*>\s*0.*gap\s*=\s*gap\s*//"],
     "Gap-based insertion sort — Shell Sort."),

    # ── Searching ──
    ("linear_search", "Linear Search", "Searching",
     [r"def\s+(?:linear_search|search_linear)\b",
      r"linear.*search",
      r"def\s+\w*search\w*\s*\(.*?\).*?for\s+\w+\s+in\s+range\s*\(.*?len\(.*?\)\s*\).*?if\s+\w+\[\w+\]\s*=="],
     "Sequential scan through elements — Linear Search."),

    ("binary_search", "Binary Search", "Searching",
     [r"mid\s*=.*left.*right.*//\s*2|mid\s*=.*low.*high.*//\s*2",
      r"binary.*search|bisect\.(bisect|insort)",
      r"while\s+low\s*<=\s*high.*mid.*left.*right"],
     "Mid-point calculation with halving — Binary Search."),

    ("jump_search", "Jump Search", "Searching",
     [r"jump.*search|step\s*=.*math\.sqrt|block.*size.*sqrt",
      r"while.*\w+\[min\(step"],
     "Fixed-step jumping with linear fallback — Jump Search."),

    ("interpolation_search", "Interpolation Search", "Searching",
     [r"interpolation.*search",
      r"pos\s*=.*low.*\+.*high.*-.*low.*//.*arr\[high\].*-.*arr\[low\]"],
     "Probe position computed from value distribution — Interpolation Search."),

    ("exponential_search", "Exponential Search", "Searching",
     [r"exponential.*search",
      r"i\s*=\s*1.*while.*i\s*<.*len.*and.*arr\[i\].*<=.*x.*i\s*\*=\s*2"],
     "Doubling range then binary search — Exponential Search."),

    ("ternary_search", "Ternary Search", "Searching",
     [r"ternary.*search|m1\s*=.*l\s*\+.*r\s*-\s*l\s*//\s*3",
      r"mid1.*mid2.*l.*r.*//\s*3"],
     "Two mid-points dividing range in thirds — Ternary Search."),

    ("dfs", "Depth-First Search (DFS)", "Searching",
     [r"def\s+dfs\s*\(|depth.first|dfs\s*\(",
      r"visited.*stack|stack\.append.*stack\.pop.*visited",
      r"def.*dfs.*visited.*for.*neighbor.*if.*not.*visited"],
     "Stack-based or recursive exploration — DFS."),

    ("bfs", "Breadth-First Search (BFS)", "Searching",
     [r"def\s+bfs\s*\(|breadth.first|bfs\s*\(",
      r"queue.*deque|from\s+collections\s+import\s+deque.*queue",
      r"queue\.append.*queue\.popleft.*visited"],
     "Queue-based level-order traversal — BFS."),

    # ── Graph ──
    ("dijkstra", "Dijkstra's Algorithm", "Graph",
     [r"dijkstra|heapq.*dist\[|priority.*queue.*dist",
      r"dist\s*=\s*\{.*float.*inf|dist\[source\]\s*=\s*0.*heapq"],
     "Priority-queue shortest-path with dist[] array — Dijkstra."),

    ("bellman_ford", "Bellman-Ford", "Graph",
     [r"bellman.ford|bellman_ford",
      r"for.*range.*V.*-.*1.*for.*u.*v.*w.*in.*edges.*dist\[v\]"],
     "V-1 edge relaxation rounds — Bellman-Ford."),

    ("floyd_warshall", "Floyd-Warshall", "Graph",
     [r"floyd.warshall|floyd_warshall",
      r"for\s+k.*for\s+i.*for\s+j.*dist\[i\]\[j\].*dist\[i\]\[k\].*dist\[k\]\[j\]"],
     "Triple nested loop over all vertices — Floyd-Warshall."),

    ("kruskal", "Kruskal's MST", "Graph",
     [r"kruskal|union.*find.*sort.*edges|edges\.sort.*weight",
      r"disjoint.*set|union_find|find\(.*parent"],
     "Sort edges and union-find for MST — Kruskal."),

    ("prim", "Prim's MST", "Graph",
     [r"prim|mst.*heapq|min.*spanning.*tree.*heap",
      r"in_mst|visited.*min.*edge.*key"],
     "Greedy vertex addition via priority queue — Prim."),

    ("topological_sort", "Topological Sort", "Graph",
     [r"topological.*sort|topo.*sort|in_degree",
      r"in_degree\[.*\]\s*==\s*0.*queue|kahns.*algorithm"],
     "Zero-in-degree queue or DFS finish-time ordering — Topological Sort."),

    ("tarjan_scc", "Tarjan's SCC", "Graph",
     [r"tarjan|scc|strongly.*connected",
      r"low\[.*\].*disc\[.*\].*stack.*scc"],
     "DFS with low-link values for SCC — Tarjan."),

    ("a_star", "A* Search", "Graph",
     [r"\ba_star\b|\bastar\b|heuristic.*f_score|g_score.*h_score",
      r"open_set.*heapq.*f_score.*g_score"],
     "Heuristic-guided best-first search — A*."),

    # ── Dynamic Programming ──
    ("fibonacci_dp", "Fibonacci (DP/Memoization)", "Dynamic Programming",
     [r"memo|dp\[.*\]\s*=\s*dp\[.*-1\]\s*\+\s*dp\[.*-2\]",
      r"@lru_cache|functools\.cache.*fibonacci|fib\(",
      r"dp\s*=\s*\[0\].*dp\[1\]\s*=\s*1.*dp\[i\]\s*=\s*dp\[i-1\]"],
     "Memoized or tabulated Fibonacci — Dynamic Programming."),

    ("lcs", "Longest Common Subsequence", "Dynamic Programming",
     [r"lcs|longest.*common.*sub|dp\[i\]\[j\]\s*=\s*dp\[i-1\]\[j-1\]\s*\+\s*1",
      r"if\s+\w+\[i-1\]\s*==\s*\w+\[j-1\].*dp\[i\]\[j\]"],
     "2D DP table with diagonal fill on character match — LCS."),

    ("knapsack", "Knapsack Problem", "Dynamic Programming",
     [r"knapsack|0.1.*knapsack|dp\[.*\]\[.*\]\s*=\s*max.*dp\[.*-1\]",
      r"for.*items.*for.*weight.*dp\[i\]\[w\]"],
     "2D DP on items and capacity — Knapsack."),

    ("matrix_chain", "Matrix Chain Multiplication", "Dynamic Programming",
     [r"matrix.*chain|m\[i\]\[j\]\s*=\s*min|chain.*multiplication",
      r"for\s+l\s+in\s+range.*for\s+i.*for\s+k.*m\[i\]\[j\]"],
     "Interval DP on matrix dimensions — Matrix Chain Multiplication."),

    ("edit_distance", "Edit Distance (Levenshtein)", "Dynamic Programming",
     [r"edit.*distance|levenshtein|dp\[i\]\[j\]\s*=\s*1\s*\+\s*min.*dp\[i-1\]",
      r"if\s+\w+\[i-1\]\s*==\s*\w+\[j-1\].*dp\[i\]\[j\]\s*=\s*dp\[i-1\]\[j-1\]"],
     "2D DP on two string lengths — Edit Distance."),

    # ── String ──
    ("kmp", "KMP Pattern Matching", "String",
     [r"kmp|failure.*function|lps\s*=|prefix.*table",
      r"def.*compute.*lps|def.*kmp.*search"],
     "Prefix-failure table for O(n+m) matching — KMP."),

    ("rabin_karp", "Rabin-Karp", "String",
     [r"rabin.*karp|rolling.*hash|hash.*window",
      r"d\s*=\s*256.*q\s*=.*prime.*h\s*=.*pow"],
     "Rolling hash for pattern matching — Rabin-Karp."),

    ("boyer_moore", "Boyer-Moore", "String",
     [r"boyer.*moore|bad.*char.*heuristic|good.*suffix",
      r"bad_char|badchar"],
     "Bad-character and good-suffix heuristics — Boyer-Moore."),

    ("trie_search", "Trie-Based Search", "String",
     [r"class\s+TrieNode|\btrie\b|insert.*TrieNode",
      r"def\s+insert.*self.*root.*TrieNode|self\.children\["],
     "Prefix tree (Trie) for string storage and search."),

    # ── Advanced ──
    ("backtracking", "Backtracking", "Advanced",
     [r"backtrack|def.*backtrack|undo.*choose|choose.*explore.*unchoose",
      r"def.*solve.*board|def.*generate.*permutations|def.*n_queens"],
     "Recursive choice-explore-unchoose — Backtracking."),

    ("greedy", "Greedy Algorithm", "Advanced",
     [r"greedy|sort.*key.*lambda|heapq.*greedy|activity.*selection",
      r"sorted.*key=lambda.*for.*in.*if.*greedy"],
     "Locally optimal choice at each step — Greedy."),

    ("divide_and_conquer", "Divide and Conquer", "Advanced",
     [r"divide.*conquer|def.*divide|left\s*=.*solve.*mid|right\s*=.*solve.*mid",
      r"return.*merge\(.*left.*right|return.*combine"],
     "Recursive split into subproblems with combine step — Divide and Conquer."),

    ("two_pointer", "Two-Pointer Technique", "Advanced",
     [r"left\s*=\s*0.*right\s*=.*len|two.*pointer|l\s*,\s*r\s*=\s*0",
      r"while\s+left\s*<\s*right.*left\s*\+=\s*1.*right\s*-=\s*1"],
     "Opposite-end pointers converging — Two-Pointer."),

    ("sliding_window", "Sliding Window", "Advanced",
     [r"sliding.*window|window.*size|max_sum.*window",
      r"window_start|window_end|for.*window.*if.*window.*>"],
     "Fixed or variable-size moving window — Sliding Window."),
]


# ─── Data Structure Patterns ──────────────────────────────────────────────────

DS_PATTERNS: List[Tuple[str, str, List[str]]] = [
    ("array", "Array/List",
     [r"\w+\s*=\s*\[|\.append\(|\.pop\(|list\("]),

    ("linked_list", "Singly Linked List",
     [r"class\s+\w*Node.*next|self\.next\s*=|ListNode"]),

    ("doubly_linked_list", "Doubly Linked List",
     [r"self\.prev\s*=|self\.next\s*=.*self\.prev|DNode|DoublyLinked"]),

    ("circular_linked_list", "Circular Linked List",
     [r"self\.next\s*=\s*self\.head|circular.*linked|tail\.next\s*=\s*head"]),

    ("stack", "Stack",
     [r"\.append\(.*\.pop\(\)|stack\s*=\s*\[|Stack\(\)|LIFO"]),

    ("queue", "Queue",
     [r"from\s+collections\s+import\s+deque|queue\.Queue\(\)|Queue\(\)|FIFO",
      r"\.popleft\(\)|enqueue|dequeue"]),

    ("deque", "Deque (Double-Ended Queue)",
     [r"deque\(\)|\.appendleft\(|\.popleft\(|collections\.deque"]),

    ("priority_queue", "Priority Queue / Min-Max Heap",
     [r"heapq\.|PriorityQueue\(\)|heappush|heappop|priority.*queue"]),

    ("binary_tree", "Binary Tree",
     [r"class\s+\w*TreeNode.*left.*right|self\.left\s*=|self\.right\s*=",
      r"BinaryTree|binary.*tree"]),

    ("bst", "Binary Search Tree",
     [r"BST|BinarySearchTree|insert.*bst|search.*bst",
      r"if.*val.*<.*node.*left.*else.*right"]),

    ("avl_tree", "AVL Tree",
     [r"AVL|avl_tree|balance.*factor|rotate.*left.*rotate.*right",
      r"height\[.*\].*balance"]),

    ("red_black_tree", "Red-Black Tree",
     [r"RED|BLACK|red.*black|RBTree|rb_tree|color\s*=\s*RED"]),

    ("heap", "Heap",
     [r"heapify|heapq\.|build.*heap|max.*heap|min.*heap"]),

    ("trie", "Trie (Prefix Tree)",
     [r"class\s+TrieNode|self\.children\s*=\s*\{\}|insert.*trie|search.*trie"]),

    ("hash_table", "Hash Table / Dictionary",
     [r"\w+\s*=\s*\{\}|\w+\s*=\s*dict\(\)|defaultdict|Counter\("]),

    ("hash_set", "Hash Set",
     [r"\w+\s*=\s*set\(\)|\w+\s*=\s*\{[^:}]+\}|\.add\(.*\.discard\("]),

    ("graph", "Graph (Adjacency List/Matrix)",
     [r"adjacency|adj_list|adj_matrix|graph\s*=\s*\{|neighbors",
      r"defaultdict\(list\).*\w+\.append"]),

    ("dag", "Directed Acyclic Graph (DAG)",
     [r"DAG|directed.*acyclic|topological|in_degree"]),

    ("disjoint_set", "Disjoint Set (Union-Find)",
     [r"union.*find|UnionFind|disjoint.*set|parent\s*=\s*list.*range",
      r"def\s+find\(.*parent|def\s+union\("]),

    ("segment_tree", "Segment Tree",
     [r"segment.*tree|SegTree|seg_tree|build.*tree.*range.*query",
      r"def\s+update.*seg|def\s+query.*seg"]),

    ("fenwick_tree", "Fenwick Tree (Binary Indexed Tree)",
     [r"fenwick|BIT|binary.*indexed.*tree|bit\[i\s*\+\s*\(i\s*&\s*-i\]",
      r"def\s+update.*bit|def\s+query.*bit"]),

    ("b_tree", "B-Tree",
     [r"BTree|b_tree|btree|MIN_DEGREE|split_child|insert_non_full"]),
]


class DSADetector:
    """
    Detects algorithms and data structures in code with confidence scoring,
    complexity analysis, and actionable suggestions.
    """

    def detect(self, code: str, language: str) -> Dict[str, Any]:
        """
        Run DSA detection on source code.

        Returns:
            {
              algorithms: [...],
              data_structures: [...],
              summary: {...},
            }
        """
        algorithms      = self._detect_algorithms(code)
        data_structures = self._detect_data_structures(code)
        summary         = self._build_summary(algorithms, data_structures)

        return {
            "algorithms":      [self._algo_to_dict(a) for a in algorithms],
            "data_structures": [self._ds_to_dict(d)   for d in data_structures],
            "summary":         summary,
        }

    # ─── Algorithm Detection ─────────────────────────────────────────────────

    def _detect_algorithms(self, code: str) -> List[AlgorithmMatch]:
        matches: List[AlgorithmMatch] = []
        code_lower = code.lower()
        lines      = code.splitlines()

        for key, display, category, patterns, reason in ALGORITHM_PATTERNS:
            hit_count = 0
            first_line = 0

            for pattern in patterns:
                for i, line in enumerate(lines, start=1):
                    if re.search(pattern, line, re.IGNORECASE):
                        hit_count += 1
                        if first_line == 0:
                            first_line = i
                        break

            if hit_count == 0 and len(lines) > 1:
                # Check sliding windows of 25 lines to prevent multiline ReDoS on long files
                window_size = 25
                for w_idx in range(0, len(lines), 12):
                    chunk = "\n".join(lines[w_idx:w_idx + window_size])
                    for pattern in patterns:
                        try:
                            if re.search(pattern, chunk, re.IGNORECASE):
                                hit_count += 1
                                if first_line == 0:
                                    first_line = w_idx + 1
                                break
                        except Exception:
                            pass
                    if hit_count > 0:
                        break

            if hit_count > 0:
                confidence  = min(1.0, 0.5 + hit_count * 0.25)
                complexity  = ALGORITHM_COMPLEXITIES.get(key, {})
                suggestion  = self._get_suggestion(key, complexity)
                end_line    = self._estimate_end_line(lines, first_line)

                matches.append(AlgorithmMatch(
                    name=key, display_name=display, category=category,
                    start_line=first_line or 1, end_line=end_line,
                    confidence=confidence, reason=reason,
                    complexity=complexity, suggestion=suggestion,
                ))

        return sorted(matches, key=lambda m: m.confidence, reverse=True)

    def _estimate_end_line(self, lines: List[str], start: int) -> int:
        """Estimate function end from indentation."""
        if start == 0 or start >= len(lines):
            return start
        base_indent = len(lines[start - 1]) - len(lines[start - 1].lstrip())
        for i in range(start, min(start + 60, len(lines))):
            line = lines[i]
            if line.strip() and (len(line) - len(line.lstrip())) <= base_indent and i > start:
                return i
        return min(start + 30, len(lines))

    def _get_suggestion(self, key: str, complexity: Dict[str, str]) -> str:
        suggestions = {
            "bubble_sort":    "Bubble Sort is O(n²). Consider replacing with Python's built-in sorted() (Tim Sort, O(n log n)) or Merge Sort.",
            "selection_sort": "Selection Sort is always O(n²). Consider Insertion Sort for nearly-sorted data or Merge Sort for large data.",
            "insertion_sort": "Insertion Sort is efficient for small (n<20) or nearly-sorted arrays. For large inputs, use Merge Sort.",
            "linear_search":  "Linear Search is O(n). If data is sorted, Binary Search achieves O(log n).",
            "dfs":            "DFS uses O(V) stack space. For very deep graphs, consider iterative DFS to avoid stack overflow.",
            "bfs":            "BFS finds shortest paths in unweighted graphs. For weighted graphs, use Dijkstra.",
            "dijkstra":       "Dijkstra requires non-negative weights. For negative weights, use Bellman-Ford.",
            "floyd_warshall": "Floyd-Warshall is O(V³). For sparse graphs, running Dijkstra from each vertex may be faster.",
            "fibonacci_dp":   "Good use of memoization! For very large n, use iterative DP to avoid recursion depth limits.",
        }
        return suggestions.get(key, f"Complexity: {complexity.get('avg', 'unknown')}.")

    # ─── Data Structure Detection ─────────────────────────────────────────────

    def _detect_data_structures(self, code: str) -> List[DataStructureMatch]:
        matches: List[DataStructureMatch] = []
        lines = code.splitlines()

        for key, display, patterns in DS_PATTERNS:
            for pattern in patterns:
                for i, line in enumerate(lines, start=1):
                    if re.search(pattern, line, re.IGNORECASE):
                        matches.append(DataStructureMatch(
                            name=key, display_name=display,
                            line=i, evidence=line.strip()[:80],
                        ))
                        break   # One match per DS per pattern group
                else:
                    continue
                break           # Found this DS, move on

        # De-duplicate by name
        seen    = set()
        unique  = []
        for m in matches:
            if m.name not in seen:
                seen.add(m.name)
                unique.append(m)

        return unique

    # ─── Summary ─────────────────────────────────────────────────────────────

    def _build_summary(self, algos: List[AlgorithmMatch],
                       ds: List[DataStructureMatch]) -> Dict[str, Any]:
        categories: Dict[str, int] = {}
        for a in algos:
            categories[a.category] = categories.get(a.category, 0) + 1

        complexity_score = self._complexity_score(algos)

        return {
            "algorithm_count":       len(algos),
            "data_structure_count":  len(ds),
            "categories":            categories,
            "complexity_score":      complexity_score,
            "top_algorithm":         algos[0].display_name if algos else None,
            "primary_data_structure": ds[0].display_name if ds else None,
        }

    @staticmethod
    def _complexity_score(algos: List[AlgorithmMatch]) -> float:
        """
        Compute a DSA complexity score 0–100.
        Higher means more sophisticated algorithm usage.
        """
        if not algos:
            return 0.0
        tier_scores = {
            "Dynamic Programming": 90, "Graph": 85, "String": 80,
            "Advanced": 75, "Searching": 60, "Sorting": 50,
        }
        best = max(tier_scores.get(a.category, 40) * a.confidence for a in algos)
        diversity_bonus = min(20, len({a.category for a in algos}) * 5)
        return round(min(100, best + diversity_bonus), 1)

    # ─── Serialization ───────────────────────────────────────────────────────

    @staticmethod
    def _algo_to_dict(a: AlgorithmMatch) -> Dict[str, Any]:
        return {
            "name":         a.name,
            "display_name": a.display_name,
            "category":     a.category,
            "start_line":   a.start_line,
            "end_line":     a.end_line,
            "confidence":   a.confidence,
            "reason":       a.reason,
            "complexity":   a.complexity,
            "suggestion":   a.suggestion,
        }

    @staticmethod
    def _ds_to_dict(d: DataStructureMatch) -> Dict[str, Any]:
        return {
            "name":         d.name,
            "display_name": d.display_name,
            "line":         d.line,
            "evidence":     d.evidence,
        }