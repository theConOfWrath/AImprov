from flask import Flask, request, render_template, flash, redirect, url_for
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For flash messages

@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        endpoint_type = request.form.get("endpoint_type")
        model_name = request.form.get("model_name")
        local_endpoint = request.form.get("local_endpoint", "")

        # Basic validation
        if not endpoint_type:
            flash("Endpoint type is required!", "error")
            return redirect(url_for("settings"))
        if endpoint_type == "local" and not local_endpoint:
            flash("Local endpoint URL is required for local LLM!", "error")
            return redirect(url_for("settings"))
        if not model_name:
            flash("Model name is required!", "error")
            return redirect(url_for("settings"))

        # Save to settings.py
        try:
            with open("settings.py", "w") as f:
                f.write(f'ENDPOINT_TYPE = "{endpoint_type}"\n')
                f.write(f'MODEL_NAME = "{model_name}"\n')
                f.write(f'LOCAL_ENDPOINT = "{local_endpoint}"\n')
            flash("Settings saved successfully! Run main.py to start the improv show.", "success")
        except Exception as e:
            flash(f"Failed to save settings: {e}", "error")

        return redirect(url_for("settings"))

    return render_template("settings.html")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
