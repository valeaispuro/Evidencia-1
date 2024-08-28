from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
import json
import threading
from warehouse_agent import WarehouseModel, WarehouseAgent, WarehouseObject, WarehouseStack

simulation_state = None


class Server(BaseHTTPRequestHandler):
    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_GET(self):
        logging.info("GET request,\nPath: %s\nHeaders:\n%s\n",
                     str(self.path), str(self.headers))
        response_data = get_response()
        self._set_response()
        self.wfile.write(json.dumps(response_data).encode('utf-8'))

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = json.loads(self.rfile.read(content_length))
        logging.info("POST request,\nPath: %s\nHeaders:\n%s\n\nBody:\n%s\n",
                     str(self.path), str(self.headers), json.dumps(post_data))

        response_data = post_response(post_data)

        self._set_response()
        self.wfile.write(json.dumps(response_data).encode('utf-8'))


def run(server_class=HTTPServer, handler_class=Server, port=8585):
    logging.basicConfig(level=logging.INFO)
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info("Starting httpd...\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info("Stopping httpd...\n")


def post_response(data):
    global simulation_state
    if 'init' in data and data['init']:
        parameters = {
            'M': data.get('M', 10),
            'N': data.get('N', 10),
            'steps': data.get('steps', 25),
            'robots': data.get('robots', 5),
            'objects': data.get('objects', 30),
            'stacks': data.get('stacks', 0),
        }
        simulation_state = WarehouseModel(parameters)
        simulation_state.setup()
        return {"message": "Simulation initialized"}
    return {"message": "Use GET request to step through simulation"}


def describe_agent(agent):
    description = {
        'id': agent.id,
        'type': agent.agentType,
    }

    if isinstance(agent, WarehouseAgent):
        description['carries'] = [describe_agent(obj) for obj in agent.carries]
    if isinstance(agent, WarehouseStack):
        description['carries'] = [describe_agent(obj) for obj in agent.content]

    return description


def clean_grid(grid):
    if grid is None:
        return None
    out = []
    for row in grid:
        out_row = []
        for cell in row:
            if len(cell) > 1:
                print(cell)
            cell = cell[0]
            if not len(cell):
                out_row.append(None)
            else:
                out_cell = []
                for agent in cell:
                    out_cell.append(describe_agent(agent))
                out_row.append(out_cell)
        out.append(out_row)
    return out


def get_response():
    global simulation_state
    if simulation_state is None:
        return {"error": "Simulation not initialized. Send a POST request to initialize."}

    step_result = simulation_state.step()
    step_result = clean_grid(step_result)
    if step_result is None:
        return {"message": "Simulation complete"}
    else:
        return {
            "step": simulation_state.steps,
            "positions": step_result
        }


if __name__ == '__main__':
    from sys import argv
    run()
