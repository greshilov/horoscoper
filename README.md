# Horoscoper

The project is named `Horoscoper` because of my "slow" workers implementation. 
They produce deterministic horoscopes based on supplied input contexts (strings) with pre-configured delays (see more [here](horoscoper/horoscope.py)).  

Live version is available via the following links:  
 * [Web interface](https://horoscoper.greshilov.me/)
 * [OpenAPI](https://horoscoper.greshilov.me/docs)
 * Monitoring (see login/password in email)
   * [API dashboard](https://horoscoper.greshilov.me/grafana/d/f3b52491-5496-4c4f-88c5-c749174237c9/api?orgId=1)
   * [Workers dashboard](https://horoscoper.greshilov.me/grafana/d/fa95f9a7-880b-4876-845b-1ef64a10e391/rq-dashboard?orgId=1)

## Architecture overview
[<img src="etc/img/arch-overview.png" width="750px"/>](etc/img/arch-overview.png "Architecture")

* API is asynchronous (implemented using `FastAPI` framework)
* Workers are synchronous and controlled via `Redis` with `Python-RQ` [library](https://python-rq.org/)
* Batching behaviour is simmilar to [static batching][1]
* Batching happens on the API side in a separate coroutine (see [horoscoper/api/batcher.py](horoscoper/api/batcher.py))
* Workers stream their responses back to API on the fly using Pub/Sub 

## Quickstart
The easiest way to check the project locally would be starting minimal working setup using the following command:  
```
docker compose up --build
```
This command will spin up one API instance, two workers and redis.  
Check the http://localhost:8080/ to play with the web interface :)  
To change number of workers update the `worker:deploy:replicas` key in [docker-compose.yml](./docker-compose.yml) file.

## Development
This project uses Makefile as a primary automation tool, so please ensure `make` command is available in your environment. Commands from Makefile also require `poetry` to be installed (check the installation instructions [here](https://python-poetry.org/docs/#installation)).

### Install dependencies
Firstly install all the required dependecies.
```
make init
```

### Run development API instance
Run the following command and check out the http://localhost:8000/.  
```
make dev-api
```
Note, you need at least one running worker in order for API to work correctly.  

### Run development worker instance
```
make dev-worker
```

### Format & lint
The following commands will format your code and lint it, using flake8.
```
make fmt
make lint
```

### Tests
```
make test
```

## References
[1]: https://www.anyscale.com/blog/continuous-batching-llm-inference "Continuous batching"  
[2]: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events  "SSE Usage"  
