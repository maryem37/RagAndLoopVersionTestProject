# Multi-Agent Test Automation System with LangGraph

## Project Structure

    test-automation-langgraph/
    ├── agents/
    │ ├── init.py
    │ ├── gherkin_generator.py # Agent 2: Converts user stories to Gherkin
    │ ├── gherkin_validator.py # Agent 3: Validates .feature files
    │ ├── test_writer.py # Agent 4: Generates executable tests
    │ ├── test_executor.py # Agent 5: Runs tests
    │ ├── coverage_analyst.py # Agent 6: Measures test coverage
    │ └── self_healing.py # Agent 7: Auto-fixes failing tests
    ├── graph/
    │   ├── init.py   ← This tells Python that 'graph' is a package
    │   ├── state.py # Defines core state structure
    │   └── workflow.py # LangGraph workflow orchestrating agents
    ├── tools/
    │   ├── __init__.py
    │   ├── swagger_parser.py
    │   ├── gherkin_lint.py
    │   └── coverage_tools.py
    ├── config/
    │   ├── init.py
    │   └── settings.py # Configuration and environment settings
    ├── examples/
    │   ├── sample_user_story.md
    │   └── sample_swagger.JSON
    |   |__ test_swagger_reader.py
    ├── tests/
    │   └── init.py
    ├── main.py # Entry point for the system
    ├── requirements.txt # Python dependencies
    └── README.md


Build Order
We'll build agents in this order:

1. **State Definition** - Core data structure for storing workflow state.  
2. **Gherkin Generator** - Converts user stories to Gherkin `.feature` files.  
3. **Gherkin Validator** - Validates `.feature` files for syntax and rules.  
4. **Test Writer** - Generates executable test scripts from validated Gherkin.  
5. **Test Executor** - Runs the generated tests and logs results.  
6. **Coverage Analyst** - Measures test coverage and provides metrics.  
7. **Self-Healing** - Automatically fixes failing tests or retries.  
8. **LangGraph Workflow** - Orchestrates all agents and manages the process.

---
<img width="526" height="378" alt="image" src="https://github.com/user-attachments/assets/e4d048f4-44ab-44f1-ab64-d257e3496191" />
<img width="840" height="394" alt="image" src="https://github.com/user-attachments/assets/a079d1e1-2656-405e-a188-6e33d2e40b46" />


## Getting Started

1. **Install dependencies**

```bash
pip install -r requirements.txt
Set up environment variables

Create a .env file in the root directory.

Define necessary environment variables (e.g., API keys, paths).

Build agents step-by-step

Start by implementing the State Definition.

Follow the build order to implement agents sequentially.

Once all agents are implemented, you can run the LangGraph Workflow via main.py.

Run the system

python main.py
Test with examples

Check examples/sample_user_story.md and examples/sample_swagger.json.

Use these to validate that agents generate and execute tests correctly.

Notes
Ensure your Python environment is compatible with the requirements.txt.

Consider using a virtual environment to isolate dependencies:

python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
Keep tests/ updated with new unit tests as you build agents.

