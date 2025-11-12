# Experiment about using TRM with MAS, trying to solve N Queen problem with llm agents

1- Gemma 3:12B version
2- Tinyllama version
3- Torch TRM implementation

Scripts use llm as shared model. There are 2 Agent types, first is Coordinator that interfaces with llm model and Queen model that moves according to inferred result from model. Result is exported as gif after timeout occurs.