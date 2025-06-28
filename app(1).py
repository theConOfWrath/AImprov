from flask import Flask, request, render_template
import os

app = Flask(__name__)

@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        endpoint_type = request.form.get("endpoint_type")
        model_name = request.form.get("model_name")
        local_endpoint = request.form.get("local_endpoint")
        # Save to settings.py or .env
        with open("settings.py", "w") as f:
            f.write(f'ENDPOINT_TYPE = "{endpoint_type}"\n')
            f.write(f'MODEL_NAME = "{model_name}"\n')
            f.write(f'LOCAL_ENDPOINT = "{local_endpoint}"\n')
        return "Settings saved! Run main.py to start the show."
    return render_template("settings.html")

if __name__ == "__main__":
    app.run(debug=True)