"""
Ellydium tech tree data model and logic.

Manages tree definitions (node keys, categories, branches, costs),
validates node selections (mutual exclusion, branch unlock prerequisites,
point budgets), and supports copy/paste of tree configurations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.modules.loadout_manager.database import EllydiumNodeDef, LoadoutDatabase

# Categories where only one node can be active at a time within the category
EXCLUSIVE_CATEGORIES = {"SpecMod", "Offence", "Defence"}

# All node categories (excluding TreePoints metadata)
NODE_CATEGORIES = (
    "CPU", "Hull", "Shield", "Capacitor", "Engine",
    "Utility", "SpecMod", "Offence", "Defence",
)

# Display colors per category (for the editor UI)
CATEGORY_COLORS = {
    "CPU":       "#00FF00",  # green
    "Hull":      "#00BFFF",  # blue
    "Shield":    "#FFFF00",  # yellow
    "Capacitor": "#9F00FF",  # purple
    "Engine":    "#00FFFF",  # cyan
    "Utility":   "#FF6600",  # orange
    "SpecMod":   "#FF00FF",  # magenta
    "Offence":   "#FF0000",  # red
    "Defence":   "#AAAAAA",  # gray
}


@dataclass
class TreeNode:
    """A single node in the Ellydium tech tree."""
    key: str
    category: str
    branch: int
    cost: int
    effect: str
    enabled: bool = False

    @property
    def is_spec_mod(self) -> bool:
        return self.category == "SpecMod"

    @property
    def is_exclusive(self) -> bool:
        return self.category in EXCLUSIVE_CATEGORIES


@dataclass
class BranchThreshold:
    """Points required to unlock a branch."""
    branch: int
    threshold: int


class EllydiumTree:
    """
    Full Ellydium tech tree for a single ship.

    Loaded from the database; provides validation, point calculation,
    and state manipulation methods.
    """

    def __init__(self) -> None:
        self.ship_name: str = ""
        self.ship_id: int = 0
        self.max_points: int = 0
        self.nodes: dict[str, TreeNode] = {}
        self.branch_thresholds: list[BranchThreshold] = []

    # ── Loading ───────────────────────────────────────────────────────

    @classmethod
    def from_database(
        cls,
        db: "LoadoutDatabase",
        ship_id: int,
        build_id: int | None = None,
    ) -> "EllydiumTree":
        """Load tree definition + optionally a build's node states."""
        tree = cls()
        tree.ship_id = ship_id

        ship = db.get_ship_by_id(ship_id)
        if ship:
            tree.ship_name = ship.name

        # Load node definitions
        defs = db.get_tree_defs(ship_id)
        for d in defs:
            if d.category == "TreePoints":
                if d.node_key == "TreePoints_Max":
                    tree.max_points = d.cost
                elif d.node_key.startswith("TreePoints_Branch"):
                    branch_num = int(d.node_key.replace("TreePoints_Branch", ""))
                    tree.branch_thresholds.append(
                        BranchThreshold(branch=branch_num, threshold=d.cost)
                    )
            else:
                tree.nodes[d.node_key] = TreeNode(
                    key=d.node_key,
                    category=d.category,
                    branch=d.branch,
                    cost=d.cost,
                    effect=d.effect,
                )

        tree.branch_thresholds.sort(key=lambda b: b.branch)

        # Load build state
        if build_id is not None:
            states = db.get_node_states(build_id)
            for key, enabled in states.items():
                if key in tree.nodes:
                    tree.nodes[key].enabled = enabled

        return tree

    # ── Point calculations ────────────────────────────────────────────

    @property
    def total_cost(self) -> int:
        """Sum of costs for all enabled nodes."""
        return sum(n.cost for n in self.nodes.values() if n.enabled)

    @property
    def remaining_points(self) -> int:
        return self.max_points - self.total_cost

    def branch_cost(self, branch: int) -> int:
        """Sum of costs for enabled nodes in a specific branch."""
        return sum(
            n.cost for n in self.nodes.values()
            if n.enabled and n.branch == branch
        )

    def get_branches(self) -> list[int]:
        """List of unique branch numbers."""
        branches = sorted({n.branch for n in self.nodes.values()})
        return branches

    def get_nodes_by_category(self, category: str) -> list[TreeNode]:
        return [n for n in self.nodes.values() if n.category == category]

    def get_nodes_by_branch(self, branch: int) -> list[TreeNode]:
        return [n for n in self.nodes.values() if n.branch == branch]

    # ── Branch unlock checks ──────────────────────────────────────────

    def is_branch_unlocked(self, branch: int) -> bool:
        """Check if a branch has met its point threshold prerequisite."""
        for bt in self.branch_thresholds:
            if bt.branch == branch:
                return self.total_cost >= bt.threshold
        # Branch 1 is always unlocked (threshold 0)
        return True

    def get_branch_threshold(self, branch: int) -> int:
        for bt in self.branch_thresholds:
            if bt.branch == branch:
                return bt.threshold
        return 0

    # ── Node toggling with validation ─────────────────────────────────

    def can_enable(self, node_key: str) -> tuple[bool, str]:
        """
        Check if a node can be enabled.
        Returns (ok, reason_if_not).
        """
        node = self.nodes.get(node_key)
        if node is None:
            return False, "Node not found"

        if node.enabled:
            return False, "Already enabled"

        # Point budget check
        if self.total_cost + node.cost > self.max_points:
            return False, f"Not enough points ({node.cost} needed, {self.remaining_points} available)"

        # Branch unlock check
        if not self.is_branch_unlocked(node.branch):
            threshold = self.get_branch_threshold(node.branch)
            return False, f"Branch {node.branch} locked (need {threshold} total points)"

        return True, ""

    def toggle_node(self, node_key: str) -> tuple[bool, str]:
        """
        Toggle a node on/off with validation.
        For exclusive categories, disables the other active node.
        Returns (success, message).
        """
        node = self.nodes.get(node_key)
        if node is None:
            return False, "Node not found"

        if node.enabled:
            # Disabling is always allowed
            node.enabled = False
            return True, f"Disabled {node_key}"

        # Enabling
        ok, reason = self.can_enable(node_key)
        if not ok:
            return False, reason

        # Exclusive category: disable other active node first
        if node.is_exclusive:
            for other in self.nodes.values():
                if other.category == node.category and other.enabled and other.key != node_key:
                    other.enabled = False

        node.enabled = True
        return True, f"Enabled {node_key}"

    # ── State export/import ───────────────────────────────────────────

    def get_state(self) -> dict[str, bool]:
        """Export current node states as a dict."""
        return {key: node.enabled for key, node in self.nodes.items()}

    def set_state(self, states: dict[str, bool]) -> None:
        """Import node states from a dict."""
        for key, enabled in states.items():
            if key in self.nodes:
                self.nodes[key].enabled = enabled

    def copy_state(self) -> dict[str, bool]:
        return self.get_state()

    def paste_state(self, states: dict[str, bool]) -> int:
        """Paste states, returning count of nodes changed."""
        changed = 0
        for key, enabled in states.items():
            if key in self.nodes and self.nodes[key].enabled != enabled:
                self.nodes[key].enabled = enabled
                changed += 1
        return changed

    def clear_all(self) -> None:
        for node in self.nodes.values():
            node.enabled = False

    # ── Diff for automation ───────────────────────────────────────────

    def diff(self, current_states: dict[str, bool]) -> tuple[list[str], list[str]]:
        """
        Compare desired state against current game state.

        Returns (to_enable, to_disable) lists of node keys.
        """
        to_enable: list[str] = []
        to_disable: list[str] = []

        for key, node in self.nodes.items():
            current = current_states.get(key, False)
            if node.enabled and not current:
                to_enable.append(key)
            elif not node.enabled and current:
                to_disable.append(key)

        return to_enable, to_disable
