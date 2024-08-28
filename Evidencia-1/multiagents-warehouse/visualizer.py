import aiohttp
import asyncio
import json
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation


async def initialize_simulation(session, url, params):
    async with session.post(url, json=params) as response:
        if response.status == 200:
            print("Simulation initialized successfully")
            return await response.json()
        else:
            print(f"Failed to initialize simulation: {await response.text()}")
            return None


async def step_simulation(session, url):
    async with session.get(url) as response:
        if response.status == 200:
            return await response.json()
        else:
            print(f"Failed to step simulation: {await response.text()}")
            return None


def process_grid(positions):
    M, N = len(positions), len(positions[0])
    grid = np.zeros((M, N))
    for i in range(M):
        for j in range(N):
            if positions[i][j] is not None:
                print(positions[i][j])
                grid[i][j] = positions[i][j][0]['type'] + 1
    return grid


def create_grid_image(grid_data, step):
    fig, ax = plt.subplots(figsize=(10, 10))
    im = ax.imshow(grid_data, cmap='viridis')
    plt.colorbar(im, ax=ax, ticks=[0, 1, 2, 3], label='Agent Type')
    ax.set_title(f"Step {step}")
    ax.set_xlabel("Column")
    ax.set_ylabel("Row")

    # Add text annotations
    for i in range(grid_data.shape[0]):
        for j in range(grid_data.shape[1]):
            if grid_data[i, j] != 0:
                ax.text(j, i, int(grid_data[i, j] - 1),
                        ha='center', va='center', color='white', fontweight='bold')

    return fig


async def run_simulation(url, params, num_steps):
    async with aiohttp.ClientSession() as session:
        # Initialize simulation
        init_response = await initialize_simulation(session, url, params)
        if init_response is None:
            return None

        # Run simulation and store grid states
        grid_states = []
        for step in range(num_steps):
            response = await step_simulation(session, url)
            if response is None or "message" in response:
                print("Simulation ended")
                break

            print(f"Step {step + 1}")

            # Process the grid and store it
            grid = process_grid(response['positions'])
            grid_states.append(grid)

        print("Simulation complete")
        return grid_states

# Server URL and simulation parameters
url = "http://localhost:8585"
params = {
    "init": True,
    "M": 15,
    "N": 15,
    "steps": 50,
    "robots": 5,
    "objects": 40,
    "stacks": 2
}
num_steps = 50

# Run the simulation asynchronously
grid_states = asyncio.run(run_simulation(url, params, num_steps))

if grid_states:
    # Create animation
    fig, ax = plt.subplots(figsize=(10, 10))

    im = ax.imshow(grid_states[0], cmap='viridis')
    plt.colorbar(im, ax=ax, ticks=[0, 1, 2, 3], label='Agent Type')
    ax.set_xlabel("Column")
    ax.set_ylabel("Row")

    title = ax.set_title("Step 0")

    def update(frame):
        im.set_array(grid_states[frame])
        title.set_text(f"Step {frame}")

        # Clear previous text annotations
        for txt in ax.texts:
            txt.remove()

        # Add new text annotations
        for i in range(grid_states[frame].shape[0]):
            for j in range(grid_states[frame].shape[1]):
                if grid_states[frame][i, j] != 0:
                    ax.text(j, i, int(grid_states[frame][i, j] - 1),
                            ha='center', va='center', color='white', fontweight='bold')

        return [im, title] + ax.texts

    anim = FuncAnimation(fig, update, frames=len(
        grid_states), interval=500, blit=True)
    plt.show()

    # Optionally, save the animation
    # anim.save('simulation_animation.gif', writer='pillow', fps=2)
else:
    print("Failed to run simulation")
