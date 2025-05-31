from flask import Flask, render_template_string, request
import psutil
import time
import pandas as pd

app = Flask(__name__)

# TASKS and HISTORY DataFrames
TASKS = pd.DataFrame({
    "tid": [1, 2, 3, 4],
    "tname": ["Render", "Clean Data", "Train Model", "Browse"],
    "ecpu": [85, 40, 90, 15],
    "egpu": [95, 10, 90, 5],
    "emem": [70, 30, 80, 15]
})

HISTORY = pd.DataFrame({
    "time": ["2025-03-05 10:00", "2025-03-05 11:00"],
    "tid": [1, 2],
    "acpu": [82, 38],
    "agpu": [90, 12],
    "amem": [65, 28],
    "dur": [45, 20]
})

# Backend Functions
def system_usage():
    return {
        "cpu": psutil.cpu_percent(interval=1),
        "gpu": 0,  # Placeholder (add GPUtil if needed)
        "memory": psutil.virtual_memory().percent
    }

def check_task(tid, tasks_df, dur=2, usage_tolerance=10):
    task = tasks_df[tasks_df["tid"] == tid]
    if task.empty:
        return {"error": "Invalid Task"}
    task = task.iloc[0]
    usage_data = [system_usage() for _ in range(dur)]
    avg_usage = {
        "cpu": sum(d["cpu"] for d in usage_data) / len(usage_data),
        "gpu": sum(d["gpu"] for d in usage_data) / len(usage_data),
        "memory": sum(d["memory"] for d in usage_data) / len(usage_data)
    }
    return {
        "tid": tid,
        "tname": task["tname"],
        "avg_cpu": round(avg_usage["cpu"], 2),
        "avg_gpu": round(avg_usage["gpu"], 2),
        "avg_mem": round(avg_usage["memory"], 2),
        "ecpu": task["ecpu"],
        "egpu": task["egpu"],
        "emem": task["emem"]
    }

def calculate_rolling_usage(history_df):
    history_df['time'] = pd.to_datetime(history_df['time'])
    history_df = history_df.set_index('time')
    rolling = history_df[['acpu', 'agpu', 'amem']].rolling(window='5Min').mean().dropna()
    return rolling.reset_index()

def is_low_work_task(task):
    return task["ecpu"] <= 30 and task["egpu"] <= 30 and task["emem"] <= 30

def suggest_task(rolling_usage, tasks_df):
    if rolling_usage.empty:
        return None, None
    last_usage = rolling_usage.iloc[-1]
    is_high = last_usage['acpu'] > 70 and last_usage['agpu'] > 70 and last_usage['amem'] > 70
    is_low = last_usage['acpu'] < 30 and last_usage['agpu'] < 30 and last_usage['amem'] < 30
    if is_high:
        low_tasks = tasks_df[tasks_df.apply(is_low_work_task, axis=1)]
        return low_tasks.iloc[0].to_dict() if not low_tasks.empty else None, "low"
    elif is_low:
        high_tasks = tasks_df[~tasks_df.apply(is_low_work_task, axis=1)]
        return high_tasks.iloc[0].to_dict() if not high_tasks.empty else None, "high"
    return None, None

