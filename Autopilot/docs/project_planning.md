# Distributed RallyRoboPilot Project Requirements

## Where we are: 
- (27.11.2024): I have to plug together the genetic algorithm 
  - This needs solving the sync problem. => self defined finish lines.
- (27.11.2024): Need to begin vision.

## Project Goal
Develop an AI model that uses computer vision to play a racing game.

## Ingredients
- [ ] Vision model training POC (local)
- [ ] Use steps 1 and 2 for preliminary model assessment and define data requirements
- [ ] Validate data and model requirements
- [ ] Distributed data collection
- [ ] Distributed race performance optimization
- [ ] Final model training for race performance
- [ ] Automated, fault-tolerant model deployment, serving and monitoring.
- [ ] Optimized model for fast racing
- [ ] Scalable production model served via API

## Milestones
- **Week 1**: Set up a local proof-of-concept (POC) for image data collection and initial model training.
  - Tasks: Complete local POC for image data collection and vision model training.
    - [x] dockerized game with API for control and metadata collection (no images)
    - [ ] image collection pipeline (local) 
      - [x] POC redis server (dockerized)
      - [ ] POC multiple stream (images) to redis
        - interface definition in `rallyrobopilot/redis_interface.py` 
    - [x] clean game for data collection
      - add finish line
      - add lap duration to sensing
      - hide rays
      - **Design decision**: keeping sync between game and autopilot is too difficult => we 
      decide to only consider laps that start from the game base state in the training (start at the starting line).
      - **Solutions**: Fixing the game-sync drift problem required two steps:
        1. Sync the sending of commands with the absolute game time. 
        2. Limit the game framerate (and physics updating) to 25 FPS so we are not missing informations between frames.

- **Week 2**: Conduct preliminary model assessment and define data requirements. Validate data and model requirements.
  - Tasks: Use steps 1 and 2 for preliminary model assessment, define data requirements, and validate them.
- **Week 3**: Begin distributed data collection and work on race performance optimization.
  - Tasks: Implement distributed data collection using the Kubernetes cluster and start optimizing race performance.
- **Week 4**: Finalize model training, deployment, and set up automated, fault-tolerant serving and monitoring.
  - Tasks: Complete final model training for race performance, deploy it, and ensure the system is automated, fault-tolerant, and monitored.



## Work Packages

- **Data Collection and Pre-processing**: Responsible for setting up local proof-of-concept (POC) for image data collection, distributed data collection, and data validation.
  - Tasks:
    - Image data collection POC (local)
    - Distributed data collection
    - Validate data and model requirements

- **AI Model Development**: Responsible for training the computer vision model for car control and optimizing it for fast racing.
  - Tasks:
    - Vision model training POC (local)
    - Optimized model for fast racing
    - Final model training for race performance

- **Infrastructure and Deployment**: Responsible for setting up distributed infrastructure, model deployment, and ensuring scalability and fault tolerance.
  - Tasks:
    - Distributed race performance optimization
    - Automated, fault-tolerant model deployment, serving, and monitoring
    - Scalable production model served via API


## Details 

### Distributed Genetic Algorithm
Architecture involves writing a custom `map` function to distribute computations 
over available pods. Scheduling happens through http. The `map` follows the interface of 
`concurrent.futures`, enabling plug-and-play usage inside the DEAP genetic algorithm library.

### Redis
- Good resources: [Redis with docker-compose](https://geshan.com.np/blog/2022/01/redis-docker/) and [concurrent Python connections to Redis](https://medium.com/@e.ahmadi/manage-concurrency-in-multiple-python-clients-in-redis-5f9a05836a92).
- **Data collection**: we suspect that collecting and sending through HTTP can cause synchronization loss. 
We thus choose to collect data from hooks within the game source code.
