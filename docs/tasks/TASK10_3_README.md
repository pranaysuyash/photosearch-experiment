# Task 10.3: Integration Experiment

## Goal
"Close the loop" by wiring together the Semantic Engine (Task 10.1) and Vector Store (Task 10.2) into a working prototype that searches real files.

## Components

### `experiment_semantic_search.py`
A standalone CLI script that serves as a proof-of-concept.

### Workflow
1.  **Scan**: It reads all images from the `media/` folder.
2.  **Index**:
    *   Loads image -> Sends to CLIP -> Gets Vector -> Adds to Store.
3.  **Loop**:
    *   Starts a REPL (Read-Eval-Print Loop).
    *   User enters "dog on mountain".
    *   Script generates text vector -> Searches Store -> Prints matches.

## Usage
```bash
python experiment_semantic_search.py
```

## Results
This experiment confirms that the architecture works for the specific dataset in `media/`. It validates that the CLIP model correctly identifies concepts in the provided sample images.
