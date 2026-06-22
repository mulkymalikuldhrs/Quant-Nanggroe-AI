"""Swarm protocol stub – supports multi‑instance collaboration when task complexity exceeds threshold.\n\nOnly minimal scaffolding needed for now. Full orchestration can be added later.\n"""

class SwarmInstance:
    def __init__(self, role: str, genome: dict):
        self.role = role
        self.genome = genome
        self.state = "initialized"
        self.output = None

    def run(self, task_data):
        """Execute the given task_data. Placeholder implementation just records the data."""
        # In a real swarm, this would trigger the full L1‑L8 pipeline for the role.
        self.output = {
            "role": self.role,
            "task": task_data,
            "result": f"{self.role} processed data"
        }
        self.state = "completed"
        return self.output

class SwarmOrchestrator:
    def __init__(self, genome: dict, threshold: int = 5):
        self.genome = genome
        self.threshold = threshold
        self.instances = []
        self.results = []

    def launch(self, task_data):
        """Launch a swarm if task complexity exceeds the threshold.
        `task_data` should contain a `complexity` integer field.
        """
        complexity = task_data.get("complexity", 1)
        if complexity < self.threshold:
            # Simple execution – single instance
            instance = SwarmInstance(role="executor", genome=self.genome)
            self.instances.append(instance)
            self.results.append(instance.run(task_data))
            return self.results
        # For higher complexity create multiple specialized instances
        roles = ["visionary", "skeptic", "engineer", "auditor", "economist"]
        for role in roles:
            instance = SwarmInstance(role=role, genome=self.genome)
            self.instances.append(instance)
            self.results.append(instance.run(task_data))
        return self.results

    def consensus(self):
        """Simple consensus: majority vote on `result` strings."""
        if not self.results:
            raise ValueError("Swarm has no results")
        from collections import Counter
        counter = Counter(r["result"] for r in self.results)
        most_common, _ = counter.most_common(1)[0]
        return most_common
