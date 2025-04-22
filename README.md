# language_game

A framework for exploring and sampling different trajectories in language-based social games.

## Overview

This project provides a robust framework for sampling and exploring different game trajectories when language model agents play social games together. The core functionality centers around the `GameSampler` which can build and explore a tree of possible game states.

## Key Features

- **Game Trajectory Sampling**: Explore different possible paths a game can take
- **Configurable Sampling Parameters**: Control depth and breadth of exploration
- **Game Tree Visualization**: Visualize the resulting decision trees in your browser
- **Game-Agnostic Design**: Works with any game that implements the required interfaces

## Game Sampler

The `GameSampler` is the heart of this project. It enables:

- Building a tree of game states
- Controlling the exploration width and depth
- Saving sampled trajectories for later analysis
- Generating visualizations of the game tree

### How Sampling Works

1. **Tree Structure**: Each game state is a node in a tree, with child nodes representing possible next states
2. **Controlled Exploration**: Parameters control how deep and wide the sampling goes
3. **Probabilistic Branching**: Captures the stochastic nature of agent decisions and game events
4. **Serialization**: Save the entire tree structure for later analysis or visualization

## Usage

```python
from src.sampler import GameSampler, GameNode
from src.game.your_game import YourGame

# Create your game instance
game = YourGame(config=your_config)

# Set up the sampler with desired parameters
sampler = GameSampler(
    name=game.name,
    max_depth=4,    # How many turns to look ahead
    max_degree=2    # Maximum branches at each decision point
)

# Create the root node with initial game state
root_node = GameNode(
    sampler=sampler,
    game=game
)

# Run the sampling process
sampler.sample_trajectories()

# Save the results
sampler.save()

# Generate an HTML visualization to view in browser
from src.utils.visualizer import create_html_tree
create_html_tree(sampler.name, sampler.id)
```

## Visualization

The project includes a browser-based visualization tool for exploring the sampled game trajectories:

1. After sampling, the script generates an HTML page
2. Open this page in any modern browser
3. Explore the game tree with interactive controls
4. See decision points, outcomes, and agent interactions

## Advanced Sampling Configuration

Fine-tune your sampling strategy with these parameters:

- **max_depth**: Controls how many turns into the future to sample
- **max_degree**: Controls how many alternative branches to consider at each point
- **sampling_strategy**: Choose different strategies for selecting which branches to explore
- **node_selection_policy**: Customize how the sampler decides which nodes to expand next

## Example: Different Sampling Strategies

```python
# Breadth-first sampling - explore many possible immediate outcomes
broad_sampler = GameSampler(
    name="breadth_first",
    max_depth=2,
    max_degree=5
)

# Depth-first sampling - follow fewer paths but explore further ahead
deep_sampler = GameSampler(
    name="depth_first",
    max_depth=8,
    max_degree=1
)

# Balanced sampling - reasonable coverage of both immediate and future states
balanced_sampler = GameSampler(
    name="balanced",
    max_depth=4,
    max_degree=2
)
```

## Contributing

Contributions to improve the sampling mechanism are welcome:
- Add new sampling strategies
- Optimize performance for larger game trees
- Enhance visualization capabilities
- Add analysis tools for sampled trajectories

## License

This project is licensed under the MIT License.