# Routes
@app.route("/")
def home():
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Alvya - AI Task Management</title>
        <style>
            :root { --primary: #4f46e5; --dark-text: #ffffff; --light-bg: #f4f5f7; --light-text: #333; }
            body { font-family: 'Arial', sans-serif; margin: 0; padding: 0; background: var(--light-bg); color: var(--light-text); transition: all 0.3s ease; }
            body.dark { background: linear-gradient(135deg, #000000, #4b0082); color: var(--dark-text); }
            header { display: flex; justify-content: space-between; align-items: center; padding: 20px 40px; background: #fff; box-shadow: 0 4px 10px rgba(0,0,0,0.1); transition: background 0.3s ease; position: relative; }
            body.dark header { background: #3a2b63; }
            .logo { font-size: 28px; font-weight: bold; color: var(--dark-text); text-decoration: none; position: absolute; left: 50%; transform: translateX(-50%); transition: transform 0.3s ease; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
            body.dark .logo { color: var(--dark-text); text-shadow: 0 0 15px #fff, 0 0 30px #fff, 0 0 10px #fff; }
            .logo:hover { transform: translateX(-50%) scale(1.1); }
            nav { display: flex; align-items: center; }
            .theme-toggle { font-size: 24px; cursor: pointer; transition: transform 0.3s ease; }
            body.dark .theme-toggle::before { content: '🌙'; }
            .theme-toggle:not(.dark)::before { content: '☀'; }
            .theme-toggle:hover { transform: scale(1.2); }
            nav ul { list-style: none; display: flex; margin: 0; padding: 0; }
            nav ul li { margin: 0 20px; }
            nav ul li a { color: inherit; text-decoration: none; font-weight: bold; font-size: 16px; padding: 8px 16px; border-radius: 5px; transition: background 0.3s ease, transform 0.3s ease; }
            nav ul li a:hover { background: rgba(79, 70, 229, 0.1); transform: translateY(-2px); }
            .hero { padding: 80px 20px; margin: 30px auto; width: 85%; background: #fff; border-radius: 15px; box-shadow: 0 6px 20px rgba(0,0,0,0.1); animation: fadeIn 1s ease; transition: background 0.3s ease; position: relative; }
            body.dark .hero { background: #3a2b63; }
            .hero h1 { font-size: 42px; margin-bottom: 15px; animation: slideUp 0.8s ease; }
            .hero p { font-size: 20px; color: #666; margin-bottom: 30px; animation: slideUp 1s ease; }
            body.dark .hero p { color: #d1d5db; }
            .btn { background: var(--primary); color: #fff; padding: 12px 25px; border-radius: 8px; font-size: 18px; text-decoration: none; display: inline-block; position: relative; overflow: hidden; transition: transform 0.3s ease, box-shadow 0.3s ease; }
            .btn:hover { transform: scale(1.05); box-shadow: 0 4px 15px rgba(79, 70, 229, 0.4); }
            .btn::after { content: '🚀'; position: absolute; top: 90%; left: 50%; transform: translateX(-50%) rotate(45deg); font-size: 24px; opacity: 0; transition: all 1.2s ease; }
            .btn.clicked::after { top: -10%; opacity: 1; }
            footer { position: fixed; bottom: 0; width: 100%; padding: 15px; background: #fff; text-align: center; box-shadow: 0 -2px 10px rgba(0,0,0,0.1); transition: background 0.3s ease; }
            body.dark footer { background: #3a2b63; }
            .loading { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); display: none; justify-content: center; align-items: center; z-index: 100; }
            .loading.active { display: flex; }
            .rocket { font-size: 50px; animation: propel 1.2s ease forwards; position: absolute; text-shadow: 0 0 15px #fff, 0 0 30px #4f46e5; }
            @keyframes propel { 
                0% { top: 90%; left: 50%; transform: translateX(-50%) scale(1); opacity: 1; } 
                50% { transform: translateX(-50%) scale(1.5); opacity: 1; } 
                100% { top: -10%; left: 90%; transform: translateX(-50%) scale(1); opacity: 0; } 
            }
            @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
            @keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        </style>
        <script>
            function rocketLaunch(event) {
                event.preventDefault();
                document.querySelector('.btn').classList.add('clicked');
                document.querySelector('.loading').classList.add('active');
                setTimeout(() => window.location.href = '/monitor', 1200);
            }
        </script>
    </head>
    <body>
        <header>
            <div class="theme-toggle" onclick="document.body.classList.toggle('dark')"></div>
            <a href="/" class="logo">Alvya</a>
            <nav>
                <ul>
                    <li><a href="/monitor">Monitoring</a></li>
                    <li><a href="/allocate">Task Allocation</a></li>
                </ul>
            </nav>
        </header>
        <section class="hero">
            <h1>AI-Powered Task Management</h1>
            <p>Optimize workflow, automate processes, and enhance productivity with Alvya.</p>
            <a href="#" class="btn" onclick="rocketLaunch(event)">Get Started →</a>
        </section>
        <div class="loading"><span class="rocket">🚀</span></div>
        <footer>
            <p>© 2025 Alvya | All Rights Reserved</p>
        </footer>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route("/monitor", methods=["GET", "POST"])
def monitor():
    task_result = None
    overall_status = None
    if request.method == "POST":
        if "task" in request.form:
            tid = int(request.form["task"])
            task_result = check_task(tid, TASKS)
            if task_result and "error" not in task_result:
                usage_tolerance = 10
                avg_exceeds_expected = (
                    (task_result["avg_cpu"] > task_result["ecpu"] + usage_tolerance) or
                    (task_result["avg_gpu"] > task_result["egpu"] + usage_tolerance) or
                    (task_result["avg_mem"] > task_result["emem"] + usage_tolerance)
                )
                overall_status = "High Workload" if avg_exceeds_expected else "Low Workload"
    
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Alvya - Monitoring</title>
        <style>
            :root { --primary: #4f46e5; --dark-text: #ffffff; --light-bg: #f4f5f7; --light-text: #333; }
            body { font-family: 'Arial', sans-serif; margin: 0; padding: 0; background: var(--light-bg); color: var(--light-text); transition: all 0.3s ease; }
            body.dark { background: linear-gradient(135deg, #000000, #4b0082); color: var(--dark-text); }
            header { display: flex; justify-content: space-between; align-items: center; padding: 20px 40px; background: #fff; box-shadow: 0 4px 10px rgba(0,0,0,0.1); transition: background 0.3s ease; position: relative; }
            body.dark header { background: #3a2b63; }
            .logo { font-size: 28px; font-weight: bold; color: var(--dark-text); text-decoration: none; position: absolute; left: 50%; transform: translateX(-50%); transition: transform 0.3s ease; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
            body.dark .logo { color: var(--dark-text); text-shadow: 0 0 15px #fff, 0 0 30px #fff, 0 0 10px #fff; }
            .logo:hover { transform: translateX(-50%) scale(1.1); }
            nav { display: flex; align-items: center; }
            .theme-toggle { font-size: 24px; cursor: pointer; transition: transform 0.3s ease; }
            body.dark .theme-toggle::before { content: '🌙'; }
            .theme-toggle:not(.dark)::before { content: '☀'; }
            .theme-toggle:hover { transform: scale(1.2); }
            nav ul { list-style: none; display: flex; margin: 0; padding: 0; }
            nav ul li { margin: 0 20px; }
            nav ul li a { color: inherit; text-decoration: none; font-weight: bold; font-size: 16px; padding: 8px 16px; border-radius: 5px; transition: background 0.3s ease, transform 0.3s ease; }
            nav ul li a:hover { background: rgba(79, 70, 229, 0.1); transform: translateY(-2px); }
            .content { padding: 50px 20px; margin: 30px auto; width: 85%; background: #fff; border-radius: 15px; box-shadow: 0 6px 20px rgba(0,0,0,0.1); animation: fadeIn 1s ease; transition: background 0.3s ease; }
            body.dark .content { background: #3a2b63; }
            h1 { font-size: 36px; margin-bottom: 20px; animation: slideUp 0.8s ease; }
            form { margin: 20px 0; }
            select, button { padding: 10px; font-size: 16px; border-radius: 8px; border: none; margin: 0 10px; transition: transform 0.3s ease; }
            select { background: #f0f0f0; }
            body.dark select { background: #4b3a7a; color: #fff; }
            button { background: var(--primary); color: #fff; cursor: pointer; }
            button:hover { transform: scale(1.05); }
            .result { margin-top: 30px; padding: 20px; background: #f9fafb; border-radius: 10px; animation: slideUp 1s ease; transition: background 0.3s ease; }
            body.dark .result { background: #4b3a7a; }
            .status-high { color: #e11d48; font-weight: bold; }
            .status-low { color: #16a34a; font-weight: bold; }
            .suggest-btn { margin-top: 20px; }
            footer { position: fixed; bottom: 0; width: 100%; padding: 15px; background: #fff; text-align: center; box-shadow: 0 -2px 10px rgba(0,0,0,0.1); transition: background 0.3s ease; }
            body.dark footer { background: #3a2b63; }
            @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
            @keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        </style>
    </head>
    <body>
        <header>
            <div class="theme-toggle" onclick="document.body.classList.toggle('dark')"></div>
            <a href="/" class="logo">Alvya</a>
            <nav>
                <ul>
                    <li><a href="/monitor">Monitoring</a></li>
                    <li><a href="/allocate">Task Allocation</a></li>
                </ul>
            </nav>
        </header>
        <section class="content">
            <h1>Task Monitoring</h1>
            <form method="post">
                <label for="task">Select Task:</label>
                <select name="task" id="task">
                    {% for task in tasks %}
                        <option value="{{ task.tid }}">{{ task.tname }}</option>
                    {% endfor %}
                </select>
                <button type="submit">Monitor Task</button>
            </form>
            {% if task_result %}
                <div class="result">
                    <h2>{{ task_result.tname }}</h2>
                    <p>CPU Usage: {{ task_result.avg_cpu }}% (Expected: {{ task_result.ecpu }}%)</p>
                    <p>GPU Usage: {{ task_result.avg_gpu }}% (Expected: {{ task_result.egpu }}%)</p>
                    <p>Memory Usage: {{ task_result.avg_mem }}% (Expected: {{ task_result.emem }}%)</p>
                    <p>Overall Status: <span class="{% if overall_status == 'High Workload' %}status-high{% else %}status-low{% endif %}">{{ overall_status }}</span></p>
                </div>
                <form action="/allocate" method="get" class="suggest-btn">
                    <button type="submit">Give Suggested Task</button>
                </form>
            {% endif %}
        </section>
        <footer>
            <p>© 2025 Alvya | All Rights Reserved</p>
        </footer>
    </body>
    </html>
    """
    return render_template_string(html, tasks=TASKS.to_dict("records"), task_result=task_result, overall_status=overall_status)

@app.route("/allocate", methods=["GET", "POST"])
def allocate():
    task_result = None
    suggestion = None
    task_type = None
    if request.method == "POST":
        tid = int(request.form["task"])
        task_result = check_task(tid, TASKS)
        rolling_usage = calculate_rolling_usage(HISTORY.copy())
        suggestion, task_type = suggest_task(rolling_usage, TASKS)
    
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Alvya - Task Allocation</title>
        <style>
            :root { --primary: #4f46e5; --dark-text: #ffffff; --light-bg: #f4f5f7; --light-text: #333; }
            body { font-family: 'Arial', sans-serif; margin: 0; padding: 0; background: var(--light-bg); color: var(--light-text); transition: all 0.3s ease; }
            body.dark { background: linear-gradient(135deg, #000000, #4b0082); color: var(--dark-text); }
            header { display: flex; justify-content: space-between; align-items: center; padding: 20px 40px; background: #fff; box-shadow: 0 4px 10px rgba(0,0,0,0.1); transition: background 0.3s ease; position: relative; }
            body.dark header { background: #3a2b63; }
            .logo { font-size: 28px; font-weight: bold; color: var(--dark-text); text-decoration: none; position: absolute; left: 50%; transform: translateX(-50%); transition: transform 0.3s ease; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
            body.dark .logo { color: var(--dark-text); text-shadow: 0 0 15px #fff, 0 0 30px #fff, 0 0 10px #fff; }
            .logo:hover { transform: translateX(-50%) scale(1.1); }
            nav { display: flex; align-items: center; }
            .theme-toggle { font-size: 24px; cursor: pointer; transition: transform 0.3s ease; }
            body.dark .theme-toggle::before { content: '🌙'; }
            .theme-toggle:not(.dark)::before { content: '☀'; }
            .theme-toggle:hover { transform: scale(1.2); }
            nav ul { list-style: none; display: flex; margin: 0; padding: 0; }
            nav ul li { margin: 0 20px; }
            nav ul li a { color: inherit; text-decoration: none; font-weight: bold; font-size: 16px; padding: 8px 16px; border-radius: 5px; transition: background 0.3s ease, transform 0.3s ease; }
            nav ul li a:hover { background: rgba(79, 70, 229, 0.1); transform: translateY(-2px); }
            .content { padding: 50px 20px; margin: 30px auto; width: 85%; background: #fff; border-radius: 15px; box-shadow: 0 6px 20px rgba(0,0,0,0.1); animation: fadeIn 1s ease; transition: background 0.3s ease; }
            body.dark .content { background: #3a2b63; }
            h1 { font-size: 36px; margin-bottom: 20px; animation: slideUp 0.8s ease; }
            form { margin: 20px 0; }
            select, button { padding: 10px; font-size: 16px; border-radius: 8px; border: none; margin: 0 10px; transition: transform 0.3s ease; }
            select { background: #f0f0f0; }
            body.dark select { background: #4b3a7a; color: #fff; }
            button { background: var(--primary); color: #fff; cursor: pointer; }
            button:hover { transform: scale(1.05); }
            .result, .suggestion { margin-top: 30px; padding: 20px; background: #f9fafb; border-radius: 10px; animation: slideUp 1s ease; transition: background 0.3s ease; }
            body.dark .result, body.dark .suggestion { background: #4b3a7a; }
            .suggestion { color: var(--primary); }
            footer { position: fixed; bottom: 0; width: 100%; padding: 15px; background: #fff; text-align: center; box-shadow: 0 -2px 10px rgba(0,0,0,0.1); transition: background 0.3s ease; }
            body.dark footer { background: #3a2b63; }
            @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
            @keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        </style>
    </head>
    <body>
        <header>
            <div class="theme-toggle" onclick="document.body.classList.toggle('dark')"></div>
            <a href="/" class="logo">Alvya</a>
            <nav>
                <ul>
                    <li><a href="/monitor">Monitoring</a></li>
                    <li><a href="/allocate">Task Allocation</a></li>
                </ul>
            </nav>
        </header>
        <section class="content">
            <h1>Task Allocation</h1>
            <form method="post">
                <label for="task">Select Task:</label>
                <select name="task" id="task">
                    {% for task in tasks %}
                        <option value="{{ task.tid }}">{{ task.tname }}</option>
                    {% endfor %}
                </select>
                <button type="submit">Allocate Task</button>
            </form>
            {% if task_result %}
                <div class="result">
                    <h2>{{ task_result.tname }}</h2>
                    <p>CPU Usage: {{ task_result.avg_cpu }}% (Expected: {{ task_result.ecpu }}%)</p>
                    <p>GPU Usage: {{ task_result.avg_gpu }}% (Expected: {{ task_result.egpu }}%)</p>
                    <p>Memory Usage: {{ task_result.avg_mem }}% (Expected: {{ task_result.emem }}%)</p>
                    <p>Workload: {{ 'High' if task_result.avg_cpu > 70 else 'Low' }}</p>
                </div>
                {% if suggestion %}
                    <div class="suggestion">
                        <h3>Suggested Next Task ({{ task_type }}):</h3>
                        <p>{{ suggestion.tname }} (CPU: {{ suggestion.ecpu }}%, GPU: {{ suggestion.egpu }}%, Memory: {{ suggestion.emem }}%)</p>
                    </div>
                {% endif %}
            {% endif %}
        </section>
        <footer>
            <p>© 2025 Alvya | All Rights Reserved</p>
        </footer>
    </body>
    </html>
    """
    return render_template_string(html, tasks=TASKS.to_dict("records"), task_result=task_result, suggestion=suggestion, task_type=task_type)

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
