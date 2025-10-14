from flask import Flask, jsonify, request
from flask_cors import CORS
import google.generativeai as genai
import os
import json
import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Set up Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)

# Simple file-based storage
PLANS_FILE = 'plans.json'

def load_plans():
    """Load all saved plans from file"""
    if os.path.exists(PLANS_FILE):
        try:
            with open(PLANS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_plans(plans):
    """Save all plans to file"""
    with open(PLANS_FILE, 'w') as f:
        json.dump(plans, f, indent=2)

@app.route('/')
def home():
    return jsonify({"message": "Smart Task Planner Backend is running with Storage!"})

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"})

@app.route('/plan-tasks', methods=['POST'])
def plan_tasks():
    try:
        data = request.json
        goal = data.get('goal', '')
        
        if not goal:
            return jsonify({"error": "No goal provided"}), 400
        
        # Create AI prompt
        prompt = f"""
        Break down this goal into actionable tasks with suggested deadlines and dependencies: "{goal}"
        
        Please provide the response in this exact format:
        
        Task 1: [Task description]
        Deadline: [When to complete]
        Depends on: [What needs to be done first]
        
        Task 2: [Task description]
        Deadline: [When to complete] 
        Depends on: [What needs to be done first]
        
        Continue for all tasks...
        """
        
        # Call Gemini API
        model = genai.GenerativeModel('models/gemini-2.0-flash-001')
        response = model.generate_content(prompt)
        
        # Save the plan to storage
        plans = load_plans()
        new_plan = {
            'id': len(plans) + 1,
            'goal': goal,
            'task_breakdown': response.text,
            'created_at': datetime.datetime.now().isoformat(),
            'completed': False,
            'completion_percentage': 0,
            'tasks': parse_tasks_from_breakdown(response.text)
        }
        plans.append(new_plan)
        save_plans(plans)
        
        return jsonify({
            "goal": goal,
            "task_breakdown": response.text,
            "plan_id": new_plan['id'],
            "saved": True,
            "message": "Plan saved to storage!",
            "completion_percentage": 0,
            "tasks": new_plan['tasks']
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# NEW: Parse tasks from breakdown text
def parse_tasks_from_breakdown(breakdown):
    """Parse task breakdown into individual tasks with status"""
    tasks = []
    lines = breakdown.split('\n')
    
    for line in lines:
        line = line.strip()
        if line.startswith('Task'):
            tasks.append({
                'description': line,
                'completed': False,
                'task_index': len(tasks)
            })
    
    return tasks

# NEW: Update task completion status
@app.route('/update-task-status', methods=['POST'])
def update_task_status():
    try:
        data = request.json
        plan_id = data.get('plan_id')
        task_index = data.get('task_index')
        completed = data.get('completed', True)
        
        plans = load_plans()
        plan = next((p for p in plans if p['id'] == plan_id), None)
        
        if plan:
            # Update the task status
            if 'tasks' not in plan:
                plan['tasks'] = parse_tasks_from_breakdown(plan['task_breakdown'])
            
            if 0 <= task_index < len(plan['tasks']):
                plan['tasks'][task_index]['completed'] = completed
                
                # Calculate completion percentage
                completed_tasks = sum(1 for task in plan['tasks'] if task['completed'])
                plan['completion_percentage'] = int((completed_tasks / len(plan['tasks'])) * 100) if plan['tasks'] else 0
                
                save_plans(plans)
                
                return jsonify({
                    "success": True,
                    "completion_percentage": plan['completion_percentage'],
                    "completed_tasks": completed_tasks,
                    "total_tasks": len(plan['tasks'])
                })
        
        return jsonify({"error": "Plan or task not found"}), 404
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# NEW: Get resource suggestions
@app.route('/get-resources', methods=['POST'])
def get_resources():
    try:
        data = request.json
        goal = data.get('goal', '')
        task = data.get('task', '')
        
        prompt = f"""
        For the goal "{goal}" and specific task "{task}", suggest helpful resources.
        
        Provide in this format:
        
        Learning Resources:
        - [Resource type]: [Specific suggestion] - [Brief description]
        
        Tools & Software:
        - [Tool name] - [What it's used for]
        
        Tips:
        - [Practical tip]
        
        Keep it concise and actionable.
        """
        
        model = genai.GenerativeModel('models/gemini-2.0-flash-001')
        response = model.generate_content(prompt)
        
        return jsonify({
            "goal": goal,
            "task": task,
            "resources": response.text
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Get all saved plans
@app.route('/saved-plans', methods=['GET'])
def get_saved_plans():
    """Get all saved task plans"""
    plans = load_plans()
    return jsonify({
        "total_plans": len(plans),
        "plans": plans
    })

# Get a specific saved plan
@app.route('/saved-plans/<int:plan_id>', methods=['GET'])
def get_saved_plan(plan_id):
    """Get a specific saved plan"""
    plans = load_plans()
    plan = next((p for p in plans if p['id'] == plan_id), None)
    
    if plan:
        return jsonify(plan)
    else:
        return jsonify({"error": "Plan not found"}), 404

# Delete a saved plan
@app.route('/saved-plans/<int:plan_id>', methods=['DELETE'])
def delete_saved_plan(plan_id):
    """Delete a specific saved plan"""
    plans = load_plans()
    plan_index = next((i for i, p in enumerate(plans) if p['id'] == plan_id), None)
    
    if plan_index is not None:
        deleted_plan = plans.pop(plan_index)
        save_plans(plans)
        return jsonify({
            "deleted": True,
            "plan_id": plan_id,
            "goal": deleted_plan['goal']
        })
    else:
        return jsonify({"error": "Plan not found"}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)