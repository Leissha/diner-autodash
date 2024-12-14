# DinnerAutoDash - HD Research AI for Games

## Project Description
Inspired by the classic game Diner Dash and studies in AI for Games, Dinner AutoDash is a simple 2D restaurant simulation prototype built with Python and Pygame. This project explores the application of in-game AI techniques like FSM, GOAP, Steering, and A* pathfinding in a restaurant management context. The long-term vision includes potential for real-world restaurant simulation and collecting meaningful business insights.
![OG dinerdash](Docs/og_dinerdash.png)

## The Concept
- The world spawns customers at random rates and has six tables arranged in a 3×2 grid
- A left side "queue" of customers whose satisfaction declines over time
- One "servo" agent (the waiter) who uses a GOAP planner + A* pathfinding + steering to seat customers and deliver orders
- Customers follow an FSM (WAITING→ANGRY→LEAVING if not served; SEATED→ORDERED→EATING→LEAVING if served)

## Demo Videos

- **Single servo agent demonstration**: 
  
  <img src="Docs/Adobe%20Express%20-%201_Servo_agent.gif" width="800" alt="Single Agent Demo">

- **Multi-agent simulation with vector motion calculations**: 
  
  <img src="Docs/Adobe%20Express%20-%203_servo_agents_with_force_calc.gif" width="800" alt="Multi Agent Demo">


## Installation

1.  **Clone the repository:**

    ```bash
    git clone "https://github.com/Leissha/diner-autodash.git"
    cd DinnerAutoDash
    ```

2.  **Create and activate a virtual environment:**

    ```bash
    python -m venv .venv
    # On Windows:
    .\.venv\Scripts\activate
    # On macOS/Linux:
    source .venv/bin/activate
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

## How to Use

1.  **Activate the virtual environment:**

    ```bash
    # On Windows:
    .\.venv\Scripts\activate
    # On macOS/Linux:
    source .venv/bin/activate
    ```

2.  **Run the main script:**

    ```bash
    python main.py
    ```

3.  **Run the batch run script:**

    ```bash
    python batch_run.py
    ```

## Key Folders
### `Diagrams/`
System architecture and workflow diagrams:

#### System Architecture
![UML System Design](Diagrams/1.UML.jpg)
*UML system design showing the overall architecture*

![GUI Interface](Diagrams/2.GUI.jpg)
*GUI interface mockup and layout*

#### Customer Behavior
![Customer FSM](Diagrams/3.1.CustomerFSM.jpg)
*Customer Finite State Machine showing emotional states*

![Customer Timeline](Diagrams/3.2.%20CustomerFSM_timeline.jpg)
*Customer FSM timeline showing state transitions*

#### AI Planning
![GOAP Planner](Diagrams/4.1.%20GOAP_planner.jpg)
*GOAP (Goal-Oriented Action Planning) flowchart*

![Servo Agent Execution](Diagrams/4.2.%20ServoAgent_Execution_plan.jpg)
*Servo agent execution plan and decision tree*


## Directory Structure
-   `Actions/`: GOAP actions and pathfinding implementations
-   `Agents/`: AI agent implementations (servo agents)
-   `Customers/`: Customer behavior models and FSM states
-   `Docs/`: Additional documentation and testing notes
-   `Render/`: Visualization components for the simulation


### `insights/`
Performance analysis results including:

#### Performance Metrics
![Performance Analysis](insights/performance_analysis.png)
*Overall performance analysis showing key metrics*

![Performance Metrics](insights/performance_metrics.png)
*Detailed performance metrics breakdown*