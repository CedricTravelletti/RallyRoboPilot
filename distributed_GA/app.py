from flask import Flask, request, jsonify
import time
import random
import threading

app = Flask(__name__)

# To store results for each job
results = {}

@app.route('/run_simulation', methods=['POST'])
def run_simulation():
    params = request.json
    job_id = str(random.randint(1000, 9999))
    
    # Simulate expensive computation in a separate thread
    def expensive_computation():
        time.sleep(random.uniform(2, 5))  # Simulate time-consuming computation
        results[job_id] = {"status": "completed", "result": sum(params.values())}  # Example result
    
    threading.Thread(target=expensive_computation).start()
    
    return jsonify({"job_id": job_id}), 202  # Return job ID

@app.route('/result/<job_id>', methods=['GET'])
def get_result(job_id):
    if job_id in results:
        return jsonify(results[job_id])
    else:
        return jsonify({"status": "pending"}), 202

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

