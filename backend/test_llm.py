import json
from data import aggregate_training_budget
from llm import generate_summary

data = aggregate_training_budget()
result = generate_summary(data)
print(json.dumps(result, indent=2))
